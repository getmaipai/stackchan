// Host renderer for the grid games (Four in a Row, Memory Match, Hangman, Mine Finder): the real LVGL and the unit's own drawing code, cut out of maipai_grid.cc by
// scripts/virtual-unit/grid_gen.py, draw a game in play into memory. The rules and the animation tweens are the unit's cores (maipai_grid_*_core.h). Commands on stdin:
//   game c4|match|hangman|mines [SEED]   start a game (an empty board; layout as the unit's start function)
//   drop COL OWNER                       Four in a Row: a disc of OWNER (1 person, 2 unit) falls into COL, as the unit's c4_drop_disc does
//   tap CELL                             Memory Match: turn a card; reveal CELL (Mine Finder); guess the letter CELL (0 = A, Hangman)
//   flag                                 Mine Finder: switch flagging on or off
//   advance MS                           run the clock in 30 ms ticks (falls, bounces, pulses, flips, pops, the board shake)
//   over won|lost|draw|over|timeup|SCORE TEXT|BEST TEXT|NEWBEST 0 or 1|en or es   the shared game-over screen (patch UX15) over the game, drawn by the unit's own code
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
#ifdef HAVE_MGO_NEUTRAL   /* patch UX15c: the neutral ends exist; without it the tree's screen has only won, lost and draw */
            const int res = f[0] == "won" ? MGO_WON : f[0] == "lost" ? MGO_LOST : f[0] == "over" ? MGO_OVER : f[0] == "timeup" ? MGO_TIMEUP : MGO_DRAW;
#else
            const int res = f[0] == "won" ? MGO_WON : f[0] == "lost" ? MGO_LOST : MGO_DRAW;
#endif
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
        } else if (c == "snap") {
            std::string f; in >> f; snap(f.c_str());
        }
    }
    return 0;
}
