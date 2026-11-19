/* Host test for the swipe pages data and layout (patch P11): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> pages_core_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_pages_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

static void test_defaults_and_strip(void)
{
    mpg_cfg_t c;
    mpg_defaults(&c);
    CHECK(c.n_left == 1 && c.left[0] == MPG_P_CLOCK);
    CHECK(c.n_right == 1 && c.right[0] == MPG_P_GAMES);
    CHECK(c.sheet_s == 10 && c.idle_s == 20);   /* patch UI01: the sheet stays 10 s, it was 6 */
    CHECK(c.n_actions == 4 && c.actions[0] == MPG_A_BEEP && c.actions[3] == MPG_A_HELLO);
    CHECK(c.n_items == 9 && c.items[0] == MPG_S_VOLUME);
    CHECK(mpg_page_at(&c, -1) == MPG_P_CLOCK);
    CHECK(mpg_page_at(&c, 1) == MPG_P_GAMES);
    CHECK(mpg_page_at(&c, 0) == -1 && mpg_page_at(&c, -2) == -1 && mpg_page_at(&c, 2) == -1);
    CHECK(mpg_pos_of(&c, MPG_P_CLOCK) == -1 && mpg_pos_of(&c, MPG_P_GAMES) == 1 && mpg_pos_of(&c, MPG_P_TILES) == 0);
}

static void test_set_pages(void)
{
    mpg_cfg_t c;
    mpg_defaults(&c);
    int l[3] = {MPG_P_TIMERS, MPG_P_CLOCK, MPG_P_FRAME}, r[3] = {MPG_P_GAMES, MPG_P_ACTIONS, MPG_P_TILES};
    CHECK(mpg_set_pages(&c, l, 3, r, 3) == NULL);
    CHECK(c.n_left == 3 && c.n_right == 3);
    CHECK(mpg_page_at(&c, -1) == MPG_P_TIMERS && mpg_page_at(&c, -3) == MPG_P_FRAME && mpg_page_at(&c, 3) == MPG_P_TILES);
    CHECK(mpg_pos_of(&c, MPG_P_ACTIONS) == 2);
    mpg_cfg_t keep = c;
    /* a page twice, in any combination, is refused and nothing changes */
    int dup[2] = {MPG_P_CLOCK, MPG_P_CLOCK};
    CHECK(mpg_set_pages(&c, dup, 2, r, 0) != NULL && memcmp(&c, &keep, sizeof(c)) == 0);
    int one[1] = {MPG_P_CLOCK};
    CHECK(mpg_set_pages(&c, one, 1, one, 1) != NULL);
    CHECK(mpg_set_pages(&c, l, 4, r, 0) != NULL);
    int bad[1] = {9};
    CHECK(mpg_set_pages(&c, bad, 1, r, 0) != NULL);
    CHECK(memcmp(&c, &keep, sizeof(c)) == 0);
    /* nothing at all is allowed: the unit then has no pages and the face is the only screen */
    CHECK(mpg_set_pages(&c, l, 0, r, 0) == NULL && c.n_left == 0 && c.n_right == 0);
    CHECK(mpg_page_at(&c, -1) == -1 && mpg_page_at(&c, 1) == -1);
}

static void test_timeouts_actions_items(void)
{
    mpg_cfg_t c;
    mpg_defaults(&c);
    CHECK(mpg_set_timeouts(&c, 30, 300) == NULL && c.sheet_s == 30 && c.idle_s == 300);
    CHECK(mpg_set_timeouts(&c, 31, 0) != NULL && c.sheet_s == 30);
    CHECK(mpg_set_timeouts(&c, 7, 0) != NULL && mpg_set_timeouts(&c, 5, 0) != NULL);   /* the old 5 to 7 are refused */
    CHECK(mpg_set_timeouts(&c, 0, 4) != NULL && mpg_set_timeouts(&c, 0, 301) != NULL && c.idle_s == 300);
    CHECK(mpg_set_timeouts(&c, 0, 0) == NULL);  /* 0 leaves a value as it is */
    CHECK(mpg_set_timeouts(&c, 8, 5) == NULL && c.sheet_s == 8 && c.idle_s == 5);
    int a4[4] = {MPG_A_HELLO, MPG_A_BEEP, MPG_A_DANCE, MPG_A_GAME};
    CHECK(mpg_set_actions(&c, a4, 4) == NULL && c.n_actions == 4 && c.actions[0] == MPG_A_HELLO);
    CHECK(mpg_set_actions(&c, a4, 2) == NULL && c.n_actions == 2);
    CHECK(mpg_set_actions(&c, a4, 1) != NULL);   /* fewer than two */
    CHECK(mpg_set_actions(&c, a4, 5) != NULL);   /* more than four */
    int rep[4] = {MPG_A_BEEP, MPG_A_BEEP, MPG_A_DANCE, MPG_A_GAME};
    CHECK(mpg_set_actions(&c, rep, 4) != NULL && c.n_actions == 2);
    /* patch SF59: the camera switch is an action; it is the default third tile, works in full quiet and under a mute, and is accepted by name */
    CHECK(mpg_action_blocked(MPG_A_VISION, 1, 0) == 0 && mpg_action_blocked(MPG_A_VISION, 0, 1) == 0 && mpg_action_blocked(MPG_A_DANCE, 1, 0) == 1);
    int vis[4] = {MPG_A_BEEP, MPG_A_DANCE, MPG_A_VISION, MPG_A_HELLO};
    CHECK(mpg_set_actions(&c, vis, 4) == NULL && c.actions[2] == MPG_A_VISION);
    int unk[4] = {MPG_A_BEEP, MPG_A_DANCE, MPG_A_GAME, 9};
    CHECK(mpg_set_actions(&c, unk, 4) != NULL);
    CHECK(mpg_action_by_name("find") == -1 && mpg_sheet_by_name("find") == -1);   /* find me is gone; the saved text path drops it */
    int it[12];
    for (int i = 0; i < 12; i++) it[i] = i;
    int ok[12];
    int n = 0;
    ok[n++] = MPG_S_VOLUME;
    ok[n++] = MPG_S_BRIGHTNESS;
    ok[n++] = MPG_S_MUTE;
    ok[n++] = MPG_S_QUIET;
    ok[n++] = MPG_S_LOCK;
    ok[n++] = MPG_S_TIMERS;
    ok[n++] = MPG_S_GAMES;
    ok[n++] = MPG_S_WIFI;
    ok[n++] = MPG_S_BATTERY;
    ok[n++] = MPG_S_TAILNET;
    ok[n++] = MPG_S_ADDRESS;
    CHECK(mpg_set_items(&c, ok, 11) == NULL && c.n_items == 11);
    ok[1] = MPG_S_VOLUME;
    CHECK(mpg_set_items(&c, ok, 11) != NULL);    /* a repeat */
    int none[1];
    CHECK(mpg_set_items(&c, none, 0) == NULL && c.n_items == 0);
    CHECK(mpg_set_items(&c, it, 12) != NULL);
}

static void test_text_store_round_trip(void)
{
    mpg_cfg_t a, b;
    mpg_defaults(&a);
    int l[2] = {MPG_P_TIMERS, MPG_P_FRAME}, r[3] = {MPG_P_GAMES, MPG_P_ACTIONS, MPG_P_TILES};
    CHECK(mpg_set_pages(&a, l, 2, r, 3) == NULL);
    CHECK(mpg_set_timeouts(&a, 12, 45) == NULL);
    char text[MPG_TEXT_MAX + 1];
    CHECK(mpg_cfg_to_text(&a, text, sizeof(text)) > 0);
    CHECK(strcmp(text, "L=timers,frame;R=games,actions,tiles;S=12;I=45;A=beep,dance,vision,hello;C=volume,brightness,mute,quiet,lock,timers,games,wifi,battery") == 0);
    CHECK(mpg_cfg_from_text(&b, text) == 1);
    CHECK(memcmp(&a, &b, sizeof(a)) == 0);
    /* patch NX01: a choice saved before the Lock tile names "light"; it is read as the Lock tile, in the same place, never an error and never twice */
    mpg_cfg_t old, both;
    CHECK(mpg_sheet_by_name("light") == MPG_S_LOCK && mpg_sheet_by_name("lock") == MPG_S_LOCK);
    CHECK(mpg_cfg_from_text(&old, "L=clock;R=games;S=10;I=20;A=beep,dance,vision,hello;C=volume,brightness,mute,quiet,light,timers,games,wifi,battery") == 1);
    mpg_cfg_t dflt;
    mpg_defaults(&dflt);
    CHECK(memcmp(&old, &dflt, sizeof(old)) == 0 && old.items[4] == MPG_S_LOCK && old.n_items == 9);
    CHECK(mpg_cfg_from_text(&both, "L=clock;R=games;S=10;I=20;A=beep,dance,game,hello;C=mute,light,lock,games") == 1);
    CHECK(both.n_items == 3 && both.items[0] == MPG_S_MUTE && both.items[1] == MPG_S_LOCK && both.items[2] == MPG_S_GAMES);
    mpg_sheet_t LS;
    mpg_sheet_layout(&dflt, &LS);
    int six = 0, lock_tiles = 0;
    for (int i = 0; i < LS.n; i++) {  /* the default sheet: mute, quiet, lock, apps, games and the gear, one row of six, no light tile */
        if (LS.r[i].item == MPG_S_COUNT || mpg_sheet_kind(LS.r[i].item) == 1) {
            six++;
            lock_tiles += LS.r[i].item == MPG_S_LOCK;
            CHECK(LS.r[i].y == LS.r[0 + (LS.n - 6)].y);
        }
    }
    CHECK(six == 6 && lock_tiles == 1);
    /* the longest configuration fits the flash text: six pages, six actions would not exist (five), twelve items */
    mpg_cfg_t big;
    mpg_defaults(&big);
    int bl[3] = {MPG_P_CLOCK, MPG_P_TIMERS, MPG_P_GAMES}, br[3] = {MPG_P_ACTIONS, MPG_P_FRAME, MPG_P_TILES};
    CHECK(mpg_set_pages(&big, bl, 3, br, 3) == NULL);
    int a4[4] = {MPG_A_HELLO, MPG_A_BEEP, MPG_A_DANCE, MPG_A_GAME};
    CHECK(mpg_set_actions(&big, a4, 4) == NULL);
    int all[11];
    for (int i = 0; i < 11; i++) all[i] = i;
    CHECK(mpg_set_items(&big, all, 11) == NULL);
    const int len = mpg_cfg_to_text(&big, text, sizeof(text));
    CHECK(len > 0 && len <= MPG_TEXT_MAX);
    CHECK(mpg_cfg_from_text(&b, text) == 1 && memcmp(&big, &b, sizeof(b)) == 0);
    /* a small buffer says so instead of cutting */
    char tiny[20];
    CHECK(mpg_cfg_to_text(&big, tiny, sizeof(tiny)) == -1);
    /* nothing saved, damaged or unknown text: the defaults, and the caller is told */
    mpg_cfg_t d;
    mpg_defaults(&d);
    CHECK(mpg_cfg_from_text(&b, NULL) == 0 && memcmp(&b, &d, sizeof(b)) == 0);
    CHECK(mpg_cfg_from_text(&b, "") == 0 && memcmp(&b, &d, sizeof(b)) == 0);
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=clock;S=10;I=20;A=beep,dance,game,hello;C=volume") == 0 && memcmp(&b, &d, sizeof(b)) == 0);
    CHECK(mpg_cfg_from_text(&b, "L=bogus;R=games;S=10;I=20;A=beep,dance,game,hello;C=volume") == 0);
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=games;S=99;I=20;A=beep,dance,game,hello;C=volume") == 0);
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=games;S=10;I=20;A=beep;C=volume") == 1 && b.n_actions == 2);   /* one is topped up to the two a strip needs */
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=games;S=10;I=20;A=;C=volume") == 1 && b.n_actions == 2);
    CHECK(mpg_cfg_from_text(&b, "garbage;;;===") == 0);
    /* an empty strip is a valid saved choice */
    CHECK(mpg_cfg_from_text(&b, "L=;R=;S=10;I=20;A=beep,dance,game,hello;C=volume,mute") == 1 && b.n_left == 0 && b.n_right == 0 && b.n_items == 2);
    /* a text saved before patch UI01 (find in the actions and the items, a 6 s sheet) loads with find dropped and the time raised */
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=games;S=6;I=20;A=find,beep,dance,game;C=volume,brightness,mute,find,timers") == 1);
    CHECK(b.sheet_s == 8 && b.n_actions == 4 && b.actions[0] == MPG_A_BEEP && b.actions[1] == MPG_A_DANCE && b.actions[2] == MPG_A_VISION && b.actions[3] == MPG_A_HELLO);   /* beep, dance, game was the old default: patch SF101 moves it to the new one */
    CHECK(b.n_items == 4 && b.items[3] == MPG_S_TIMERS);
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=games;S=15;I=20;A=hello,find,beep,dance,game;C=volume,find") == 1 && b.n_actions == 4 && b.actions[0] == MPG_A_HELLO && b.sheet_s == 15 && b.n_items == 1);
    /* the flash key and the text limit */
    CHECK(strlen("pages_cfg") <= 15 && strlen("page_tiles") <= 15);
}

static void test_tiles(void)
{
    mpg_tiles_t t;
    mpg_tiles_clear(&t);
    CHECK(mpg_tiles_add(&t, "sun", "Today", "72 F") == 0 && t.n == 1 && t.t[0].icon == MPG_I_SUN);
    CHECK(strcmp(t.t[0].label, "Today") == 0 && strcmp(t.t[0].value, "72 F") == 0);
    /* an unknown icon is none; text is cut, cleaned of control and non ASCII characters, trimmed */
    CHECK(mpg_tiles_add(&t, "flying-saucer", "  A very long label here  ", "0123456789ABCDEF") == 0 && t.t[1].icon == MPG_I_NONE);
    CHECK(strlen(t.t[1].label) <= MPG_TILE_LABEL && strlen(t.t[1].value) == MPG_TILE_VALUE);
    CHECK(t.t[1].label[0] == 'A');
    CHECK(mpg_tiles_add(&t, "home", "Garage\n\x01\xC3\xA9", "ok") == 0);
    CHECK(strcmp(t.t[2].label, "Garage") == 0);
    CHECK(mpg_tiles_add(&t, "bell", "", "") == -2 && t.n == 3);
    CHECK(mpg_tiles_add(&t, NULL, NULL, "9") == 0 && t.n == 4);
    CHECK(mpg_tiles_add(&t, "heart", "a", "b") == 0 && mpg_tiles_add(&t, "lamp", "c", "d") == 0 && t.n == 6);
    CHECK(mpg_tiles_add(&t, "temp", "e", "f") == -1 && t.n == 6);   /* at most six */
    char age[32];
    mpg_age_text(age, sizeof(age), 10, 0);
    CHECK(strcmp(age, "just now") == 0);
    mpg_age_text(age, sizeof(age), 300, 0);
    CHECK(strcmp(age, "5 min ago") == 0);
    mpg_age_text(age, sizeof(age), 7300, 0);
    CHECK(strcmp(age, "2 h ago") == 0);
    mpg_age_text(age, sizeof(age), 200000, 1);
    CHECK(strstr(age, "dia") != NULL);
    CHECK(mpg_tiles_save_due(1000, 0) && !mpg_tiles_save_due(1500, 1000) && mpg_tiles_save_due(1600, 1000));
}

static void test_icons(void)
{
    for (int i = 1; i < MPG_I_COUNT; i++) {
        mpg_shape_t s[MPG_ICON_SHAPES_MAX];
        const int n = mpg_icon_shapes(i, s);
        CHECK(n >= 3 && n <= MPG_ICON_SHAPES_MAX);
        for (int k = 0; k < n; k++) {
            CHECK(s[k].x >= 0 && s[k].y >= 0 && s[k].x + s[k].w <= 24 && s[k].y + s[k].h <= 24 && s[k].w > 0 && s[k].h > 0);
            if (s[k].kind == MPG_SH_CIRCLE || s[k].kind == MPG_SH_RING) {
                CHECK(s[k].w == s[k].h);
            }
        }
        CHECK(mpg_icon_by_name(MPG_ICON_NAMES[i]) == i);
    }
    mpg_shape_t s[MPG_ICON_SHAPES_MAX];
    CHECK(mpg_icon_shapes(MPG_I_NONE, s) == 0);
}

static void test_sheet_layout(void)
{
    mpg_cfg_t c;
    mpg_defaults(&c);
    mpg_sheet_t L;
    mpg_sheet_layout(&c, &L);
    /* the default sheet: status line, one slider row, two tile rows (six tiles and More) */
    CHECK(L.top_y >= 80 && L.top_y <= 120);   /* patch UI05: one row of icon tiles; patch UX02c: the tiles carry a 16 px word, so the sheet is 16 px taller */
    CHECK(L.top_y >= 28);                      /* never over the banner */
    CHECK(L.n_status == 2 && L.status_h == MPG_STATUS_ROW_H && L.text_h == 0);   /* Wi-Fi and battery: the status row */
    int tiles = 0, sliders = 0;
    for (int i = 0; i < L.n; i++) {
        const mpg_rect_t* r = &L.r[i];
        CHECK(r->x >= 0 && r->x + r->w <= 320 && r->y >= L.top_y && r->y + r->h <= 240);
        if (r->item == MPG_S_COUNT || mpg_sheet_kind(r->item) == 1) {
            tiles++;
            CHECK(r->w >= MPG_TOUCH_MIN && r->h >= MPG_TOUCH_MIN);   /* touch targets are at least 44 by 44 */
        } else {
            sliders++;
            CHECK(r->h >= MPG_TOUCH_MIN);
        }
        for (int j = i + 1; j < L.n; j++) {
            const mpg_rect_t* q = &L.r[j];
            const int apart = r->x + r->w <= q->x || q->x + q->w <= r->x || r->y + r->h <= q->y || q->y + q->h <= r->y;
            CHECK(apart);
        }
    }
    CHECK(sliders == 2 && tiles == 6);   /* volume and brightness; mute quiet light timers games + the gear */
    CHECK(L.r[L.n - 1].item == MPG_S_COUNT);
    /* every configuration fits: any subset of items keeps the sheet on the screen and below the banner */
    for (unsigned mask = 0; mask < (1u << MPG_S_COUNT); mask += 7) {
        int it[MPG_S_COUNT], n = 0;
        for (int b = 0; b < MPG_S_COUNT; b++) {
            if (mask & (1u << b)) it[n++] = b;
        }
        mpg_cfg_t d;
        mpg_defaults(&d);
        if (mpg_set_items(&d, it, n) != NULL) {
            continue;
        }
        mpg_sheet_layout(&d, &L);
        CHECK(L.top_y >= 28 && L.top_y <= 240 - MPG_SHEET_HANDLE_H - MPG_TILE_H - 6);
        for (int i = 0; i < L.n; i++) {
            CHECK(L.r[i].x >= 0 && L.r[i].x + L.r[i].w <= 320 && L.r[i].y >= L.top_y && L.r[i].y + L.r[i].h <= 240);
        }
    }
    /* nothing chosen: only the More button */
    int none[1];
    CHECK(mpg_set_items(&c, none, 0) == NULL);
    mpg_sheet_layout(&c, &L);
    CHECK(L.n == 1 && L.r[0].item == MPG_S_COUNT && L.n_status == 0);
}

/* Patch UI05 and UI04: icon tiles, the status row and the bot's own settings screen. */
static void test_icons_status_row_and_settings_screen(void)
{
    mpg_shape_t sh[MPG_ICON_SHAPES_MAX];
    for (int item = MPG_S_MUTE; item <= MPG_S_COUNT; item++) {
        if (item > MPG_S_GAMES && item != MPG_S_COUNT) continue;
        const int n = mpg_sheet_icon_shapes(item, sh);
        CHECK(n >= 2 && n <= MPG_ICON_SHAPES_MAX);
        for (int k = 0; k < n; k++) {
            CHECK(sh[k].x >= 0 && sh[k].y >= 0 && sh[k].x + sh[k].w <= 24 && sh[k].y + sh[k].h <= 24 && sh[k].w > 0 && sh[k].h > 0);
        }
    }
    /* the status row sits at the top of the sheet and the text lines for the network and the address under it */
    mpg_cfg_t c;
    mpg_defaults(&c);
    int it[6] = {MPG_S_VOLUME, MPG_S_WIFI, MPG_S_BATTERY, MPG_S_TAILNET, MPG_S_ADDRESS, MPG_S_MUTE};
    CHECK(mpg_set_items(&c, it, 6) == NULL);
    mpg_sheet_t L;
    mpg_sheet_layout(&c, &L);
    CHECK(L.status_h == MPG_STATUS_ROW_H && L.status_y == L.top_y + MPG_SHEET_HANDLE_H);
    CHECK(L.text_h == 2 * MPG_STATUS_LINE_H && L.text_y == L.status_y + MPG_STATUS_ROW_H);
    CHECK(L.top_y >= 28);
    int only_text[2] = {MPG_S_TAILNET, MPG_S_ADDRESS};
    CHECK(mpg_set_items(&c, only_text, 2) == NULL);
    mpg_sheet_layout(&c, &L);
    CHECK(L.status_h == 0 && L.text_h == 2 * MPG_STATUS_LINE_H);
    /* the tiles are one row of up to six, centered, 44 by 44 and apart */
    mpg_defaults(&c);
    mpg_sheet_layout(&c, &L);
    int row_y = -1, ntile = 0;
    for (int i = 0; i < L.n; i++) {
        if (L.r[i].item == MPG_S_COUNT || mpg_sheet_kind(L.r[i].item) == 1) {
            if (row_y < 0) row_y = L.r[i].y;
            CHECK(L.r[i].y == row_y && L.r[i].w == MPG_TILE_W && L.r[i].h == MPG_TILE_H);
            ntile++;
        }
    }
    CHECK(ntile == 6 && L.r[L.n - 1].item == MPG_S_COUNT && L.r[L.n - 1].x + MPG_TILE_W <= 320 && L.r[L.n - 6].x >= 0);
    CHECK(L.r[L.n - 6].x + L.r[L.n - 1].x + MPG_TILE_W == 320);   /* centered */
    /* colors follow the state: green good, amber low, red critical */
    CHECK(mpg_signal_level(4) == 0 && mpg_signal_level(3) == 0 && mpg_signal_level(2) == 1 && mpg_signal_level(1) == 2 && mpg_signal_level(0) == 2);
    CHECK(mpg_battery_level(80, 0) == 0 && mpg_battery_level(30, 0) == 0 && mpg_battery_level(29, 0) == 1 && mpg_battery_level(15, 0) == 1 &&
          mpg_battery_level(14, 0) == 2 && mpg_battery_level(5, 1) == 0);
    /* the settings screen: every target at least 44 by 44, nothing off the glass or overlapping, five styles and the pictures tile */
    mpg_box_t boxes[2 + MPG_SET_TILES_MAX + 2];
    int nb = 0;
    boxes[nb++] = mpg_set_wifi_box();
    boxes[nb++] = mpg_set_done_box();
    for (int i = 0; i < MPG_SET_TILES_MAX; i++) boxes[nb++] = mpg_set_tile_box(i);
    boxes[nb++] = mpg_set_switch_box();
    boxes[nb++] = mpg_set_more_box();
    for (int i = 0; i < nb; i++) {
        CHECK(boxes[i].w >= MPG_TOUCH_MIN && boxes[i].h >= MPG_TOUCH_MIN);
        CHECK(boxes[i].x >= 0 && boxes[i].y >= 0 && boxes[i].x + boxes[i].w <= 320 && boxes[i].y + boxes[i].h <= 240);
        for (int j = 0; j < i; j++) {
            CHECK(boxes[i].x + boxes[i].w <= boxes[j].x || boxes[j].x + boxes[j].w <= boxes[i].x || boxes[i].y + boxes[i].h <= boxes[j].y ||
                  boxes[j].y + boxes[j].h <= boxes[i].y);
        }
    }
    const mpg_box_t pv = mpg_set_preview_box();
    CHECK(pv.x + pv.w <= mpg_set_tile_box(0).x && pv.y + pv.h <= mpg_set_switch_box().y);
    for (int i = 0; i < MPG_SET_STYLES; i++) {
        mpg_pshape_t ps[MPG_PSHAPES_MAX];
        const int n = mpg_set_preview_shapes(MPG_SET_STYLE_ID[i], ps);
        CHECK(n >= 2 && n <= MPG_PSHAPES_MAX);
        for (int k = 0; k < n; k++) CHECK(ps[k].x >= 0 && ps[k].y >= 0 && ps[k].x + ps[k].w <= pv.w && ps[k].y + ps[k].h <= pv.h);
        CHECK(strlen(MPG_SET_STYLE_NAME[0][i]) > 0 && strlen(MPG_SET_STYLE_NAME[1][i]) > 0);
    }
}

/* Patch UI07: every page's content lies inside the content zone (screen y 28 to 184, zone y 0 to 156): never over the banner row (screen
 * y 0 to 28), never over the page dots at the bottom edge or the subtitle zone below the zone, and clear of the grabber handle. */
#define ZONE_CONTENT_TOP 0
#define ZONE_DOTS_TOP (MPG_PAGER_Y - 4)
static int in_zone(int x, int y, int w, int h)
{
    return x >= 0 && x + w <= MPG_ZONE_W && y >= ZONE_CONTENT_TOP && y + h <= ZONE_DOTS_TOP && MPG_ZONE_Y + y >= 28 && MPG_ZONE_Y + y + h <= 184;
}
static int clear_of_grabber(int x, int y, int w, int h)
{
    const int gx = MPG_ZONE_W / 2 - 24, gy = 2, gw = 48, gh = 5;
    return x + w <= gx || gx + gw <= x || y + h <= gy || gy + gh <= y;
}

static void test_every_page_content_stays_in_the_zone(void)
{
    CHECK(MPG_ZONE_Y == 28 && MPG_ZONE_Y + MPG_ZONE_H == 184);
    CHECK(MPG_PAGER_Y + 4 <= MPG_ZONE_H);   /* the dots sit inside the zone, at its bottom edge */
    for (int ring = 0; ring <= 1; ring++) {   /* clock: the digits, the date line, the AM mark */
        const mpg_clock_layout_t l = mpg_clock_layout(ring);
        const int w = 4 * l.digit_w + 2 * l.gap + l.colon_w;
        CHECK(in_zone(l.x0, l.y0, w, l.digit_h) && clear_of_grabber(l.x0, l.y0, w, l.digit_h));
        CHECK(in_zone(0, l.date_y, MPG_ZONE_W, 23));
        if (ring) CHECK(in_zone(l.ring_cx - l.ring / 2, l.ring_cy - l.ring / 2, l.ring, l.ring));
    }
    for (int n = 1; n <= 3; n++) {            /* games */
        for (int i = 0; i < n; i++) {
            int y, h;
            mpg_games_row(n, i, &y, &h);
            CHECK(in_zone(8, y, 304, h) && clear_of_grabber(8, y, 304, h));
        }
    }
    for (int n = 0; n <= 3; n++) {            /* timers: rows, then the quick starts */
        for (int i = 0; i < n; i++) {
            const int y = mpg_timer_top(n) + i * MPG_TIMER_PITCH;
            CHECK(in_zone(8, y, 304, MPG_TIMER_ROW_H) && clear_of_grabber(8, y, 304, MPG_TIMER_ROW_H));
        }
        if (mpg_timer_quick(n)) CHECK(in_zone(8, mpg_timer_quick_y(), 304, mpg_timer_quick_h(n)));
    }
    for (int n = 1; n <= 6; n++) {            /* quick actions and the dashboard tiles share the grid */
        for (int i = 0; i < n; i++) {
            int x, y, w, h;
            mpg_cell(i, n, 8, 26, 304, 108, 8, &x, &y, &w, &h);
            CHECK(in_zone(x, y, w, h) && clear_of_grabber(x, y, w, h));
        }
    }
    CHECK(in_zone(64, 0, 192, 144));          /* the picture frame (the grabber is drawn over its top edge on purpose) */
    /* the title of a page, the grabber and the status row of the sheet never reach the banner row either */
    CHECK(MPG_ZONE_Y + 2 >= 28);
    mpg_cfg_t c;
    mpg_defaults(&c);
    mpg_sheet_t L;
    mpg_sheet_layout(&c, &L);
    CHECK(L.top_y >= 28);
}

static void test_page_contents(void)
{
    char s[16];
    mpg_fmt_left(s, sizeof(s), 272);
    CHECK(strcmp(s, "4:32") == 0);
    mpg_fmt_left(s, sizeof(s), 3730);
    CHECK(strcmp(s, "1:02:10") == 0);
    mpg_fmt_left(s, sizeof(s), -5);
    CHECK(strcmp(s, "0:00") == 0);
    mpg_best_text(s, sizeof(s), 0, 0);
    CHECK(strcmp(s, "Best -") == 0);
    mpg_best_text(s, sizeof(s), 312, 0);
    CHECK(strcmp(s, "Best 312") == 0);
    CHECK(mpg_dim_pct(1) == 55 && mpg_dim_pct(0) == 100 && mpg_scale(200, 55) == 110);
    CHECK(mpg_dim_pct(1) >= 50);   /* patch UI11: the owner found the old 35 percent too dim to read */
    /* patch UI13: the games page is a grid of two columns and three rows of 44 px tiles, five games and a More tile when there are more than six */
    CHECK(mpg_games_per_page(3) == 3 && mpg_games_per_page(6) == 6 && mpg_games_per_page(7) == 5 && !mpg_games_has_more(6) && mpg_games_has_more(7));
    CHECK(mpg_games_next_offset(0, 7) == 5 && mpg_games_next_offset(5, 7) == 0 && mpg_games_next_offset(0, 12) == 5 && mpg_games_next_offset(10, 12) == 0);
    for (int a = 0; a < MPG_GAMES_SLOTS; a++) {
        int x, y, w, h;
        mpg_games_tile(a, &x, &y, &w, &h);
        CHECK(h >= 44 && w >= 44 && x >= 8 && x + w <= 320 - 8 && y >= MPG_GAMES_TOP && y + h <= MPG_PAGER_Y - 4);   /* clear of the page dots */
        for (int b = 0; b < a; b++) {
            int x2, y2, w2, h2;
            mpg_games_tile(b, &x2, &y2, &w2, &h2);
            CHECK(x + w <= x2 || x2 + w2 <= x || y + h <= y2 || y2 + h2 <= y);
        }
    }
    /* patch UX13e: the games page scrolls: two columns of 148 by 64 px tiles, 8 px gaps and margins, the content as tall as the rows need */
    for (int n = 1; n <= 13; n++) {
        for (int i = 0; i < n; i++) {
            int x, y, w, h;
            mpg_gscroll_tile(i, &x, &y, &w, &h);
            CHECK(w >= 56 && h >= 56 && x >= 8 && x + w <= MPG_ZONE_W - 8 && y >= 0 && y + h <= mpg_gscroll_content_h(n));
            for (int j = 0; j < i; j++) {
                int x2, y2, w2, h2;
                mpg_gscroll_tile(j, &x2, &y2, &w2, &h2);
                CHECK(x + w + 8 <= x2 || x2 + w2 + 8 <= x || y + h + 8 <= y2 || y2 + h2 + 8 <= y);   /* an 8 px gap between tiles */
            }
        }
    }
    CHECK(mpg_gscroll_content_h(0) == 0 && mpg_gscroll_content_h(2) == 64 && mpg_gscroll_content_h(13) == 7 * 64 + 6 * 8);
    /* patch UX13c: the control sheet at finger size: two pages, a fixed height, every target 56 px (the page target 48), 8 px gaps and margins, nothing overlaps */
    {
        mpg_cfg_t d2;
        mpg_defaults(&d2);
        mpg_sheet2_t S;
        mpg_sheet2_layout(&d2, &S);
        CHECK(S.top_y == 240 - MPG_SHEET2_H && S.top_y >= 28);                       /* the fixed height; never over the banner */
        int sliders = 0, tiles = 0;
        for (int i = 0; i < S.n; i++) {
            const mpg_rect_t* r = &S.r[i];
            CHECK(S.page[i] <= 1 && r->h >= 56 && r->x >= 8 && r->x + r->w <= 320 - 8 && r->y >= S.top_y + MPG_SHEET2_HANDLE_H && r->y + r->h <= S.next.y - 8 + 0);
            if (S.page[i] == 0) { sliders++; CHECK(r->w >= 200); } else { tiles++; CHECK(r->w >= 88); }
            for (int j = 0; j < i; j++) {
                if (S.page[j] != S.page[i]) continue;                                   /* the pages are never on screen together */
                const mpg_rect_t* q = &S.r[j];
                CHECK(r->x + r->w + 8 <= q->x || q->x + q->w + 8 <= r->x || r->y + r->h + 8 <= q->y || q->y + q->h + 8 <= r->y);
            }
        }
        CHECK(sliders == 2 && tiles == 6);                                              /* the two pages hold every item: both sliders, the five tiles and the gear */
        CHECK(S.next.h >= 48 && S.next.w >= 72 && S.next.x + S.next.w <= 320 - 8 && S.next.y + S.next.h <= 240 - 4);
        CHECK(S.dots_y > S.next.y && S.dots_y < S.next.y + S.next.h);
        for (int i = 0; i < S.n; i++) CHECK(S.r[i].y + S.r[i].h + 8 <= S.next.y);       /* the page target is 8 px under the last row on either page */
        CHECK(S.status_h == MPG_SHEET2_STATUS_H && S.text_h == 0 && S.n_status == 2);
        CHECK(MPG_SHEET2_PAGES == 2);
    }
    /* patch UX14: three clock styles; each fits the zone above the page dots, the sleep sign has room, a tap cycles and wraps */
    CHECK(MPG_CLOCK_STYLES == 3 && mpg_clock_style_next(0) == 1 && mpg_clock_style_next(1) == 2 && mpg_clock_style_next(2) == 0 && mpg_clock_style_clamp(7) == 0 && mpg_clock_style_clamp(-1) == 0);
    for (int st = 0; st < MPG_CLOCK_STYLES; st++) {
        const mpg_clock_layout_t l = mpg_clock_layout(st);
        const int w = 4 * l.digit_w + 2 * l.gap + l.colon_w;
        CHECK(l.x0 >= 0 && l.x0 + w <= MPG_ZONE_W);
        CHECK(l.y0 >= 8 && l.y0 + l.digit_h <= l.date_y);
        CHECK(l.date_y + (l.date_big ? 23 : 19) <= MPG_PAGER_Y - 4);   /* the date line clears the page dots */
        CHECK(l.icon_x >= 0 && l.icon_x + 44 <= MPG_ZONE_W && l.icon_y >= 0 && l.icon_y + 20 <= MPG_PAGER_Y - 4);
        if (st != 0) CHECK(l.icon_x + 44 <= l.x0);   /* the sign does not touch the digits (style 0 puts it beside the date line) */
        CHECK(l.ampm_x + 24 <= MPG_ZONE_W);
    }
    for (int ring = 0; ring <= 1; ring++) {
        const mpg_clock_layout_t l = mpg_clock_layout(ring);
        const int w = 4 * l.digit_w + 2 * l.gap + l.colon_w;
        CHECK(l.x0 >= 0 && l.x0 + w <= MPG_ZONE_W);
        CHECK(((l.digit_h - 3 * l.bar) % 2) == 0);   /* h = 3 bar + 2 L, as the bar math needs */
        CHECK(l.date_y + 23 <= MPG_PAGER_Y - 4);     /* the date clears the pager dots, which sit in the bottom row */
        if (!ring) {
            CHECK(l.digit_h >= 100 && l.digit_w >= 54);   /* patch UI01: the clock is bigger than before (87 by 44) */
        }
        CHECK(l.y0 >= 0);
        if (ring) {
            CHECK(l.ring_cy - l.ring / 2 >= 0 && l.ring_cy + l.ring / 2 <= MPG_PAGER_Y + 2);
            CHECK(w + 6 <= l.ring - 20);              /* the digits sit inside the ring */
        }
    }
    /* grids: 4 cells 2 by 2, 5 and 6 cells 3 by 2; every cell inside the area and apart */
    for (int n = 1; n <= 6; n++) {
        int xs[6], ys[6], ws[6], hs[6];
        for (int i = 0; i < n; i++) {
            mpg_cell(i, n, 8, MPG_CONTENT_Y, 304, MPG_CONTENT_BOTTOM - MPG_CONTENT_Y, 6, &xs[i], &ys[i], &ws[i], &hs[i]);
            CHECK(xs[i] >= 8 && xs[i] + ws[i] <= 312 && ys[i] >= MPG_CONTENT_Y && ys[i] + hs[i] <= MPG_CONTENT_BOTTOM);
            CHECK(ws[i] >= 60 && hs[i] >= 44);   /* big buttons */
            for (int j = 0; j < i; j++) {
                CHECK(xs[i] + ws[i] <= xs[j] || xs[j] + ws[j] <= xs[i] || ys[i] + hs[i] <= ys[j] || ys[j] + hs[j] <= ys[i]);
            }
        }
    }
    /* patch UI01: the games rows and the timer rows are at least 44 px high for three and fit above the dots */
    for (int n = 1; n <= 3; n++) {
        for (int i = 0; i < n; i++) {
            int y, h;
            mpg_games_row(n, i, &y, &h);
            CHECK(h >= MPG_TOUCH_MIN && h <= 52 && y >= 0 && y + h <= MPG_PAGER_Y - 4);
        }
    }
    for (int n = 0; n <= 3; n++) {
        CHECK(n == 0 || mpg_timer_top(n) + (n - 1) * MPG_TIMER_PITCH + MPG_TIMER_ROW_H <= MPG_PAGER_Y - 4);
        CHECK(MPG_TIMER_ROW_H >= MPG_TOUCH_MIN);
        if (mpg_timer_quick(n)) {
            CHECK(mpg_timer_quick_h(n) >= MPG_TOUCH_MIN && mpg_timer_quick_y() + mpg_timer_quick_h(n) <= MPG_PAGER_Y - 4);
            CHECK(n == 0 || mpg_timer_quick_y() >= mpg_timer_top(n) + n * MPG_TIMER_PITCH);
        }
    }
    /* the pager dots stay inside the zone and are centered */
    for (int n = 2; n <= 7; n++) {
        CHECK(mpg_pager_x(n, 0) + mpg_pager_x(n, n - 1) == MPG_ZONE_W);
    }
    /* a quiet unit does not play sounds or dance on a button, and a muted one does not beep */
    CHECK(mpg_action_blocked(MPG_A_DANCE, 1, 0) && mpg_action_blocked(MPG_A_BEEP, 1, 0) && !mpg_action_blocked(MPG_A_GAME, 1, 0));
    CHECK(mpg_action_blocked(MPG_A_BEEP, 0, 1) && !mpg_action_blocked(MPG_A_DANCE, 0, 1));
    CHECK(!mpg_action_blocked(MPG_A_BEEP, 0, 0));
    CHECK(mpg_frame_next(3, 2) == 0 && mpg_frame_next(3, 0) == 1 && mpg_frame_next(0, 0) == 0);
    /* page names and titles line up */
    for (int i = 0; i < MPG_P_COUNT; i++) {
        CHECK(mpg_page_by_name(MPG_PAGE_NAMES[i]) == i && strlen(MPG_PAGE_TITLE[0][i]) > 0 && strlen(MPG_PAGE_TITLE[1][i]) > 0);
    }
    for (int i = 0; i < MPG_A_COUNT; i++) {
        CHECK(mpg_action_by_name(MPG_ACTION_NAMES[i]) == i && strlen(MPG_ACTION_TITLE[1][i]) > 0);
    }
    for (int i = 0; i < MPG_S_COUNT; i++) {
        CHECK(mpg_sheet_by_name(MPG_SHEET_NAMES[i]) == i && strlen(MPG_SHEET_TITLE[1][i]) > 0);
    }
}

/* The wire names the host table (host/maipai_body/swipe_pages.py) must agree with: printed for the parity test. */
static void print_table(void)
{
    printf("{\"pages\":[");
    for (int i = 0; i < MPG_P_COUNT; i++) printf("%s\"%s\"", i ? "," : "", MPG_PAGE_NAMES[i]);
    printf("],\"actions\":[");
    for (int i = 0; i < MPG_A_COUNT; i++) printf("%s\"%s\"", i ? "," : "", MPG_ACTION_NAMES[i]);
    printf("],\"sheet\":[");
    for (int i = 0; i < MPG_S_COUNT; i++) printf("%s\"%s\"", i ? "," : "", MPG_SHEET_NAMES[i]);
    printf("],\"icons\":[");
    for (int i = 0; i < MPG_I_COUNT; i++) printf("%s\"%s\"", i ? "," : "", MPG_ICON_NAMES[i]);
    mpg_cfg_t d;
    mpg_defaults(&d);
    mpg_sheet_t L;
    mpg_sheet_layout(&d, &L);
    printf("],\"limits\":{\"side\":%d,\"sheet_s\":[%d,%d],\"idle_s\":[%d,%d],\"actions\":[%d,%d],\"sliders\":%d,\"tiles\":%d,\"status\":%d,\"tile_count\":%d},",
           MPG_SIDE_MAX, MPG_SHEET_S_MIN, MPG_SHEET_S_MAX, MPG_IDLE_S_MIN, MPG_IDLE_S_MAX, MPG_ACTIONS_MIN, MPG_ACTIONS_MAX,
           MPG_SHEET_MAX_SLIDERS, MPG_SHEET_MAX_TILES, MPG_SHEET_MAX_STATUS, MPG_TILES_MAX);
    printf("\"icon_shapes\":{");
    for (int i = 1; i < MPG_I_COUNT; i++) {
        mpg_shape_t s[MPG_ICON_SHAPES_MAX];
        const int n = mpg_icon_shapes(i, s);
        printf("%s\"%s\":[", i > 1 ? "," : "", MPG_ICON_NAMES[i]);
        for (int k = 0; k < n; k++) printf("%s[%d,%d,%d,%d,%d]", k ? "," : "", s[k].kind, s[k].x, s[k].y, s[k].w, s[k].h);
        printf("]");
    }
    printf("},\"sheet_icons\":{");
    for (int it = MPG_S_MUTE; it <= MPG_S_COUNT; it++) {
        if (it > MPG_S_GAMES && it != MPG_S_COUNT) continue;
        mpg_shape_t s[MPG_ICON_SHAPES_MAX];
        const int n = mpg_sheet_icon_shapes(it, s);
        printf("%s\"%s\":[", it > MPG_S_MUTE ? "," : "", it == MPG_S_COUNT ? "more" : MPG_SHEET_NAMES[it]);
        for (int k = 0; k < n; k++) printf("%s[%d,%d,%d,%d,%d]", k ? "," : "", s[k].kind, s[k].x, s[k].y, s[k].w, s[k].h);
        printf("]");
    }
    printf("},\"sheet_default\":{\"top_y\":%d,\"rects\":[", L.top_y);
    for (int i = 0; i < L.n; i++) printf("%s[%d,%d,%d,%d,%d]", i ? "," : "", L.r[i].item, L.r[i].x, L.r[i].y, L.r[i].w, L.r[i].h);
    printf("]},\"defaults\":{\"left\":[\"clock\"],\"right\":[\"games\"],\"sheet_s\":%d,\"idle_s\":%d}}\n", d.sheet_s, d.idle_s);
}

/* --layout a,b,c: the sheet layout for those items as JSON, for the settings page parity test. */
static int print_layout(const char* list)
{
    int it[MPG_SHEET_MAX_ITEMS + 1], n = 0;
    n = mpg_split(list, strlen(list), mpg_sheet_by_name, it, MPG_SHEET_MAX_ITEMS);
    mpg_cfg_t c;
    mpg_defaults(&c);
    if (n < 0 || mpg_set_items(&c, it, n) != NULL) {
        printf("{\"error\":true}\n");
        return 0;
    }
    mpg_sheet_t L;
    mpg_sheet_layout(&c, &L);
    printf("{\"top_y\":%d,\"status_y\":%d,\"status_h\":%d,\"text_y\":%d,\"text_h\":%d,\"status\":[", L.top_y, L.status_y, L.status_h, L.text_y, L.text_h);
    for (int i = 0; i < L.n_status; i++) printf("%s%d", i ? "," : "", L.status_items[i]);
    printf("],\"rects\":[");
    for (int i = 0; i < L.n; i++) printf("%s[%d,%d,%d,%d,%d]", i ? "," : "", L.r[i].item, L.r[i].x, L.r[i].y, L.r[i].w, L.r[i].h);
    printf("]}\n");
    return 0;
}

static void test_old_default_actions_migrate(void)   /* patch SF101 */
{
    mpg_cfg_t c, d;
    mpg_defaults(&d);
    CHECK(mpg_cfg_from_text(&c, "L=clock;R=games;S=10;I=20;A=beep,dance,game;C=volume,brightness,mute,quiet,light,timers,games,wifi,battery") == 1);
    CHECK(c.n_actions == d.n_actions && memcmp(c.actions, d.actions, MPG_ACTIONS_MAX) == 0);      /* the old default becomes the new one */
    CHECK(mpg_cfg_from_text(&c, "L=clock;R=games;S=10;I=20;A=beep,game;C=volume,brightness,mute,quiet,light,timers,games,wifi,battery") == 1);
    CHECK(c.n_actions == 2 && c.actions[0] == MPG_A_BEEP && c.actions[1] == MPG_A_GAME);          /* a list the owner chose stays */
    CHECK(mpg_cfg_from_text(&c, "L=clock;R=games;S=10;I=20;A=beep,dance,hello;C=volume,brightness,mute,quiet,light,timers,games,wifi,battery") == 1);
    CHECK(c.n_actions == 3 && c.actions[2] == MPG_A_HELLO);
}

int main(int argc, char** argv)
{
    if (argc > 1 && strcmp(argv[1], "--table") == 0) {
        print_table();
        return 0;
    }
    if (argc > 2 && strcmp(argv[1], "--layout") == 0) {
        return print_layout(argv[2]);
    }
    test_defaults_and_strip();
    test_set_pages();
    test_timeouts_actions_items();
    test_text_store_round_trip();
    test_tiles();
    test_icons();
    test_sheet_layout();
    test_icons_status_row_and_settings_screen();
    test_every_page_content_stays_in_the_zone();
    test_page_contents();
    test_old_default_actions_migrate();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("pages_core_test: all passed\n");
    return 0;
}
