// Host renderer for the games (patch UI13): the real LVGL and the unit's own drawing code (maipai_games_draw.h) draw a game pack's screens into
// memory, so every game screen can be looked at without flashing the unit. Commands come from stdin, one per line:
//   load FILE.mpk            parse a pack and build its shapes (the previous game is dropped)
//   lang en|es               the language of the texts
//   state N                  put the game in state N (the number is the state's place in the pack's table)
//   ctr I V                  set counter I
//   board I V                set Tic-Tac-Toe cell I (0 empty, 1 the person, 2 the unit)
//   guides on|off            draw the banner row, drag bar strip and bottom margin lines (y 28, 44 and 224) and the touch regions on the picture
//   t MS / draw             the clock (for motion keyframes) and a draw at that time; snap draws at the present clock
//   snap FILE.png            draw and write the screen as a PNG
//   sheet FILE.png COLS      a grid of every snap so far at half size
// Build: bash scripts/fw-face-render/games_render.sh <firmware tree root> <out dir>
#include <lvgl.h>
#include <zlib.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "maipai_games_core.h"
#include "maipai_games_draw.h"

static uint8_t s_buf[320 * 240 * 2];
static uint32_t tick_cb() { return 1000; }
static void flush_cb(lv_display_t* d, const lv_area_t*, uint8_t*) { lv_display_flush_ready(d); }

static void write_png(const char* path, const std::vector<uint8_t>& rgb, int w, int h)
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
    if (f == nullptr) {
        printf("cannot write %s\n", path);
        return;
    }
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

static uint8_t g_blob[MG_MAX_PACK];
static mg_pack_t g_pack;
static mg_run_t g_run;
static lv_obj_t* g_root = nullptr;
static lv_obj_t* g_obj[MG_MAX_SHAPES];
static uint8_t g_type[MG_MAX_SHAPES], g_text[MG_MAX_SHAPES];
static lv_point_precise_t g_pts[MG_MAX_SHAPES][2];
static mgd::Parts g_mole;
static uint32_t g_now = 1000;
static bool g_es = false, g_guides = false, g_loaded = false;
static std::vector<std::vector<uint8_t>> g_tiles;

static void drop()
{
    if (g_root != nullptr) {
        lv_obj_delete(g_root);
        g_root = nullptr;
    }
    g_loaded = false;
}

static bool load(const char* path)
{
    drop();
    FILE* f = fopen(path, "rb");
    if (f == nullptr) {
        printf("cannot open %s\n", path);
        return false;
    }
    const size_t n = fread(g_blob, 1, sizeof(g_blob), f);
    fclose(f);
    const mg_err_t err = mg_parse(g_blob, n, &g_pack);
    if (err != MG_OK) {
        printf("pack refused: %s\n", mg_err_text(err, 0));
        return false;
    }
    mg_start(&g_run, &g_pack, 0, 7);
    g_root = lv_obj_create(lv_layer_top());
    lv_obj_remove_style_all(g_root);
    lv_obj_remove_flag(g_root, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_set_size(g_root, 320, 240);
    lv_obj_set_pos(g_root, 0, 0);
    lv_obj_set_style_bg_color(g_root, lv_color_black(), 0);
    lv_obj_set_style_bg_opa(g_root, LV_OPA_COVER, 0);
    memset(&g_mole, 0, sizeof(g_mole));
    for (int i = 0; i < g_pack.n_shapes; i++) {
        mg_shape_t s;
        mg_shape_get(&g_pack, i, &s);
        g_type[i] = s.type;
        g_text[i] = s.text;
        g_obj[i]  = mgd::build_shape(g_root, s, g_pts[i], &g_mole);
    }
    mgd::build_drag_bar(g_root);  // patch GM02: the drag bar on every game screen
    g_loaded = true;
    return true;
}

static std::vector<uint8_t> grab()
{
    mgd::draw_state(g_run, g_obj, g_type, g_text, &g_mole, g_es, g_now >= 900 ? g_now - 900 : 0);  // patch GM04: a still picture is taken well after what appeared (no pop in the middle)
    mgd::animate(g_run, g_obj, g_type, g_pts, &g_mole, g_now);  // the springs and easings at this moment
    lv_obj_invalidate(lv_screen_active());
    lv_refr_now(nullptr);
    std::vector<uint8_t> rgb;
    rgb.reserve(320 * 240 * 3);
    for (int i = 0; i < 320 * 240; i++) {
        const uint16_t v = (uint16_t)(s_buf[i * 2] | (s_buf[i * 2 + 1] << 8));
        rgb.push_back((uint8_t)(((v >> 11) & 31) * 255 / 31));
        rgb.push_back((uint8_t)(((v >> 5) & 63) * 255 / 63));
        rgb.push_back((uint8_t)((v & 31) * 255 / 31));
    }
    if (g_guides) {
        auto put = [&](int x, int y, int r, int g, int b) {
            if (x >= 0 && x < 320 && y >= 0 && y < 240) {
                rgb[((size_t)y * 320 + x) * 3] = (uint8_t)r;
                rgb[((size_t)y * 320 + x) * 3 + 1] = (uint8_t)g;
                rgb[((size_t)y * 320 + x) * 3 + 2] = (uint8_t)b;
            }
        };
        for (int x = 0; x < 320; x++) {
            put(x, 27, 255, 0, 255);
            put(x, MG_SAFE_BOTTOM, 255, 0, 255);  // the bottom of the safe area (patch GM01: y 224)
            put(x, MG_DRAG_BOTTOM, 255, 255, 0);  // the end of the drag bar strip (patch GM02)
        }
        for (int i = 0; i < g_pack.n_regions; i++) {  // the touch regions in cyan
            mg_region_t g;
            mg_region_get(&g_pack, i, &g);
            for (int x = g.x; x < g.x + g.w; x++) {
                put(x, g.y, 0, 255, 255);
                put(x, g.y + g.h - 1, 0, 255, 255);
            }
            for (int y = g.y; y < g.y + g.h; y++) {
                put(g.x, y, 0, 255, 255);
                put(g.x + g.w - 1, y, 0, 255, 255);
            }
        }
    }
    return rgb;
}

int main()
{
    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t* d = lv_display_create(320, 240);
    lv_display_set_buffers(d, s_buf, nullptr, sizeof(s_buf), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(d, flush_cb);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB565);
    lv_obj_set_style_bg_color(lv_screen_active(), lv_color_black(), 0);
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream in(line);
        std::string cmd;
        in >> cmd;
        if (cmd.empty() || cmd[0] == '#') {
            continue;
        }
        if (cmd == "load") {
            std::string p;
            in >> p;
            load(p.c_str());
        } else if (cmd == "lang") {
            std::string l;
            in >> l;
            g_es = l == "es";
        } else if (cmd == "guides") {
            std::string l;
            in >> l;
            g_guides = l == "on";
        } else if (cmd == "clear") {
            g_tiles.clear();
        } else if (!g_loaded) {
            printf("no game loaded for: %s\n", line.c_str());
        } else if (cmd == "clear") {  // forget the snaps so far (the next sheet starts fresh)
            g_tiles.clear();
        } else if (cmd == "t") {  // the clock, in ms: motion keyframes are taken at chosen times after a change
            in >> g_now;
        } else if (cmd == "draw") {  // let the player see the change at the present time (starts its motion)
            mgd::draw_state(g_run, g_obj, g_type, g_text, &g_mole, g_es, g_now);
        } else if (cmd == "state") {
            int n;
            in >> n;
            g_run.state = (uint8_t)n;
        } else if (cmd == "ctr") {
            int i, v;
            in >> i >> v;
            if (i >= 0 && i < MG_COUNTERS) g_run.ctr[i] = (int16_t)v;
        } else if (cmd == "board") {
            int i, v;
            in >> i >> v;
            if (i >= 0 && i < MG_BOARD_CELLS) g_run.board[i] = (uint8_t)v;
        } else if (cmd == "snap") {
            std::string path;
            in >> path;
            auto rgb = grab();
            write_png(path.c_str(), rgb, 320, 240);
            g_tiles.push_back(rgb);
            printf("wrote %s\n", path.c_str());
        } else if (cmd == "sheet") {
            std::string path;
            int cols = 3;
            in >> path >> cols;
            const int tw = 160, th = 120, gap = 2;
            const int rows = (int)((g_tiles.size() + cols - 1) / cols);
            const int W = cols * (tw + gap), H = rows * (th + gap);
            std::vector<uint8_t> out((size_t)W * H * 3, 60);
            for (size_t t = 0; t < g_tiles.size(); t++) {
                const int ox = (int)(t % cols) * (tw + gap), oy = (int)(t / cols) * (th + gap);
                for (int y = 0; y < th; y++) {
                    for (int x = 0; x < tw; x++) {
                        for (int c = 0; c < 3; c++) {
                            int sum = 0;
                            for (int dy = 0; dy < 2; dy++)
                                for (int dx = 0; dx < 2; dx++) sum += g_tiles[t][((size_t)(y * 2 + dy) * 320 + (x * 2 + dx)) * 3 + c];
                            out[((size_t)(oy + y) * W + ox + x) * 3 + c] = (uint8_t)(sum / 4);
                        }
                    }
                }
            }
            write_png(path.c_str(), out, W, H);
            printf("wrote %s\n", path.c_str());
        } else {
            printf("unknown command: %s\n", line.c_str());
        }
    }
    return 0;
}
