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
    CHECK(c.sheet_s == 6 && c.idle_s == 20);
    CHECK(c.n_actions == 4 && c.actions[3] == MPG_A_GAME);
    CHECK(c.n_items == 10 && c.items[0] == MPG_S_VOLUME);
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
    CHECK(mpg_set_timeouts(&c, 15, 300) == NULL && c.sheet_s == 15 && c.idle_s == 300);
    CHECK(mpg_set_timeouts(&c, 16, 0) != NULL && c.sheet_s == 15);
    CHECK(mpg_set_timeouts(&c, 4, 0) != NULL);
    CHECK(mpg_set_timeouts(&c, 0, 4) != NULL && mpg_set_timeouts(&c, 0, 301) != NULL && c.idle_s == 300);
    CHECK(mpg_set_timeouts(&c, 0, 0) == NULL);  /* 0 leaves a value as it is */
    CHECK(mpg_set_timeouts(&c, 5, 5) == NULL && c.sheet_s == 5 && c.idle_s == 5);
    int a5[5] = {MPG_A_HELLO, MPG_A_FIND, MPG_A_BEEP, MPG_A_DANCE, MPG_A_GAME};
    CHECK(mpg_set_actions(&c, a5, 5) == NULL && c.n_actions == 5 && c.actions[0] == MPG_A_HELLO);
    CHECK(mpg_set_actions(&c, a5, 3) != NULL);   /* fewer than four */
    CHECK(mpg_set_actions(&c, a5, 7) != NULL);   /* more than six */
    int rep[4] = {MPG_A_FIND, MPG_A_FIND, MPG_A_BEEP, MPG_A_DANCE};
    CHECK(mpg_set_actions(&c, rep, 4) != NULL && c.n_actions == 5);
    int unk[4] = {MPG_A_FIND, MPG_A_BEEP, MPG_A_DANCE, 9};
    CHECK(mpg_set_actions(&c, unk, 4) != NULL);
    int it[12];
    for (int i = 0; i < 12; i++) it[i] = i;
    int ok[12];
    int n = 0;
    ok[n++] = MPG_S_VOLUME;
    ok[n++] = MPG_S_BRIGHTNESS;
    ok[n++] = MPG_S_MUTE;
    ok[n++] = MPG_S_QUIET;
    ok[n++] = MPG_S_LIGHT;
    ok[n++] = MPG_S_FIND;
    ok[n++] = MPG_S_TIMERS;
    ok[n++] = MPG_S_GAMES;
    ok[n++] = MPG_S_WIFI;
    ok[n++] = MPG_S_BATTERY;
    ok[n++] = MPG_S_TAILNET;
    ok[n++] = MPG_S_ADDRESS;
    CHECK(mpg_set_items(&c, ok, 12) == NULL && c.n_items == 12);
    ok[1] = MPG_S_VOLUME;
    CHECK(mpg_set_items(&c, ok, 12) != NULL);    /* a repeat */
    int none[1];
    CHECK(mpg_set_items(&c, none, 0) == NULL && c.n_items == 0);
    CHECK(mpg_set_items(&c, it, 13) != NULL);
}

static void test_text_store_round_trip(void)
{
    mpg_cfg_t a, b;
    mpg_defaults(&a);
    int l[2] = {MPG_P_TIMERS, MPG_P_FRAME}, r[3] = {MPG_P_GAMES, MPG_P_ACTIONS, MPG_P_TILES};
    CHECK(mpg_set_pages(&a, l, 2, r, 3) == NULL);
    CHECK(mpg_set_timeouts(&a, 9, 45) == NULL);
    char text[MPG_TEXT_MAX + 1];
    CHECK(mpg_cfg_to_text(&a, text, sizeof(text)) > 0);
    CHECK(strcmp(text, "L=timers,frame;R=games,actions,tiles;S=9;I=45;A=find,beep,dance,game;C=volume,brightness,mute,quiet,light,find,timers,games,wifi,battery") == 0);
    CHECK(mpg_cfg_from_text(&b, text) == 1);
    CHECK(memcmp(&a, &b, sizeof(a)) == 0);
    /* the longest configuration fits the flash text: six pages, six actions would not exist (five), twelve items */
    mpg_cfg_t big;
    mpg_defaults(&big);
    int bl[3] = {MPG_P_CLOCK, MPG_P_TIMERS, MPG_P_GAMES}, br[3] = {MPG_P_ACTIONS, MPG_P_FRAME, MPG_P_TILES};
    CHECK(mpg_set_pages(&big, bl, 3, br, 3) == NULL);
    int a5[5] = {MPG_A_HELLO, MPG_A_FIND, MPG_A_BEEP, MPG_A_DANCE, MPG_A_GAME};
    CHECK(mpg_set_actions(&big, a5, 5) == NULL);
    int all[12];
    for (int i = 0; i < 12; i++) all[i] = i;
    CHECK(mpg_set_items(&big, all, 12) == NULL);
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
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=clock;S=6;I=20;A=find,beep,dance,game;C=volume") == 0 && memcmp(&b, &d, sizeof(b)) == 0);
    CHECK(mpg_cfg_from_text(&b, "L=bogus;R=games;S=6;I=20;A=find,beep,dance,game;C=volume") == 0);
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=games;S=99;I=20;A=find,beep,dance,game;C=volume") == 0);
    CHECK(mpg_cfg_from_text(&b, "L=clock;R=games;S=6;I=20;A=find;C=volume") == 0);
    CHECK(mpg_cfg_from_text(&b, "garbage;;;===") == 0);
    /* an empty strip is a valid saved choice */
    CHECK(mpg_cfg_from_text(&b, "L=;R=;S=6;I=20;A=find,beep,dance,game;C=volume,mute") == 1 && b.n_left == 0 && b.n_right == 0 && b.n_items == 2);
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
    CHECK(L.top_y >= 80 && L.top_y <= 110);   /* the lower half to the lower 60 percent of the screen */
    CHECK(L.top_y >= 28);                      /* never over the banner */
    CHECK(L.n_status == 2 && L.status_h == 16);
    int tiles = 0, sliders = 0;
    for (int i = 0; i < L.n; i++) {
        const mpg_rect_t* r = &L.r[i];
        CHECK(r->x >= 0 && r->x + r->w <= 320 && r->y >= L.top_y && r->y + r->h <= 240);
        if (r->item == MPG_S_COUNT || mpg_sheet_kind(r->item) == 1) {
            tiles++;
            CHECK(r->w >= 64 && r->h >= 38);   /* large touch targets: 4.8 mm and more on the 2 inch screen */
        } else {
            sliders++;
            CHECK(r->h >= 28);
        }
        for (int j = i + 1; j < L.n; j++) {
            const mpg_rect_t* q = &L.r[j];
            const int apart = r->x + r->w <= q->x || q->x + q->w <= r->x || r->y + r->h <= q->y || q->y + q->h <= r->y;
            CHECK(apart);
        }
    }
    CHECK(sliders == 2 && tiles == 7);   /* mute quiet light find timers games + More */
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
        CHECK(L.top_y >= 28 && L.top_y <= 240 - 8 - 38 - 8);
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
    CHECK(mpg_dim_pct(1) == 35 && mpg_dim_pct(0) == 100 && mpg_scale(200, 35) == 70);
    for (int ring = 0; ring <= 1; ring++) {
        const mpg_clock_layout_t l = mpg_clock_layout(ring);
        const int w = 4 * l.digit_w + 2 * l.gap + l.colon_w;
        CHECK(l.x0 >= 0 && l.x0 + w <= MPG_ZONE_W);
        CHECK(((l.digit_h - 3 * l.bar) % 2) == 0);   /* h = 3 bar + 2 L, as the bar math needs */
        CHECK(l.date_y + 22 <= MPG_PAGER_Y);         /* the date clears the pager dots */
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
    /* the pager dots stay inside the zone and are centered */
    for (int n = 2; n <= 7; n++) {
        CHECK(mpg_pager_x(n, 0) + mpg_pager_x(n, n - 1) == MPG_ZONE_W);
    }
    /* a quiet unit does not play sounds or dance on a button, and a muted one does not beep */
    CHECK(mpg_action_blocked(MPG_A_DANCE, 1, 0) && mpg_action_blocked(MPG_A_BEEP, 1, 0) && !mpg_action_blocked(MPG_A_GAME, 1, 0));
    CHECK(mpg_action_blocked(MPG_A_BEEP, 0, 1) && mpg_action_blocked(MPG_A_FIND, 0, 1) == 1 && !mpg_action_blocked(MPG_A_DANCE, 0, 1));
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
    printf("{\"top_y\":%d,\"status_y\":%d,\"status_h\":%d,\"status\":[", L.top_y, L.status_y, L.status_h);
    for (int i = 0; i < L.n_status; i++) printf("%s%d", i ? "," : "", L.status_items[i]);
    printf("],\"rects\":[");
    for (int i = 0; i < L.n; i++) printf("%s[%d,%d,%d,%d,%d]", i ? "," : "", L.r[i].item, L.r[i].x, L.r[i].y, L.r[i].w, L.r[i].h);
    printf("]}\n");
    return 0;
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
    test_page_contents();
    if (failures) {
        printf("%d failure(s)\n", failures);
        return 1;
    }
    printf("pages_core_test: all passed\n");
    return 0;
}
