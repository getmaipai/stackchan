// Host renderer for the grid games (Four in a Row, Memory Match, Hangman, Mine Finder): the real LVGL and the unit's own drawing code, cut out of maipai_grid.cc by
// scripts/virtual-unit/grid_gen.py, draw a game in play into memory. The rules and the animation tweens are the unit's cores (maipai_grid_*_core.h). Commands on stdin:
//   game c4|match|hangman|mines [SEED]   start a game (an empty board; layout as the unit's start function)
//   drop COL OWNER                       Four in a Row: a disc of OWNER (1 person, 2 unit) falls into COL, as the unit's c4_drop_disc does
//   tap CELL                             Memory Match: turn a card; reveal CELL (Mine Finder); guess the letter CELL (0 = A, Hangman)
//   flag                                 Mine Finder: switch flagging on or off
//   advance MS                           run the clock in 30 ms ticks (falls, bounces, pulses, flips, pops, the board shake)
//   over won|lost|draw|SCORE TEXT|BEST TEXT|NEWBEST 0 or 1|en or es   the shared game-over screen (patch UX15) over the game, drawn by the unit's own code
//   qa riddle|joke or riddle|WORDS|ANSWER|CHARS SHOWN (-1 all)|REVEALED 0 or 1|en or es   the question and answer game screens (patch UX17)
//   qa trivia|QUESTION|A1;A2;A3;A4|N|TOTAL|SCORE|RESULT 0 1 2|CHOSEN|RIGHT|lang
//   qa twenty|QUESTION|N|GUESS 0 or 1|lang
//   stripadd                             keep this very frame (no time passes) for a filmstrip
//   stripwrite FILE.png COLS             the kept frames at half size, COLS to a row, in one picture
//   swipe X0 Y0 X1 Y1 HELD_MS            a finger down at X0 Y0 and up at X1 Y1 after HELD_MS: the unit's own classification (tap, long press, swipe) steers Snake, slides 2048, taps or flags Mine Finder (patch SF76)
//   tiles E0 .. E15                      2048: set the sixteen tile exponents (0 empty, 1 = 2, 2 = 4 ... 11 = 2048)
//   snap FILE.png
// Build: see scripts/virtual-unit/build-screens.sh. Placement: host-side development tool; no firmware change. Upstream: none.
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
#include "maipai_grid_core.h"
#include "maipai_grid_c4_core.h"
#include "maipai_grid_mem_core.h"
#include "maipai_grid_hangman_core.h"
#include "maipai_grid_mines_core.h"
#include "maipai_grid_anim_core.h"
#if __has_include("maipai_grid_slide_core.h")
#include "maipai_gesture_core.h"
#include "maipai_grid_slide_core.h"   /* patch SF77: 2048 */
#include "maipai_grid_snake_core.h"   /* patch SF77: Snake */
#include "maipai_grid_input_core.h"   /* patch SF76: swipes and long press */
#define HAVE_SLIDE_SNAKE 1
#endif
#include "maipai_games_sfx_core.h"
#include "maipai_games_draw.h"
#if __has_include("maipai_qa.h")
#include "maipai_qa.h"   /* patch UX17: the question and answer game screens */
#define HAVE_QA 1
#endif
#if __has_include("maipai_game_over.h")
#include "maipai_game_over.h"   /* patch UX15: the shared game-over screen */
#define HAVE_GAME_OVER 1
#endif

static uint8_t s_buf[320 * 240 * 2];
static uint32_t g_now = 1000;
static std::vector<std::vector<uint8_t>> s_strip;
static uint32_t tick_cb() { return g_now; }
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


namespace {
uint32_t now_ms() { return g_now; }
}
#include "grid_draw_gen.h"

static void snap(const char* path)
{
    lv_refr_now(nullptr);
    std::vector<uint8_t> rgb;
    for (int i = 0; i < 320 * 240; i++) {
        const uint16_t v = (uint16_t)(s_buf[i * 2] | (s_buf[i * 2 + 1] << 8));
        rgb.push_back((uint8_t)(((v >> 11) & 31) * 255 / 31));
        rgb.push_back((uint8_t)(((v >> 5) & 63) * 255 / 63));
        rgb.push_back((uint8_t)((v & 31) * 255 / 31));
    }
    write_png(path, rgb, 320, 240);
}

static void c4_land(Grid* g, int owner)
{
    const int res = gc4_result(&g->c4);
    if (res == GR_PLAYING) return;
    g->result_pending = (uint8_t)res;
    if (res == GR_PERSON_WON || res == GR_UNIT_WON) {
        if (gc4_win_line(&g->c4, res == GR_PERSON_WON ? 1 : 2, g->win_cells)) {
            g->flash_left = 4;
            for (int k = 0; k < 4; k++) gan_flash(&g->anim, now_ms(), g->win_cells[k]);
            return;
        }
    }
    gan_shake(&g->anim, now_ms());
}

static void tick(Grid* g)
{
    gan_ev_t ev[GAN_EV_MAX];
    const int n = gan_tick(&g->anim, g_now, ev);
    for (int k = 0; k < n; k++) {
        if (g->kind != kC4) continue;
        if (ev[k].type == GAN_EV_FALL_DONE) c4_land(g, ev[k].owner);
        else if (ev[k].type == GAN_EV_FLASH_DONE) { if (g->flash_left > 0) g->flash_left--; if (g->flash_left == 0) g->win_lit = 1; }
    }
#ifdef HAVE_SLIDE_SNAKE
    if (g->kind == kSnake && g->result == GR_PLAYING && (int32_t)(g_now - g->next_step_ms) >= 0) {
        const int r = gsn_step(&g->snake);
        g->next_step_ms = g_now + gsn_interval_ms(&g->snake);
        if (r == GSN_DIED) g->result = GR_UNIT_WON;
        else if (r == GSN_WON) g->result = GR_PERSON_WON;
    }
#endif
    if (g->kind == kMatch) {
        const int p0 = g->mem.pending[0], p1 = g->mem.pending[1];
        if (gm_tick(&g->mem, g_now)) {
#ifdef GAN_FLIP_MS   /* patch SF74 is in the tree */
            if (p0 >= 0) gan_flip(&g->anim, g_now, p0);
            if (p1 >= 0) gan_flip(&g->anim, g_now, p1);
#endif
        }
    }
    if (g->board != nullptr) lv_obj_invalidate(g->board);
}

int main()
{
    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t* d = lv_display_create(320, 240);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(d, s_buf, nullptr, sizeof(s_buf), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(d, flush_cb);
    lv_obj_set_style_bg_color(lv_screen_active(), lv_color_black(), 0);
    static const char* const kWords[] = {"robot", "planet", "garden", "rocket"};
    Grid* g = nullptr;
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream in(line);
        std::string c;
        in >> c;
        if (c == "game") {
            std::string k; uint32_t seed = 7; in >> k >> seed;
            g = (Grid*)calloc(1, sizeof(Grid));
            s_grid = g;
            g->kind = k == "c4" ? kC4 : k == "match" ? kMatch : k == "hangman" ? kHangman : k == "slide" ? kSlide : k == "snake" ? kSnake : kMines;
            g->seed = seed;
            if (g->kind == kC4) { gr_layout(&g->lay, GC4_COLS, GC4_ROWS, 0); gc4_clear(&g->c4); }
            else if (g->kind == kHangman) { gh_init(&g->hang, kWords[seed % 4], GH_MAX_MISS); g->lay.cols = 9; g->lay.rows = 3; g->lay.cw = 31; g->lay.ch = 32; g->lay.x0 = 20; g->lay.y0 = 126; }
            else if (g->kind == kMines) { gmn_init(&g->mines, seed); gr_layout(&g->lay, GMN_COLS, GMN_ROWS, 1); g->lay.x0 = 52; }
#ifdef HAVE_SLIDE_SNAKE
            else if (g->kind == kSlide) { gsl_init(&g->slide, seed); gr_layout(&g->lay, GS_N, GS_N, 1); g->spawn_cell = 255; }
            else if (g->kind == kSnake) { gsn_init(&g->snake, seed); gr_layout(&g->lay, GSN_COLS, GSN_ROWS, 0); g->next_step_ms = g_now + 1600; }
#endif
            else { gm_init(&g->mem, 16, seed); gr_layout(&g->lay, 4, 4, 1); }
            gan_init(&g->anim);
            build(g);
            lv_obj_invalidate(g->board);
        } else if (g == nullptr) {
            printf("start a game first: game c4|match|hangman|mines\n");
        } else if (c == "drop") {
            int col, owner; in >> col >> owner;
            const int row = gc4_drop(&g->c4, col, owner);
            if (row < 0) { printf("column %d is full\n", col); continue; }
            const int cell = row * g->lay.cols + col;
            gan_fall(&g->anim, g_now, cell, owner, row, row + 1, g->lay.y0 - g->lay.ch, g->lay.y0 + row * g->lay.ch + 3);
        } else if (c == "tap") {
            int i; in >> i;
            if (g->kind == kMatch) { if (gm_tap(&g->mem, i, g_now)) {
#ifdef GAN_FLIP_MS
                gan_flip(&g->anim, g_now, i);
#endif
            } }
            else if (g->kind == kMines) { gmn_reveal(&g->mines, i);
#ifdef GAN_POP_MS
                gan_pop(&g->anim, g_now, i);
#endif
            }
            else if (g->kind == kHangman) { gh_guess(&g->hang, (char)('A' + i));
#ifdef GAN_POP_MS
                gan_pop(&g->anim, g_now, i);
#endif
            }
        } else if (c == "swipe" || c == "tiles") {
#ifdef HAVE_SLIDE_SNAKE
            if (c == "tiles") { for (int i = 0; i < GS_N * GS_N; i++) { int e = 0; in >> e; g->slide.t[i] = (uint8_t)e; } g->spawn_cell = 255; continue; }
            int x0, y0, x1, y1, held; in >> x0 >> y0 >> x1 >> y1 >> held;
            const int what = gi_classify(x0, y0, x1, y1, (uint32_t)held);
            if (g->kind == kSnake) {
                if (what == GI_SWIPE_LEFT) gsn_turn(&g->snake, GSN_LEFT); else if (what == GI_SWIPE_RIGHT) gsn_turn(&g->snake, GSN_RIGHT);
                else if (what == GI_SWIPE_UP) gsn_turn(&g->snake, GSN_UP); else if (what == GI_SWIPE_DOWN) gsn_turn(&g->snake, GSN_DOWN);
            } else if (g->kind == kSlide) {
                const int dir = what == GI_SWIPE_LEFT ? GS_LEFT : what == GI_SWIPE_RIGHT ? GS_RIGHT : what == GI_SWIPE_UP ? GS_UP : what == GI_SWIPE_DOWN ? GS_DOWN : -1;
                uint8_t before[GS_N * GS_N]; memcpy(before, g->slide.t, sizeof(before));
                if (dir >= 0 && gsl_slide(&g->slide, dir)) {
                    for (int i = 0; i < GS_N * GS_N; i++) if (g->slide.t[i] != 0 && before[i] == 0 && (g->slide.t[i] == 1 || g->slide.t[i] == 2)) { gan_pop(&g->anim, g_now, i); break; }
                    if (gsl_result(&g->slide) != GR_PLAYING) g->result = gsl_result(&g->slide);
                }
            } else if (g->kind == kMines) {
                const int cell = gr_cell_at(&g->lay, x0, y0);
                if (cell >= 0 && what == GI_LONG) gmn_flag(&g->mines, cell);
                else if (cell >= 0 && what == GI_TAP) { gmn_reveal(&g->mines, cell); gan_pop(&g->anim, g_now, cell); }
            }
            if (g->board != nullptr) lv_obj_invalidate(g->board);
#else
            printf("this firmware tree has no swipe inputs (patch SF76)\n");
#endif
        } else if (c == "flag") {
            g->flag_mode = !g->flag_mode;
        } else if (c == "advance") {
            int ms; in >> ms;
            for (int t = 0; t < ms; t += 30) { g_now += 30; tick(g); }
        } else if (c == "over") {
#ifdef HAVE_GAME_OVER
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 5) f.push_back("");
            const int res = f[0] == "won" ? MGO_WON : f[0] == "lost" ? MGO_LOST : MGO_DRAW;
            mgo::build(lv_layer_top(), res, f[1].c_str(), f[2].c_str(), f[3] == "1", f[4] == "es");
#else
            printf("this firmware tree has no game-over screen (patch UX15)\n");
#endif
        } else if (c == "qa") {
#ifdef HAVE_QA
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 12) f.push_back("");
            static std::vector<std::string> keep;   // the label texts outlive this command
            if (f[0] == "riddle") {
                mqa::riddle(lv_layer_top(), f[1] == "joke", f[2].c_str(), f[4].empty() ? -1 : atoi(f[4].c_str()), f[3].c_str(), f[5] == "1", f[6] == "es");
            } else if (f[0] == "trivia") {
                std::vector<std::string> ans; std::stringstream as(f[2]);
                for (std::string a; std::getline(as, a, ';');) ans.push_back(a);
                const char* ap[4] = {"", "", "", ""};
                for (size_t i = 0; i < ans.size() && i < 4; i++) ap[i] = ans[i].c_str();
                mqa::trivia(lv_layer_top(), f[1].c_str(), ap, (int)ans.size(), atoi(f[3].c_str()), atoi(f[4].c_str()), atoi(f[5].c_str()), atoi(f[6].c_str()), atoi(f[7].c_str()), atoi(f[8].c_str()), f[9] == "es");
            } else if (f[0] == "twenty") {
                mqa::twenty(lv_layer_top(), f[1].c_str(), atoi(f[2].c_str()), f[3] == "1", f[4] == "es");
            }
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no question and answer screens (patch UX17)\n");
#endif
        } else if (c == "stripadd") {
            lv_refr_now(nullptr);
            std::vector<uint8_t> rgb;
            for (int i = 0; i < 320 * 240; i++) {
                const uint16_t v = (uint16_t)(s_buf[i * 2] | (s_buf[i * 2 + 1] << 8));
                rgb.push_back((uint8_t)(((v >> 11) & 31) * 255 / 31)); rgb.push_back((uint8_t)(((v >> 5) & 63) * 255 / 63)); rgb.push_back((uint8_t)((v & 31) * 255 / 31));
            }
            s_strip.push_back(rgb);
        } else if (c == "stripwrite") {
            std::string f; int cols = 3; in >> f >> cols;
            const int n = (int)s_strip.size(), rows = (n + cols - 1) / cols, W = 160, H = 120;
            std::vector<uint8_t> out((size_t)cols * W * rows * H * 3, 0);
            for (int k = 0; k < n; k++) {
                const int ox = (k % cols) * W, oy = (k / cols) * H;
                for (int y = 0; y < H; y++) for (int x = 0; x < W; x++) for (int ch = 0; ch < 3; ch++) {
                    const auto& src = s_strip[k];
                    const int a = src[((2 * y) * 320 + 2 * x) * 3 + ch] + src[((2 * y) * 320 + 2 * x + 1) * 3 + ch] + src[((2 * y + 1) * 320 + 2 * x) * 3 + ch] + src[((2 * y + 1) * 320 + 2 * x + 1) * 3 + ch];
                    out[(((size_t)(oy + y)) * cols * W + ox + x) * 3 + ch] = (uint8_t)((a + 2) / 4);
                }
            }
            write_png(f.c_str(), out, cols * W, rows * H);
            s_strip.clear();
        } else if (c == "snap") {
            std::string f; in >> f; snap(f.c_str());
        }
    }
    return 0;
}
