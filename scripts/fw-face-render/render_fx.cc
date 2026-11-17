// Host renderer with the overlay engine, the screen effects and the speech bubble (patches TA02 to TA04): the real LVGL and the real face classes, drawn into memory. Commands come from stdin, one per line:
//   style NAME | emotion NAME | weight L R | speak LEVEL (0 stops) | advance MS | snap FILE.png | colour R G B | cmd ... (see below)
// The look is judged from the PNGs this writes; the unit's own PNGs (scripts/fw-serial.py snap) confirm it at the end.
#include <lvgl.h>
#include <zlib.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sstream>
#include <iostream>
#include <vector>
#include <stackchan/avatar/skins/default/default.h>
#include "maipai_facefx.h"
#include "render_hooks.h"
#include "maipai_overlay_core.h"
#include "maipai_look_core.h"
#include "maipai_prefs_core.h"

int64_t g_fake_us = 1000000;
using namespace stackchan::avatar;

static uint8_t s_buf[320 * 240 * 2];

static void flush_cb(lv_display_t* d, const lv_area_t*, uint8_t*) { lv_display_flush_ready(d); }
static uint32_t tick_cb() { return (uint32_t)(g_fake_us / 1000); }

static std::vector<uint8_t> to_rgb(const uint8_t* rgb565)
{
    std::vector<uint8_t> o;
    for (int i = 0; i < 320 * 240; i++) {
        uint16_t v = rgb565[i * 2] | (rgb565[i * 2 + 1] << 8);
        o.push_back(((v >> 11) & 31) * 255 / 31);
        o.push_back(((v >> 5) & 63) * 255 / 63);
        o.push_back((v & 31) * 255 / 31);
    }
    return o;
}

static void write_rgb_png(const char* path, const std::vector<uint8_t>& rgb, int w, int h)
{
    std::vector<uint8_t> raw;
    for (int y = 0; y < h; y++) {
        raw.push_back(0);
        raw.insert(raw.end(), rgb.begin() + (size_t)y * w * 3, rgb.begin() + (size_t)(y + 1) * w * 3);
    }
    uLongf cl = compressBound(raw.size());
    std::vector<uint8_t> comp(cl);
    compress(comp.data(), &cl, raw.data(), raw.size());
    FILE* f = fopen(path, "wb");
    auto be32 = [&](uint32_t v) { uint8_t b[4] = {(uint8_t)(v >> 24), (uint8_t)(v >> 16), (uint8_t)(v >> 8), (uint8_t)v}; fwrite(b, 1, 4, f); };
    auto chunk = [&](const char* t, const uint8_t* d, uint32_t n) {
        be32(n); fwrite(t, 1, 4, f); if (n) fwrite(d, 1, n, f);
        uint32_t c = crc32(0, (const Bytef*)t, 4); if (n) c = crc32(c, d, n); be32(c);
    };
    const uint8_t sig[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    fwrite(sig, 1, 8, f);
    uint8_t ihdr[13] = {(uint8_t)(w >> 24), (uint8_t)(w >> 16), (uint8_t)(w >> 8), (uint8_t)w, (uint8_t)(h >> 24), (uint8_t)(h >> 16), (uint8_t)(h >> 8), (uint8_t)h, 8, 2, 0, 0, 0};
    chunk("IHDR", ihdr, 13);
    chunk("IDAT", comp.data(), (uint32_t)cl);
    chunk("IEND", nullptr, 0);
    fclose(f);
}

static void write_png(const char* path, const uint8_t* rgb565);
static std::vector<std::vector<uint8_t>> g_tiles;

// A grid of the tiles taken so far, each shrunk by `div` (1, 2 or 4), with a 2 px grey gap.
static void write_sheet(const char* path, int cols, int div)
{
    const int tw = 320 / div, th = 240 / div, gap = 2;
    const int rows = (int)((g_tiles.size() + cols - 1) / cols);
    const int W = cols * (tw + gap), H = rows * (th + gap);
    std::vector<uint8_t> out((size_t)W * H * 3, 60);
    for (size_t i = 0; i < g_tiles.size(); i++) {
        const int ox = (int)(i % cols) * (tw + gap), oy = (int)(i / cols) * (th + gap);
        for (int y = 0; y < th; y++)
            for (int x = 0; x < tw; x++)
                for (int ch = 0; ch < 3; ch++) {
                    int sum = 0;
                    for (int dy = 0; dy < div; dy++)
                        for (int dx = 0; dx < div; dx++) sum += g_tiles[i][((y * div + dy) * 320 + x * div + dx) * 3 + ch];
                    out[((size_t)(oy + y) * W + ox + x) * 3 + ch] = (uint8_t)(sum / (div * div));
                }
    }
    write_rgb_png(path, out, W, H);
}

// Track A: the overlay layers and the screen effects, composited exactly as the unit does in its flush callback.
static mo_layer_t g_ov[2];
static mfx_t g_fx;
static uint8_t g_gmask[MFX_GLOW_MAX_SIDE * MFX_GLOW_MAX_SIDE];
static int g_style = 0, g_glow_pref = 0, g_sleeping = 0;
static uint32_t g_seed = 1000;

static void fx_refresh()
{
    const ml_style_t* st = ml_style(g_style);
    g_fx.glow = g_glow_pref && !g_sleeping && st->eye_d > 0 && mfx_glow_side(st->eye_d) <= MFX_GLOW_MAX_SIDE;
    if (g_fx.glow) {
        g_fx.gside = mfx_glow_bake(g_gmask, st->eye_d);
        g_fx.gmask = g_gmask;
        g_fx.gx[0] = 160 - st->eye_x - g_fx.gside / 2;
        g_fx.gx[1] = 160 + st->eye_x - g_fx.gside / 2;
        g_fx.gy = 120 + st->eye_y - g_fx.gside / 2;
        g_fx.gcol = 0xFFFF;
    }
}

// What the panel would show for the face LVGL drew into `src`: the overlays, then the effects, over the whole screen.
static void compose(const uint8_t* src, uint8_t* dst)
{
    memcpy(dst, src, 320 * 240 * 2);
    uint16_t* px = reinterpret_cast<uint16_t*>(dst);
    mc_t cv = {px, 0, 0, 319, 239, 320, 0};
    for (int l = 0; l < 2; l++) mo_draw(&g_ov[l], &cv);
    if (mfx_any(&g_fx)) mfx_post(&g_fx, px, 0, 0, 319, 239);
}

static void write_png(const char* path, const uint8_t* rgb565) { static uint8_t out[320 * 240 * 2]; compose(rgb565, out); write_rgb_png(path, to_rgb(out), 320, 240); }

static DefaultAvatar* g_av;
static lv_obj_t* g_scr;

static void frame()
{
    g_fake_us += 33333;
    for (int l = 0; l < 2; l++) {
        mo_step(&g_ov[l], 33);
        g_ov[l].ndirty = 0;
        if (g_ov[l].id != MO_NONE && mo_done(&g_ov[l])) mo_clear(&g_ov[l]);
    }
    g_av->update();
    render_hook_frame(g_av);
    lv_timer_handler();
}

static Emotion emo(const std::string& n)
{
    if (n == "happy") return Emotion::Happy;
    if (n == "angry") return Emotion::Angry;
    if (n == "sad") return Emotion::Sad;
    if (n == "doubt") return Emotion::Doubt;
    if (n == "sleepy") return Emotion::Sleepy;
    return render_hook_emotion(n);
}

int main()
{
    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t* d = lv_display_create(320, 240);
    lv_display_set_buffers(d, s_buf, nullptr, sizeof(s_buf), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(d, flush_cb);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB565);
    g_scr = lv_screen_active();
    lv_obj_set_style_bg_color(g_scr, lv_color_black(), 0);
    static DefaultAvatar av;
    g_av = &av;
    av.init(g_scr);
    render_hook_init(g_av, g_scr);
    maipai_speech_set_active(false);
    bool speaking = false;
    int level = 0;
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream in(line);
        std::string c;
        in >> c;
        if (c.empty() || c[0] == '#') continue;
        if (c == "style") {  // remember it for the glow, then let the hook set it
            const std::streampos at = in.tellg(); std::string n; in >> n; in.clear(); in.seekg(at);
            for (int i = 0; i < ML_STYLE_COUNT; i++) if (n == ML_STYLES[i].name) g_style = i;
            fx_refresh();
        }
        if (c == "emotion") { std::string n; in >> n; g_av->setEmotion(emo(n)); g_sleeping = n == "sleeping" || n == "closing"; fx_refresh(); }
        else if (c == "speak") {
            in >> level;
            speaking = level > 0;
            maipai_speech_set_active(speaking);
        } else if (c == "advance") {
            int ms; in >> ms;
            for (int t = 0; t < ms; t += 33) {
                if (speaking) maipai_speech_feed_bench(level);
                frame();
            }
        } else if (c == "snap") {
            std::string f; in >> f;
            if (speaking) maipai_speech_feed_bench(level);
            frame(); frame();
            write_png(f.c_str(), s_buf);
        } else if (c == "zonecheck") {
            // zonecheck STYLE EMOTION SPEAK THINK: after one frame, how many pixels are lit in the banner zone (y 0 to 28) and in the
            // subtitle zone (y 184 to 240); with no banner and no subtitle both must be 0 (the face stays in its own zone, patch N04)
            std::string st, em; int sp = 0, th = 0; in >> st >> em >> sp >> th;
            if (speaking) maipai_speech_feed_bench(level);
            frame();
            auto rgb = to_rgb(s_buf);
            int top = 0, bottom = 0, miny = 999, maxy = -1;
            for (int y = 0; y < 240; y++) for (int x = 0; x < 320; x++) {
                const int i = (y * 320 + x) * 3;
                if (rgb[i] + rgb[i + 1] + rgb[i + 2] > 60) {
                    if (y < 28) top++; else if (y >= 184) bottom++;
                    if (y < miny) miny = y;
                    if (y > maxy) maxy = y;
                }
            }
            printf("zone %s %s speak %d think %d top %d bottom %d miny %d maxy %d\n", st.c_str(), em.c_str(), sp, th, top, bottom, miny, maxy);
        } else if (c == "count") {
            // count x0 y0 x1 y1: how many pixels in the box are lit (brighter than half), for the shape tests
            int x0, y0, x1, y1; in >> x0 >> y0 >> x1 >> y1;
            if (speaking) maipai_speech_feed_bench(level);
            frame();
            auto rgb = to_rgb(s_buf);
            int n = 0, minx = 9999, maxx = -1, miny = 9999, maxy = -1;
            for (int y = y0; y < y1; y++) for (int x = x0; x < x1; x++) {
                const int i = (y * 320 + x) * 3;
                if (rgb[i] + rgb[i + 1] + rgb[i + 2] > 3 * 128) { n++; minx = x < minx ? x : minx; maxx = x > maxx ? x : maxx; miny = y < miny ? y : miny; maxy = y > maxy ? y : maxy; }
            }
            printf("count %d bbox %d %d %d %d\n", n, minx, miny, maxx, maxy);
        } else if (c == "eyes") {
            // eyes: one frame, then the lit pixels of the left eye box and of the right eye box (so both are read at the same instant)
            if (speaking) maipai_speech_feed_bench(level);
            frame();
            auto rgb = to_rgb(s_buf);
            int n[2] = {0, 0};
            for (int y = 30; y < 142; y++) for (int x = 12; x < 308; x++) {
                if (x >= 140 && x < 180) continue;
                const int i = (y * 320 + x) * 3;
                if (rgb[i] + rgb[i + 1] + rgb[i + 2] > 3 * 128) n[x < 160 ? 0 : 1]++;
            }
            printf("eyes %d %d\n", n[0], n[1]);
        } else if (c == "tile") {
            if (speaking) maipai_speech_feed_bench(level);
            frame(); frame();
            { static uint8_t out[320 * 240 * 2]; compose(s_buf, out); g_tiles.push_back(to_rgb(out)); }
        } else if (c == "sheet") {
            std::string f; int cols = 4, div = 2; in >> f >> cols >> div;
            write_sheet(f.c_str(), cols, div);
            g_tiles.clear();
        } else if (c == "overlay") {
            // overlay NAME [INTENSITY 1-3] [SECONDS, 0 = until cleared]
            std::string n; int inten = 2, secs = 0; in >> n >> inten >> secs;
            const int id = mo_id(n.c_str());
            if (id == 0) { fprintf(stderr, "unknown overlay %s\n", n.c_str()); continue; }
            mo_start(&g_ov[mo_layer_of(id)], id, inten, (uint32_t)secs, g_seed++);
        } else if (c == "ovflash") {  // run on until the thunder flash is on screen (at most 20 s)
            for (int i = 0; i < 600 && g_ov[0].s1 != 2; i++) frame();
        } else if (c == "tilenow") {  // a picture of this very frame, no time passes
            static uint8_t out[320 * 240 * 2]; compose(s_buf, out); g_tiles.push_back(to_rgb(out));
        } else if (c == "ovclear") {
            for (int l = 0; l < 2; l++) mo_clear(&g_ov[l]);
        } else if (c == "ovstop") {
            for (int l = 0; l < 2; l++) mo_stop(&g_ov[l]);
        } else if (c == "fx") {
            // fx crt|night|glow on|off  /  fx mode NAME
            std::string k, v; in >> k >> v;
            if (k == "crt") g_fx.crt = v == "on";
            else if (k == "night") g_fx.night = v == "on";
            else if (k == "glow") { g_glow_pref = v == "on"; fx_refresh(); }
            else if (k == "mode") { const int m = mp_enum_value(MP_FX_COLOUR_MODE, v.c_str()); mfx_set_mode(&g_fx, m < 0 ? 0 : m); }
        } else if (c == "bubble") {
            std::string rest; std::getline(in, rest);
            if (!rest.empty() && rest[0] == ' ') rest.erase(0, 1);
            if (rest == "off") g_av->clearSpeech(); else g_av->setSpeech(rest);
        } else if (!render_hook_cmd(g_av, c, in)) {
            fprintf(stderr, "unknown command: %s\n", c.c_str());
        }
    }
    fflush(stdout);
    _exit(0);  // the avatar's destructors walk LVGL objects after the display is gone

}
