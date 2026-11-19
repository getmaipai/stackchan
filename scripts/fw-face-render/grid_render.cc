// Host renderer for the grid games (Four in a Row, Memory Match, Hangman, Mine Finder): the real LVGL and the unit's own drawing code, cut out of maipai_grid.cc by
// scripts/virtual-unit/grid_gen.py, draw a game in play into memory. The rules and the animation tweens are the unit's cores (maipai_grid_*_core.h). Commands on stdin:
//   game c4|match|hangman|mines [SEED]   start a game (an empty board; layout as the unit's start function)
//   drop COL OWNER                       Four in a Row: a disc of OWNER (1 person, 2 unit) falls into COL, as the unit's c4_drop_disc does
//   tap CELL                             Memory Match: turn a card; reveal CELL (Mine Finder); guess the letter CELL (0 = A, Hangman)
//   flag                                 Mine Finder: switch flagging on or off
//   advance MS                           run the clock in 30 ms ticks (falls, bounces, pulses, flips, pops, the board shake)
//   over won|lost|draw|over|timeup|SCORE TEXT|BEST TEXT|NEWBEST 0 or 1|en or es   the shared game-over screen (patch UX15) over the game, drawn by the unit's own code
//   over ... |en|LOOK|T_MS|PRESSED   (patch UX15d) after the language (en, es, fr, de, pt or it) three more fields, all optional: the look level (0 today's screen, 1 the new look still, 2 moving), the time in
//                                        ms after the screen appeared (the motion is played to it in 30 ms steps), and the pressed button (1 Play again, 2 Quit)
//   overpop T_MS | overpress N           the same screen later: play its motion on to T_MS, or press a button (0 lets go)
//   overwidths                           the width in px of every word of the screen in every language (`word KIND LANG WIDTH`), for the test that none is too wide
//   qa riddle|joke or riddle|WORDS|ANSWER|CHARS SHOWN (-1 all)|REVEALED 0 or 1|en or es   the question and answer game screens (patch UX17)
//   qa trivia|QUESTION|A1;A2;A3;A4|N|TOTAL|SCORE|RESULT 0 1 2|CHOSEN|RIGHT|lang
//   qa twenty|QUESTION|N|GUESS 0 or 1|lang
//   stripadd                             keep this very frame (no time passes) for a filmstrip
//   stripwrite FILE.png COLS             the kept frames at half size, COLS to a row, in one picture
//   swipe X0 Y0 X1 Y1 HELD_MS            a finger down at X0 Y0 and up at X1 Y1 after HELD_MS: the unit's own classification (tap, long press, swipe) steers Snake, slides 2048, taps or flags Mine Finder (patch SF76)
//   tiles E0 .. E15                      2048: set the sixteen tile exponents (0 empty, 1 = 2, 2 = 4 ... 11 = 2048)
//   poker D0 D1 D2 D3 D4|HELD MASK|RE-ROLLS LEFT|ROUND|SCORE|PHASE 0 roll 1 hold|en or es   the Dice Poker screen (patch UX18)
//   hilo CUR NEXT|REVEAL|RESULT 1 right 2 wrong 3 same|STREAK|en or es   the Higher or Lower screen (patch UX21): cards are 0 to 51 (suit * 13 + rank - 1)
//   reversi MOVES|THINKING|en or es                      the Reversi screen (patch UX22): the person's cells (0 to 63) in order, the unit answering each; THINKING 1 stops before the unit's last answer
//   reversi board BOARD64|TURN 1 person 2 unit|LAST|LASTPASS|en or es   a hand-made Reversi position ('.' empty, 'P' person, 'U' unit)
//   battleship SEED|CELLS FIRED AT|en or es    the Battleship-lite screen (patch UX23): the sea of that seed after the shots, in order
//   pong BX BY VX VY|PY UY|PERSON UNIT|en or es   the Pong screen (patch UX24): the ball (px in the court), the paddles' tops, the points
//   flyer SEED|STEPS|BIRD Y|SCORE|PHASE 0 play 1 over|en or es   the flyer screen (patch UX25): the course of that seed scrolled STEPS ticks, the bird at BIRD Y (px)
//   diffbegin / diffend NAME             frame cost: after diffbegin every tick of `advance` and every `play` step is drawn in full and compared with the frame before; diffend prints, for the run,
//                                        `cost NAME frames N changed_px M bbox_px B bbox_px_max X`: the pixels that changed per frame, and the area of their bounding box (what a flush of only the changed rectangle costs)
//   play pong TICKS AIM | play flyer SEED TICKS | play battleship SEED SHOTS | play reversi SEED | play hilo SEED GUESSES    drive a game by itself (a fixed, simple policy) one step per frame, for diffbegin
//   technique NAME N                     (PERF=1) draw one visual technique in a 100 by 100 pixel box N times and print `technique NAME objects O us_per_refresh U flushed_px F` (see docs/plan/games-visual-budget.md)
//   timeit N                             (PERF=1) redraw the whole board N times and print `timeit us_per_redraw U` (host microseconds: a relative cost)
//   look LEVEL                           Four in a Row: 0 plain, 1 gradients and highlights, 2 adds soft shadows (patch UX26, bench only)
//   balance SEED|STEPS|en or es          the Balance screen (patch UX27): the course of that seed after STEPS ticks of the core's own autopilot (a made-up lean)
//   maze SEED|STEPS|en or es             the Maze screen (patch UX28): the maze of that seed after STEPS ticks of the core's own autopilot
//   objcount                             print `objects N labels L`: the LVGL objects on the top layer and how many of them are labels (RAM on the unit)
//   snap FILE.png
// Build: see scripts/virtual-unit/build-screens.sh. Placement: host-side development tool; no firmware change. Upstream: none.
#include <lvgl.h>
#include <zlib.h>
#include <chrono>
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
#if __has_include("maipai_dicepoker.h")
#include "maipai_dicepoker.h"   /* patch UX18: Dice Poker */
#define HAVE_POKER 1
#endif
#if __has_include("maipai_hilo.h")
#include "maipai_hilo.h"   /* patch UX21: Higher or Lower */
#define HAVE_HILO 1
#endif
#if __has_include("maipai_reversi.h")
#include "maipai_reversi.h"   /* patch UX22: Reversi */
#define HAVE_REVERSI 1
#endif
#if __has_include("maipai_battleship.h")
#include "maipai_battleship.h"   /* patch UX23: Battleship-lite */
#define HAVE_BATTLESHIP 1
#endif
#if __has_include("maipai_pong.h")
#include "maipai_pong.h"   /* patch UX24: Pong */
#define HAVE_PONG 1
#endif
#if __has_include("maipai_flyer.h")
#include "maipai_flyer.h"   /* patch UX25: Flappy-style flyer */
#define HAVE_FLYER 1
#endif
#if __has_include("maipai_balance.h")
#include "maipai_balance.h"   /* patch UX27: Balance */
#define HAVE_BALANCE 1
#endif
#if __has_include("maipai_maze.h")
#include "maipai_maze.h"   /* patch UX28: Maze */
#define HAVE_MAZE 1
#endif
#if __has_include("maipai_qa.h")
#include "maipai_qa.h"   /* patch UX17: the question and answer game screens */
#define HAVE_QA 1
#endif
#if __has_include("maipai_game_over.h")
#include "maipai_game_over.h"   /* patch UX15: the shared game-over screen */
#define HAVE_GAME_OVER 1
#endif

#ifdef HAVE_MGO_LOOK
static mgo::Screen s_over = {};   // the game-over screen last built by `over` (patch UX15d)
static uint32_t s_over_t = 0;
#endif
static uint8_t s_buf[320 * 240 * 2];
static uint32_t g_now = 1000;
static std::vector<std::vector<uint8_t>> s_strip;
static uint32_t tick_cb() { return g_now; }
static long s_flushed_px = 0;   // PERF=1: the pixels the display was asked to flush (partial mode: only the dirty areas)
static void flush_cb(lv_display_t* d, const lv_area_t* a, uint8_t*) { s_flushed_px += (long)(a->x2 - a->x1 + 1) * (a->y2 - a->y1 + 1); lv_display_flush_ready(d); }

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

// ---- frame cost (diffbegin / diffend): how much of the glass changes from one frame to the next ----
static std::vector<uint16_t> s_prev;
static bool s_diffing = false, s_have_prev = false;
struct DRect { int x, y, w, h; };
static std::vector<DRect> s_dirty;   // when not empty: the rectangles a game says it changed; diff_frame counts the changed pixels outside them
static long s_d_outside = 0, s_d_dirty = 0, s_d_dirty_max = 0;
static long s_d_frames = 0, s_d_changed = 0, s_d_bbox = 0, s_d_bbox_max = 0, s_d_tiles = 0, s_d_tiles_max = 0;

static void diff_frame()
{
    lv_obj_invalidate(lv_screen_active());
    lv_obj_invalidate(lv_layer_top());
    lv_refr_now(nullptr);
    std::vector<uint16_t> now(320 * 240);
    for (int i = 0; i < 320 * 240; i++) now[i] = (uint16_t)(s_buf[i * 2] | (s_buf[i * 2 + 1] << 8));
    if (s_have_prev) {
        if (!s_dirty.empty()) {   // the area of the rectangles the game invalidated this frame (columns of the screen counted once: a union by 1 px rows)
            long area = 0;
            for (int y = 0; y < 240; y++) for (int x = 0; x < 320; x++) { bool in = false; for (const DRect& r : s_dirty) in |= x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h; area += in; }
            s_d_dirty += area; if (area > s_d_dirty_max) s_d_dirty_max = area;
        }
        int x0 = 999, y0 = 999, x1 = -1, y1 = -1;
        long changed = 0;
        bool tile[15][20] = {};   // 16 by 16 pixel tiles that hold a change: the area a flush of several small dirty rectangles costs
        for (int y = 0; y < 240; y++) for (int x = 0; x < 320; x++) if (now[y * 320 + x] != s_prev[y * 320 + x]) {
            changed++;
            tile[y / 16][x / 16] = true;
            if (!s_dirty.empty()) {
                bool in = false;
                for (const DRect& r : s_dirty) in |= x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h;
                if (!in) { if (s_d_outside < 6 && getenv("DIFFDEBUG")) fprintf(stderr, "outside dirty: frame %ld px %d,%d\n", s_d_frames, x, y); s_d_outside++; }
            }
            if (x < x0) x0 = x;
            if (x > x1) x1 = x;
            if (y < y0) y0 = y;
            if (y > y1) y1 = y;
        }
        const long bbox = changed ? (long)(x1 - x0 + 1) * (y1 - y0 + 1) : 0;
        long tiles = 0;
        for (int ty = 0; ty < 15; ty++) for (int tx = 0; tx < 20; tx++) if (tile[ty][tx]) tiles += 256;
        s_d_tiles += tiles;
        if (tiles > s_d_tiles_max) s_d_tiles_max = tiles;
        s_d_frames++;
        s_d_changed += changed;
        s_d_bbox += bbox;
        if (bbox > s_d_bbox_max) s_d_bbox_max = bbox;
    }
    s_prev = now;
    s_have_prev = true;
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
    lv_display_set_buffers(d, s_buf, nullptr, sizeof(s_buf), getenv("PERF") ? LV_DISPLAY_RENDER_MODE_PARTIAL : LV_DISPLAY_RENDER_MODE_FULL);   // PERF=1: only the dirty areas are drawn and flushed, as on the unit
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
            for (int t = 0; t < ms; t += 30) { g_now += 30; tick(g); if (s_diffing) diff_frame(); }
        } else if (c == "over") {
#ifdef HAVE_GAME_OVER
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 8) f.push_back("");
#ifdef HAVE_MGO_LOOK   /* patch UX15d: the look levels, six languages, the motion and the pressed state */
            {
                static const char* const names[6] = {"en", "es", "fr", "de", "pt", "it"};
                int lang = 0;
                for (int k = 0; k < 6; k++) if (f[4] == names[k]) lang = k;
                const int res = f[0] == "won" ? MGO_WON : f[0] == "lost" ? MGO_LOST : f[0] == "over" ? MGO_OVER : f[0] == "timeup" ? MGO_TIMEUP : MGO_DRAW;
                mgo::g_look = f[5].empty() ? 0 : atoi(f[5].c_str());
                s_over = mgo::build_lang(lv_layer_top(), res, f[1].c_str(), f[2].c_str(), f[3] == "1", lang);
                mgo::g_look = 0;
                s_over_t = 0;
                const uint32_t to = f[6].empty() ? 0 : (uint32_t)atoi(f[6].c_str());
                for (uint32_t tt = 0; tt <= to; tt += 30) mgo::set_pop(s_over, tt);
                if (to > 0) mgo::set_pop(s_over, to);
                if (!f[7].empty()) mgo::set_pressed(s_over, atoi(f[7].c_str()));
            }
#else
#ifdef HAVE_MGO_NEUTRAL   /* patch UX15c: the neutral ends exist; without it the tree's screen has only won, lost and draw */
            const int res = f[0] == "won" ? MGO_WON : f[0] == "lost" ? MGO_LOST : f[0] == "over" ? MGO_OVER : f[0] == "timeup" ? MGO_TIMEUP : MGO_DRAW;
#else
            const int res = f[0] == "won" ? MGO_WON : f[0] == "lost" ? MGO_LOST : MGO_DRAW;
#endif
            mgo::build(lv_layer_top(), res, f[1].c_str(), f[2].c_str(), f[3] == "1", f[4] == "es");
#endif
#else
            printf("this firmware tree has no game-over screen (patch UX15)\n");
#endif
#ifdef HAVE_MGO_LOOK
        } else if (c == "overpop") {
            uint32_t to; in >> to;
            for (uint32_t tt = s_over_t; tt <= to; tt += 30) mgo::set_pop(s_over, tt);
            mgo::set_pop(s_over, to);
            s_over_t = to;
        } else if (c == "overpress") {
            int b; in >> b;
            mgo::set_pressed(s_over, b);
        } else if (c == "overwidths") {
            static const char* const names[6] = {"en", "es", "fr", "de", "pt", "it"};
            for (int lang = 0; lang < MGO_LANGS; lang++) {
                for (int r = MGO_WON; r <= MGO_TIMEUP; r++) printf("word title %s %d\n", names[lang], mgo::pen_text_w(mgo_title_l(r, lang), &lv_font_montserrat_24));
                for (int b = MGO_BTN_AGAIN; b <= MGO_BTN_QUIT; b++) printf("word button %s %d\n", names[lang], mgo::pen_text_w(mgo_button_label_l(b, lang), &lv_font_montserrat_20));
                printf("word newbest %s %d\n", names[lang], mgo::pen_text_w(mgo_new_best_label_l(lang), &lv_font_montserrat_16));
            }
            fflush(stdout);
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
        } else if (c == "poker") {
#ifdef HAVE_POKER
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 7) f.push_back("");
            dp_t pk; dp_init(&pk, 1);
            std::stringstream ds(f[0]); for (int i = 0; i < DP_DICE; i++) { int v = 1; ds >> v; pk.d[i] = (uint8_t)v; }
            pk.held = (uint8_t)atoi(f[1].c_str()); pk.rolls_left = (uint8_t)atoi(f[2].c_str()); pk.round = (uint8_t)atoi(f[3].c_str()); pk.score = (uint16_t)atoi(f[4].c_str());
            pk.phase = (uint8_t)(atoi(f[5].c_str()) ? DP_PHASE_HOLD : DP_PHASE_ROLL);
            dpk::screen(lv_layer_top(), pk, f[6] == "es");
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no Dice Poker (patch UX18)\n");
#endif
        } else if (c == "hilo") {
#ifdef HAVE_HILO
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 5) f.push_back("");
            static hl_t hg;
            hl_init(&hg, 1);
            int cur = 0, nx = 1; std::stringstream cs(f[0]); cs >> cur >> nx;
            for (int i = 0; i < HL_DECK; i++) if (hg.deck[i] == cur) { hg.deck[i] = hg.deck[0]; hg.deck[0] = (uint8_t)cur; break; }
            const bool reveal = atoi(f[1].c_str()) != 0;
            if (reveal) {
                for (int i = 1; i < HL_DECK; i++) if (hg.deck[i] == nx) { hg.deck[i] = hg.deck[1]; hg.deck[1] = (uint8_t)nx; break; }
                hg.pos = 1; hg.last = (uint8_t)nx; hg.last_result = (uint8_t)atoi(f[2].c_str());
            }
            hg.streak = (uint16_t)atoi(f[3].c_str());
            hlo::screen(lv_layer_top(), hg, reveal, f[4] == "es");
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no Higher or Lower (patch UX21)\n");
#endif
        } else if (c == "reversi") {
#ifdef HAVE_REVERSI
            static rv_t rg;
            rv_init(&rg);
            std::string rest; std::getline(in, rest);
            rest = rest.substr(rest.find_first_not_of(' '));
            std::vector<std::string> f;
            {   std::stringstream ss(rest); for (std::string part; std::getline(ss, part, '|');) f.push_back(part); }
            bool es = false;
            if (!f.empty() && f[0].rfind("board ", 0) == 0) {
                while (f.size() < 5) f.push_back("");
                const std::string b = f[0].substr(6);
                for (int i = 0; i < RV_CELLS && i < (int)b.size(); i++) rg.b[i] = b[i] == 'P' ? RV_PERSON : (b[i] == 'U' ? RV_UNIT : RV_EMPTY);
                rg.turn = (uint8_t)atoi(f[1].c_str()); rg.last = (int8_t)atoi(f[2].c_str()); rg.last_pass = (uint8_t)atoi(f[3].c_str());
                if (rv_count_moves(rg.b, RV_PERSON) == 0 && rv_count_moves(rg.b, RV_UNIT) == 0) rg.phase = RV_END;
                es = f[4] == "es";
            } else {
                while (f.size() < 3) f.push_back("");
                std::stringstream ms(f[0]);
                int cell, thinking = atoi(f[1].c_str());
                std::vector<int> cells; while (ms >> cell) cells.push_back(cell);
                for (size_t k = 0; k < cells.size(); k++) {
                    rv_person_move(&rg, cells[k]);
                    while (rg.phase == RV_PLAY && rg.turn == RV_UNIT && !(thinking && k + 1 == cells.size())) rv_unit_move(&rg);
                }
                es = f[2] == "es";
            }
            rvs::screen(lv_layer_top(), &rg, es);
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no Reversi (patch UX22)\n");
#endif
        } else if (c == "battleship") {
#ifdef HAVE_BATTLESHIP
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 3) f.push_back("");
            static bs_t bg;
            bs_init(&bg, (uint32_t)atoi(f[0].c_str()));
            std::stringstream cs(f[1]); int cell; while (cs >> cell) bs_fire(&bg, cell);
            bsh::screen(lv_layer_top(), &bg, f[2] == "es");
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no Battleship-lite (patch UX23)\n");
#endif
        } else if (c == "pong") {
#ifdef HAVE_PONG
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 4) f.push_back("");
            static pg_t pgm;
            pg_init(&pgm, 1);
            int bx = 150, by = 90, vx = 3, vy = 0; std::stringstream bs(f[0]); bs >> bx >> by >> vx >> vy;
            pgm.bx = bx * 16; pgm.by = by * 16; pgm.vx = vx * 16; pgm.vy = vy * 16;
            int py = 76, uy = 76; std::stringstream ps(f[1]); ps >> py >> uy; pgm.py = (int16_t)py; pgm.uy = (int16_t)uy;
            int sp = 0, su = 0; std::stringstream sc(f[2]); sc >> sp >> su; pgm.sp = (uint8_t)sp; pgm.su = (uint8_t)su;
            pgs::screen(lv_layer_top(), &pgm, f[3] == "es");
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no Pong (patch UX24)\n");
#endif
        } else if (c == "flyer") {
#ifdef HAVE_FLYER
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 6) f.push_back("");
            static fl_t fg;
            fl_init(&fg, (uint32_t)atoi(f[0].c_str()));
            const int steps = atoi(f[1].c_str()), by = atoi(f[2].c_str());
            for (int i = 0; i < steps; i++) { fg.y = by * 16; fg.vy = 0; fl_step(&fg); fg.phase = FL_PLAY; }
            fg.y = by * 16; fg.vy = 0; fg.score = (uint16_t)atoi(f[3].c_str()); fg.phase = (uint8_t)(atoi(f[4].c_str()) ? FL_OVER : FL_PLAY);
            flys::screen(lv_layer_top(), &fg, f[5] == "es");
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no flyer (patch UX25)\n");
#endif
        } else if (c == "technique") {
            std::string name; int n = 200; in >> name >> n;
            lv_obj_t* box = lv_obj_create(lv_layer_top());
            lv_obj_remove_style_all(box);
            lv_obj_remove_flag(box, LV_OBJ_FLAG_SCROLLABLE);
            lv_obj_set_pos(box, 110, 70);
            lv_obj_set_size(box, 100, 100);
            lv_obj_set_style_bg_opa(box, LV_OPA_COVER, 0);
            lv_obj_set_style_bg_color(box, lv_color_hex(0x2C3E7A), 0);
            int objects = 1;
            if (name == "radius") lv_obj_set_style_radius(box, 14, 0);
            else if (name == "circle") lv_obj_set_style_radius(box, LV_RADIUS_CIRCLE, 0);
            else if (name == "border") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_border_width(box, 3, 0); lv_obj_set_style_border_color(box, lv_color_hex(0x6A86D8), 0); }
            else if (name == "gradient") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_bg_grad_color(box, lv_color_hex(0x10141C), 0); lv_obj_set_style_bg_grad_dir(box, LV_GRAD_DIR_VER, 0); }
            else if (name == "shadow") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_shadow_width(box, 14, 0); lv_obj_set_style_shadow_offset_y(box, 5, 0); lv_obj_set_style_shadow_color(box, lv_color_black(), 0); lv_obj_set_style_shadow_opa(box, LV_OPA_60, 0); }
            else if (name == "shadow-small") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_shadow_width(box, 6, 0); lv_obj_set_style_shadow_offset_y(box, 2, 0); lv_obj_set_style_shadow_color(box, lv_color_black(), 0); lv_obj_set_style_shadow_opa(box, LV_OPA_60, 0); }
            else if (name == "alpha") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_bg_opa(box, LV_OPA_50, 0); }
            else if (name == "outline") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_outline_width(box, 4, 0); lv_obj_set_style_outline_color(box, lv_color_hex(0xF2B24A), 0); }
            else if (name == "highlight") {   // a soft highlight: a pale rounded strip over the top half (a second object)
                lv_obj_set_style_radius(box, 14, 0);
                lv_obj_t* h = lv_obj_create(box); lv_obj_remove_style_all(h); lv_obj_set_pos(h, 6, 4); lv_obj_set_size(h, 88, 26); lv_obj_set_style_radius(h, 10, 0);
                lv_obj_set_style_bg_opa(h, LV_OPA_20, 0); lv_obj_set_style_bg_color(h, lv_color_white(), 0); objects++;
            }
            else if (name == "particles8" || name == "particles24") {   // small discs spread over the box, one object each
                const int k = name == "particles8" ? 8 : 24;
                lv_obj_set_style_bg_opa(box, LV_OPA_TRANSP, 0);
                for (int i = 0; i < k; i++) { lv_obj_t* p = lv_obj_create(box); lv_obj_remove_style_all(p); lv_obj_set_size(p, 8, 8); lv_obj_set_pos(p, 4 + (i * 37) % 84, 4 + (i * 53) % 84); lv_obj_set_style_radius(p, LV_RADIUS_CIRCLE, 0); lv_obj_set_style_bg_opa(p, LV_OPA_COVER, 0); lv_obj_set_style_bg_color(p, lv_color_hex(0xF2B24A), 0); objects++; }
            }
            else if (name == "label") { lv_obj_t* l = lv_label_create(box); lv_label_set_text(l, "Higher"); lv_obj_set_style_text_font(l, &lv_font_montserrat_20, 0); lv_obj_set_style_text_color(l, lv_color_white(), 0); lv_obj_center(l); objects++; }
            else if (name == "label-scaled") { lv_obj_t* l = lv_label_create(box); lv_label_set_text(l, "K"); lv_obj_set_style_text_font(l, &lv_font_montserrat_20, 0); lv_obj_set_style_text_color(l, lv_color_white(), 0); lv_obj_set_style_transform_scale(l, 512, 0); lv_obj_center(l); objects++; }
            else if (name == "rotate") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_size(box, 70, 70); lv_obj_set_style_transform_rotation(box, 300, 0); }
            else if (name == "squash") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_transform_scale_x(box, 300, 0); lv_obj_set_style_transform_scale_y(box, 200, 0); }
            else if (name == "image-mask") { lv_obj_set_style_radius(box, 14, 0); lv_obj_set_style_clip_corner(box, true, 0); }
            lv_refr_now(nullptr);
            s_flushed_px = 0;
            const auto t0 = std::chrono::steady_clock::now();
            for (int i = 0; i < n; i++) { lv_obj_invalidate(box); lv_refr_now(nullptr); }
            const double us = std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - t0).count() / n;
            printf("technique %s objects %d us_per_refresh %.1f flushed_px %ld\n", name.c_str(), objects, us, s_flushed_px / n);
            fflush(stdout);
            lv_obj_delete(box);
        } else if (c == "timeit") {
            int n = 100; in >> n;
            lv_refr_now(nullptr);
            const auto t0 = std::chrono::steady_clock::now();
            for (int i = 0; i < n; i++) { redraw(g); lv_refr_now(nullptr); }
            const double us = std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - t0).count() / n;
            printf("timeit us_per_redraw %.1f\n", us);
            fflush(stdout);
        } else if (c == "look") {
#ifdef HAVE_LOOK
            int lv = 0; in >> lv; s_look = lv;
            if (g != nullptr) redraw(g);
#else
            printf("this firmware tree has no richer look (patch UX26)\n");
#endif
        } else if (c == "balance") {
#ifdef HAVE_BALANCE
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 3) f.push_back("");
            static bl_t blm;
            bl_init(&blm, (uint32_t)atoi(f[0].c_str()));
            for (int i = 0, n = atoi(f[1].c_str()); i < n && blm.phase == BL_PLAY; i++) { int r, p; bl_autopilot(&blm, &r, &p); bl_step(&blm, r, p); }
            bls::screen(lv_layer_top(), &blm, f[2] == "es");
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no Balance (patch UX27)\n");
#endif
        } else if (c == "maze") {
#ifdef HAVE_MAZE
            std::string rest; std::getline(in, rest);
            std::vector<std::string> f; std::stringstream ss(rest.substr(rest.find_first_not_of(' ')));
            for (std::string part; std::getline(ss, part, '|');) f.push_back(part);
            while (f.size() < 3) f.push_back("");
            static mz_t mzm;
            mz_init(&mzm, (uint32_t)atoi(f[0].c_str()));
            for (int i = 0, n = atoi(f[1].c_str()); i < n && mzm.phase == MZ_PLAY; i++) { int r, p; mz_autopilot(&mzm, &r, &p); mz_step(&mzm, r, p); }
            mzs::screen(lv_layer_top(), &mzm, f[2] == "es");
            lv_refr_now(nullptr);
#else
            printf("this firmware tree has no Maze (patch UX28)\n");
#endif
        } else if (c == "objcount") {
            int objs = 0, labels = 0;
            std::vector<lv_obj_t*> stack{lv_layer_top()};
            while (!stack.empty()) {
                lv_obj_t* o = stack.back(); stack.pop_back();
                const uint32_t n = lv_obj_get_child_count(o);
                for (uint32_t i = 0; i < n; i++) { lv_obj_t* ch = lv_obj_get_child(o, (int32_t)i); objs++; if (lv_obj_check_type(ch, &lv_label_class)) labels++; stack.push_back(ch); }
            }
            printf("objects %d labels %d\n", objs, labels);
            fflush(stdout);
        } else if (c == "diffbegin") {
            s_diffing = true; s_have_prev = false; s_d_frames = s_d_changed = s_d_bbox = s_d_bbox_max = s_d_tiles = s_d_tiles_max = 0;
            s_d_outside = 0; s_d_dirty = s_d_dirty_max = 0;
            diff_frame();   // the first frame is the reference
        } else if (c == "diffend") {
            std::string name; in >> name;
            const long n = s_d_frames ? s_d_frames : 1;
            printf("cost %s frames %ld changed_px %ld bbox_px %ld bbox_px_max %ld tile_px %ld tile_px_max %ld outside_dirty %ld dirty_px %ld dirty_px_max %ld\n", name.c_str(), s_d_frames, s_d_changed / n, s_d_bbox / n, s_d_bbox_max, s_d_tiles / n, s_d_tiles_max, s_d_outside, s_d_dirty / n, s_d_dirty_max);
            fflush(stdout);
            s_diffing = false;
        } else if (c == "play") {
            std::string what; in >> what;
            lv_obj_t* cur = nullptr;
            auto show = [&](lv_obj_t* o) { if (cur) lv_obj_delete(cur); cur = o; diff_frame(); };
#ifdef HAVE_MGO_LOOK
            if (what == "over") {   // patch UX15d: the game-over screen's motion, a frame every 30 ms from RESULT's screen to MS: play over won|lost|draw|over|timeup NEWBEST LOOK MS
                std::string res; int nb, look, ms; in >> res >> nb >> look >> ms;
                const int r = res == "won" ? MGO_WON : res == "lost" ? MGO_LOST : res == "over" ? MGO_OVER : res == "timeup" ? MGO_TIMEUP : MGO_DRAW;
                mgo::g_look = look;
                mgo::Screen sc = mgo::build_lang(lv_layer_top(), r, "Score 120", "Best 90", nb != 0, 0);
                mgo::g_look = 0;
                cur = sc.root;
                diff_frame();   // the screen appears: the whole glass changes, as it does for every game-over look, so the numbers below start from the first frame of the screen itself
                s_have_prev = false; s_d_frames = s_d_changed = s_d_bbox = s_d_bbox_max = s_d_tiles = s_d_tiles_max = 0; s_d_outside = 0; s_d_dirty = s_d_dirty_max = 0;
                diff_frame();
                uint32_t before = 0;
                for (int tt = 30; tt <= ms; tt += 30) {
                    mgo_rect_t rr[MGO2_MAX_RECTS];
                    const int nr = sc.st != nullptr ? mgo_dirty(r, nb, sc.st->num_len, before, (uint32_t)tt, rr) : 0;
                    s_dirty.clear();
                    if (sc.st != nullptr && look >= MGO_LOOK_FULL) for (int i = 0; i < nr; i++) s_dirty.push_back({rr[i].x, rr[i].y, rr[i].w, rr[i].h});
                    mgo::set_pop(sc, (uint32_t)tt);
                    diff_frame();
                    before = (uint32_t)tt;
                }
                s_dirty.clear();
            }
#endif
#ifdef HAVE_PONG
            if (what == "pong") {
                int ticks, aim; in >> ticks >> aim;
                static pg_t pgp; pg_init(&pgp, 3);
                show(pgs::screen(lv_layer_top(), &pgp, false));
                #ifdef PG_DIRTY_API
                for (int t = 0; t < ticks && pgp.phase == PG_PLAY; t++) {
                    const pg_t before = pgp;
                    pg_drag(&pgp, pg_ball_cy(&pgp) + (pgp.vx < 0 ? aim : 0)); pg_step(&pgp);
                    pg_rect_t rr[5]; const int nr = pg_dirty(&before, &pgp, rr);
                    s_dirty.clear(); for (int i = 0; i < nr; i++) s_dirty.push_back({rr[i].x, rr[i].y, rr[i].w, rr[i].h});
                    show(pgs::screen(lv_layer_top(), &pgp, false));
                }
                s_dirty.clear();
#else
                for (int t = 0; t < ticks && pgp.phase == PG_PLAY; t++) { pg_drag(&pgp, pg_ball_cy(&pgp) + (pgp.vx < 0 ? aim : 0)); pg_step(&pgp); show(pgs::screen(lv_layer_top(), &pgp, false)); }
#endif
            }
#endif
#ifdef HAVE_FLYER
            if (what == "flyer") {
                int seed, ticks; in >> seed >> ticks;
                static fl_t flp; fl_init(&flp, (uint32_t)seed);
                show(flys::screen(lv_layer_top(), &flp, false));
                for (int t = 0; t < ticks && flp.phase == FL_PLAY; t++) {
                    int next = -1;
                    for (int i = 0; i < FL_PIPES; i++) if (flp.px[i] + FL_PIPE_W * 16 >= FL_BIRD_X * 16 && (next < 0 || flp.px[i] < flp.px[next])) next = i;
                    const int mid = next >= 0 ? flp.gap[next] + FL_GAP / 2 : (FL_TOP + FL_BOTTOM) / 2;
                    if (fl_bird_top(&flp) + FL_BIRD / 2 > mid + 14 && flp.vy >= 0) fl_tap(&flp);
#ifdef FL_DIRTY_API
                    const fl_t before = flp;
                    fl_step(&flp);
                    fl_rect_t rr[FL_PIPES * 4 + 2]; const int nr = fl_dirty(&before, &flp, rr);
                    s_dirty.clear(); for (int i = 0; i < nr; i++) s_dirty.push_back({rr[i].x, rr[i].y, rr[i].w, rr[i].h});
#else
                    fl_step(&flp);
#endif
                    show(flys::screen(lv_layer_top(), &flp, false));
                }
                s_dirty.clear();
            }
#endif
#ifdef HAVE_BATTLESHIP
            if (what == "battleship") {
                int seed, shots; in >> seed >> shots;
                static bs_t bsp; bs_init(&bsp, (uint32_t)seed);
                show(bsh::screen(lv_layer_top(), &bsp, false));
                for (int i = 0, fired = 0; i < BS_CELLS && fired < shots && bsp.phase == BS_PLAY; i++) if (((i / 6 + i % 6) % 2) == 0) { bs_fire(&bsp, i); fired++; show(bsh::screen(lv_layer_top(), &bsp, false)); }
            }
#endif
#ifdef HAVE_REVERSI
            if (what == "reversi") {
                int seed; in >> seed;
                static rv_t rvp; rv_init(&rvp);
                show(rvs::screen(lv_layer_top(), &rvp, false));
                uint32_t r = (uint32_t)seed;
                for (int guard = 0; guard < 140 && rvp.phase == RV_PLAY; guard++) {
                    if (rvp.turn == RV_PERSON) {
                        int cells[64], n = 0;
                        for (int i = 0; i < RV_CELLS; i++) if (rv_legal(&rvp, i, RV_PERSON)) cells[n++] = i;
                        r = r * 1664525u + 1013904223u;
                        rv_person_move(&rvp, cells[(r >> 8) % (uint32_t)n]);
                    } else rv_unit_move(&rvp);
                    show(rvs::screen(lv_layer_top(), &rvp, false));
                }
            }
#endif
#ifdef HAVE_HILO
            if (what == "hilo") {
                int seed, guesses; in >> seed >> guesses;
                static hl_t hlp; hl_init(&hlp, (uint32_t)seed);
                show(hlo::screen(lv_layer_top(), hlp, false, false));
                for (int i = 0; i < guesses && hlp.phase == HL_PLAY; i++) {
                    hl_guess(&hlp, hl_rank(hl_current(&hlp)) <= 7);
                    show(hlo::screen(lv_layer_top(), hlp, true, false));
                    if (hlp.phase == HL_PLAY) show(hlo::screen(lv_layer_top(), hlp, false, false));
                }
            }
#endif
#ifdef HAVE_BALANCE
            if (what == "balance") {
                int seed, ticks; in >> seed >> ticks;
                static bl_t blp; bl_init(&blp, (uint32_t)seed);
                show(bls::screen(lv_layer_top(), &blp, false));
                for (int t = 0; t < ticks && blp.phase == BL_PLAY; t++) {
                    const bl_t before = blp;
                    int r, p; bl_autopilot(&blp, &r, &p); bl_step(&blp, r, p);
                    bl_rect_t rr[6]; const int nr = bl_dirty(&before, &blp, rr);
                    s_dirty.clear(); for (int i = 0; i < nr; i++) s_dirty.push_back({rr[i].x, rr[i].y, rr[i].w, rr[i].h});
                    show(bls::screen(lv_layer_top(), &blp, false));
                }
                s_dirty.clear();
            }
#endif
#ifdef HAVE_MAZE
            if (what == "maze") {
                int seed, ticks; in >> seed >> ticks;
                static mz_t mzp; mz_init(&mzp, (uint32_t)seed);
                show(mzs::screen(lv_layer_top(), &mzp, false));
                for (int t = 0; t < ticks && mzp.phase == MZ_PLAY; t++) {
                    const mz_t before = mzp;
                    int r, p; mz_autopilot(&mzp, &r, &p); mz_step(&mzp, r, p);
                    mz_rect_t rr[4]; const int nr = mz_dirty(&before, &mzp, rr);
                    s_dirty.clear(); for (int i = 0; i < nr; i++) s_dirty.push_back({rr[i].x, rr[i].y, rr[i].w, rr[i].h});
                    show(mzs::screen(lv_layer_top(), &mzp, false));
                }
                s_dirty.clear();
            }
#endif
            if (cur) lv_obj_delete(cur);
        } else if (c == "snap") {
            std::string f; in >> f; snap(f.c_str());
        }
    }
    return 0;
}
