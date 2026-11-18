// Host renderer: the real LVGL and the real face classes, drawn into memory. Commands come from stdin, one per line:
//   style NAME | emotion NAME | weight L R | speak LEVEL (0 stops) | advance MS | snap FILE.png | colour R G B | cmd ... (see below)
// The look is judged from the PNGs this writes; the unit's own PNGs (scripts/fw-serial.py snap) confirm it at the end.
#include <lvgl.h>
#include <zlib.h>
#include <unistd.h>
#include <time.h>
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
#if __has_include("maipai_overlay_core.h")
#include "maipai_overlay_core.h"  // the overlay engine (disco ball, confetti, rain ...): the unit's own code, drawn over the frame as the flush callback does (patches TA03, O01, O02)
#include "maipai_decor_core.h"
#define MAIPAI_HAVE_OVERLAYS 1
#endif
#if __has_include("maipai_screens.h")
#include "maipai_screens.h"  // maipai_face_paused(): the guard the unit puts around the face update (patch UX06)
#define MAIPAI_HAVE_FACE_PAUSE 1
#endif

int64_t g_fake_us = 1000000;
using namespace stackchan::avatar;

static uint8_t s_buf[320 * 240 * 2];

static double g_flush_px = 0;
static void flush_cb(lv_display_t* d, const lv_area_t* a, uint8_t*)
{
    g_flush_px += (double)(a->x2 - a->x1 + 1) * (a->y2 - a->y1 + 1);
    lv_display_flush_ready(d);
}
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

#ifdef MAIPAI_HAVE_OVERLAYS
// The overlay layers (commands: overlay NAME [INTENSITY 1-3] [SECONDS, 0 = until cleared], ovclear) and the music notes beside the face (notes N, 0 clears), composed over the
// frame exactly as the unit's flush callback does. The notes are drawn from the decor core's own parts (position, size, fade); the head's slant is not drawn.
static mo_layer_t g_ov[2];
static uint32_t g_ov_seed = 1000;
static int g_notes = 0;
static int64_t g_notes_t0_us = 0;

static void blend_px(uint16_t* px, int x, int y, int r, int g, int b, int opa)
{
    if (x < 0 || y < 0 || x > 319 || y > 239 || opa <= 0) return;
    uint16_t v = px[y * 320 + x];
    const int vr = ((v >> 11) & 31) * 255 / 31, vg = ((v >> 5) & 63) * 255 / 63, vb = (v & 31) * 255 / 31;
    const int nr = (vr * (255 - opa) + r * opa) / 255, ng = (vg * (255 - opa) + g * opa) / 255, nb = (vb * (255 - opa) + b * opa) / 255;
    px[y * 320 + x] = (uint16_t)(((nr * 31 / 255) << 11) | ((ng * 63 / 255) << 5) | (nb * 31 / 255));
}

static void draw_notes(uint16_t* px)
{
    if (g_notes <= 0) return;
    md_part_t parts[MD_MAX_PARTS];
    const int n = md_parts_n(MD_NOTES, (uint32_t)((g_fake_us - g_notes_t0_us) / 1000), parts, MD_MAX_PARTS, g_notes);
    for (int i = 0; i < n; i++) {
        const md_part_t& p = parts[i];
        for (int y = -p.h / 2; y <= p.h / 2; y++)
            for (int x = -p.w / 2; x <= p.w / 2; x++) {
                if (p.round && (x * x * 4 * p.h * p.h + y * y * 4 * p.w * p.w) > p.w * p.w * p.h * p.h) continue;
                blend_px(px, 160 + p.x + x, 120 + p.y + y, 255, 255, 255, p.opa);
            }
    }
}

static void compose(const uint8_t* src, uint8_t* dst)
{
    memcpy(dst, src, 320 * 240 * 2);
    uint16_t* px = reinterpret_cast<uint16_t*>(dst);
    mc_t cv = {px, 0, 0, 319, 239, 320, 0};
    for (int l = 0; l < 2; l++) mo_draw(&g_ov[l], &cv);
    draw_notes(px);
}
static void write_png(const char* path, const uint8_t* rgb565) { static uint8_t out[320 * 240 * 2]; compose(rgb565, out); write_rgb_png(path, to_rgb(out), 320, 240); }
static std::vector<uint8_t> tile_rgb(const uint8_t* rgb565) { static uint8_t out[320 * 240 * 2]; compose(rgb565, out); return to_rgb(out); }
static void overlays_step()
{
    for (int l = 0; l < 2; l++) {
        mo_step(&g_ov[l], 33);
        g_ov[l].ndirty = 0;
        if (g_ov[l].id != MO_NONE && mo_done(&g_ov[l])) mo_clear(&g_ov[l]);
    }
}
#else
static void write_png(const char* path, const uint8_t* rgb565) { write_rgb_png(path, to_rgb(rgb565), 320, 240); }
static std::vector<uint8_t> tile_rgb(const uint8_t* rgb565) { return to_rgb(rgb565); }
static void overlays_step() {}
#endif
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

static DefaultAvatar* g_av;
static lv_obj_t* g_scr;

// Draw cost model (patch V10), PERF=1 only: LVGL draws and flushes only the dirty areas, as on the unit, so the flushed pixels
// per frame are what its draw time follows; the host time of a frame is a relative check against the old face.
static double g_inv_px = 0, g_frame_ms = 0;
static int g_frames = 0;
static void inv_cb(lv_event_t* e)
{
    const lv_area_t* a = (const lv_area_t*)lv_event_get_param(e);
    if (a == nullptr) return;
    int x1 = a->x1 < 0 ? 0 : a->x1, y1 = a->y1 < 0 ? 0 : a->y1, x2 = a->x2 > 319 ? 319 : a->x2, y2 = a->y2 > 239 ? 239 : a->y2;
    if (x2 >= x1 && y2 >= y1) g_inv_px += (double)(x2 - x1 + 1) * (y2 - y1 + 1);
}

static void frame()
{
    g_fake_us += 33333;
    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
#ifdef MAIPAI_HAVE_FACE_PAUSE
    if (!maipai_face_paused())
#endif
        g_av->update();
    overlays_step();
    render_hook_frame(g_av);
    lv_timer_handler();
    clock_gettime(CLOCK_MONOTONIC, &t1);
    g_frame_ms += (t1.tv_sec - t0.tv_sec) * 1000.0 + (t1.tv_nsec - t0.tv_nsec) / 1e6;
    g_frames++;
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
    lv_display_set_buffers(d, s_buf, nullptr, sizeof(s_buf), getenv("PERF") ? LV_DISPLAY_RENDER_MODE_PARTIAL : LV_DISPLAY_RENDER_MODE_FULL);  // PERF=1: only the dirty areas are drawn and flushed, as on the unit
    lv_display_set_flush_cb(d, flush_cb);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB565);
    lv_display_add_event_cb(d, inv_cb, LV_EVENT_INVALIDATE_AREA, nullptr);
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
        if (c == "emotion") { std::string n; in >> n; g_av->setEmotion(emo(n)); }
        else if (c == "speak") {
            in >> level;
            speaking = level > 0;
            maipai_speech_set_active(speaking);
        } else if (c == "clock") {
            int64_t ms; in >> ms;  // the fake clock jumps to ms (a unit that has run for days; the tick the faces see wraps at 2^32)
            g_fake_us = ms * 1000;
        } else if (c == "advance") {
            int ms; in >> ms;
            for (int t = 0; t < ms; t += 33) {
                if (speaking) maipai_speech_feed_bench(level);
                frame();
            }
        } else if (c == "snapnow") {   // a picture of this very frame: no frame runs, no time passes (the filmstrips step with advance 33, one frame each)
            std::string f; in >> f;
            write_png(f.c_str(), s_buf);
            printf("snapnow\n"); fflush(stdout);   // the answer is the barrier: no frame runs to wait for it
        } else if (c == "snap") {
            std::string f; in >> f;
            if (speaking) maipai_speech_feed_bench(level);
            frame(); frame();
            write_png(f.c_str(), s_buf);
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
            for (int y = 30; y < 166; y++) for (int x = 12; x < 308; x++) {
                if (x >= 140 && x < 180) continue;
                const int i = (y * 320 + x) * 3;
                if (rgb[i] + rgb[i + 1] + rgb[i + 2] > 3 * 128) n[x < 160 ? 0 : 1]++;
            }
            printf("eyes %d %d\n", n[0], n[1]);
        } else if (c == "perfbegin") {
            g_inv_px = 0; g_flush_px = 0; g_frame_ms = 0; g_frames = 0;
        } else if (c == "perfend") {
            std::string label; in >> label;
            printf("perf %s frames %d flushed_px_per_frame %.0f host_ms_per_frame %.3f\n", label.c_str(), g_frames, g_frames ? g_flush_px / g_frames : 0.0, g_frames ? g_frame_ms / g_frames : 0.0);
        } else if (c == "eyebox") {
            // eyebox YLIM: one frame, then the lit pixels (count and box) of the left half and of the right half above row YLIM, read from
            // the same frame (two `count` commands are two frames apart, and the gaze drifts between them)
            int ylim; in >> ylim;
            if (speaking) maipai_speech_feed_bench(level);
            frame();
            auto rgb = to_rgb(s_buf);
            for (int half = 0; half < 2; half++) {
                int n = 0, minx = 9999, maxx = -1, miny = 9999, maxy = -1;
                for (int y = 20; y < ylim; y++) for (int x = half * 160; x < half * 160 + 160; x++) {
                    const int i = (y * 320 + x) * 3;
                    if (rgb[i] + rgb[i + 1] + rgb[i + 2] > 3 * 128) { n++; minx = x < minx ? x : minx; maxx = x > maxx ? x : maxx; miny = y < miny ? y : miny; maxy = y > maxy ? y : maxy; }
                }
                printf("eyebox %d %d %d %d %d\n", n, minx, miny, maxx, maxy);
            }
        } else if (c == "tile") {
            if (speaking) maipai_speech_feed_bench(level);
            frame(); frame();
            g_tiles.push_back(tile_rgb(s_buf));
        } else if (c == "sheet") {
            std::string f; int cols = 4, div = 2; in >> f >> cols >> div;
            write_sheet(f.c_str(), cols, div);
            g_tiles.clear();
#ifdef MAIPAI_HAVE_OVERLAYS
        } else if (c == "overlay") {
            std::string n; int inten = 2, secs = 0; in >> n >> inten >> secs;
            const int id = mo_id(n.c_str());
            if (id == 0) { fprintf(stderr, "unknown overlay %s\n", n.c_str()); continue; }
            mo_start(&g_ov[mo_layer_of(id)], id, inten, (uint32_t)secs, g_ov_seed++);
        } else if (c == "ovclear") {
            for (int l = 0; l < 2; l++) mo_clear(&g_ov[l]);
        } else if (c == "notes") {
            in >> g_notes;
            g_notes_t0_us = g_fake_us;
#endif
        } else if (!render_hook_cmd(g_av, c, in)) {
            fprintf(stderr, "unknown command: %s\n", c.c_str());
        }
    }
    fflush(stdout);
    _exit(0);  // the avatar's destructors walk LVGL objects after the display is gone

}
