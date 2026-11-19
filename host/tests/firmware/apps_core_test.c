/* Host test for the Apps wall, the Timers and Alarms apps and the tabbed Settings layout (patch UI16):
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> apps_core_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_apps_core.h"
#include "maipai_lock_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

static int up(mac_touch_t* t, int x0, int y0, int x1, int y1, uint32_t ms, int paged)
{
    mac_touch_down(t, x0, y0, 1000);
    return mac_touch_up(t, x1, y1, 1000 + ms, paged);
}

static void test_touch(void)
{
    mac_touch_t t;
    memset(&t, 0, sizeof(t));
    CHECK(up(&t, 100, 100, 102, 101, 120, 1) == MAC_T_TAP);
    CHECK(up(&t, 100, 100, 100, 100, 800, 1) == MAC_T_NONE);          /* a press held too long is not a tap */
    CHECK(up(&t, 100, 30, 100, 31, 100, 1) == MAC_T_NONE);            /* the drag bar's press starts no tap */
    CHECK(up(&t, 100, 35, 100, 35, 100, 1) == MAC_T_NONE);
    CHECK(up(&t, 100, 36, 100, 36, 100, 1) == MAC_T_TAP);             /* y 36 and below belongs to the targets */
    CHECK(up(&t, 100, 40, 102, 80, 200, 1) == MAC_T_DISMISS);         /* begun on the strip, 40 px down: dismiss */
    CHECK(up(&t, 100, 40, 102, 60, 200, 1) == MAC_T_NONE);            /* only 20 px: not enough */
    CHECK(up(&t, 100, 44, 100, 120, 200, 1) == MAC_T_NONE);           /* begun at y 44 or below: a scroll or a drag, never a dismiss */
    CHECK(up(&t, 100, 30, 140, 80, 200, 1) == MAC_T_NONE);            /* too slanted */
    CHECK(up(&t, 100, 30, 100, 80, 1600, 1) == MAC_T_NONE);           /* too slow */
    CHECK(up(&t, 250, 120, 100, 124, 200, 1) == MAC_T_NEXT);          /* the finger moves left: the next page */
    CHECK(up(&t, 100, 120, 250, 116, 200, 1) == MAC_T_PREV);
    CHECK(up(&t, 250, 120, 100, 124, 200, 0) == MAC_T_NONE);          /* not a paged view */
    CHECK(up(&t, 250, 120, 230, 120, 200, 1) == MAC_T_NONE);          /* under 36 px */
    CHECK(up(&t, 250, 120, 150, 210, 200, 1) == MAC_T_NONE);          /* mostly diagonal */
    CHECK(mac_touch_up(&t, 0, 0, 5000, 1) == MAC_T_NONE);             /* an up with no down */
    CHECK(mac_press_dead(28) && mac_press_dead(35) && !mac_press_dead(36) && !mac_press_dead(27));
}

static void test_wall(void)
{
    CHECK(mac_wall_pages(0) == 1 && mac_wall_pages(1) == 1 && mac_wall_pages(4) == 1 && mac_wall_pages(5) == 2 && mac_wall_pages(8) == 2 && mac_wall_pages(9) == 3);
    CHECK(mac_wall_count(0, 8) == 4 && mac_wall_count(1, 8) == 4 && mac_wall_count(1, 7) == 3 && mac_wall_count(2, 7) == 0 && mac_wall_count(0, 2) == 2);
    CHECK(mac_wall_clamp(-1, 8) == 0 && mac_wall_clamp(5, 8) == 1 && mac_wall_clamp(0, 0) == 0);
    CHECK(mac_wall_step(0, 8, 1) == 1 && mac_wall_step(1, 8, 1) == 1 && mac_wall_step(1, 8, -1) == 0 && mac_wall_step(0, 8, -1) == 0);
    for (int a = 0; a < MAC_WALL_PER_PAGE; a++) {
        int x, y, w, h;
        mac_wall_tile(a, &x, &y, &w, &h);
        CHECK(w == 150 && h == 86);                                       /* patch NX08, spaced by UX13e: two columns across the width with 6 px margins, two rows down the zone */
        { int ax, ay, aw, ah, px, py, pw, ph; mac_tile_art_box(&ax, &ay, &aw, &ah); mac_tile_plate_box(&px, &py, &pw, &ph);
          CHECK(ax >= 0 && ax + aw <= w && ay + ah <= py && py + ph <= h && ph >= 28); }   /* the picture sits above the label plate, both inside the tile */
        CHECK(x >= 0 && x + w <= MAC_W && y >= MAC_TOP && y + h <= MAC_WALL_DOTS_Y - MAC_WALL_DOT_ON / 2); /* the dots stay below the tiles */
        CHECK(w >= MAC_TARGET_MIN && h >= MAC_TARGET_MIN);
        for (int b = a + 1; b < MAC_WALL_PER_PAGE; b++) {
            int x2, y2, w2, h2;
            mac_wall_tile(b, &x2, &y2, &w2, &h2);
            const int sep_x = x + w <= x2 || x2 + w2 <= x, sep_y = y + h <= y2 || y2 + h2 <= y;
            CHECK(sep_x || sep_y);
            if (!sep_x) CHECK(y2 - (y + h) == MAC_WALL_GAP || y - (y2 + h2) == MAC_WALL_GAP);   /* 8 px between the rows (patch UX13e) */
            if (!sep_y) CHECK(x2 - (x + w) == MAC_WALL_GAP || x - (x2 + w2) == MAC_WALL_GAP);   /* and between the columns */
        }
        CHECK(mac_wall_hit(x + w / 2, y + h / 2) == a);
        CHECK(mac_wall_hit(x, y) == a && mac_wall_hit(x + w - 1, y + h - 1) == a);
    }
    CHECK(mac_wall_hit(2, 100) == -1 && mac_wall_hit(158, 100) == -1 && mac_wall_hit(160, 119) == -1 && mac_wall_hit(100, MAC_WALL_DOTS_Y) == -1);   /* the margins, the gap and the dots hit nothing */
    CHECK(MAC_WALL_Y0 == MAC_TOP);                                        /* the tiles use the zone from its top */
    CHECK(MAC_WALL_DOTS_Y + MAC_WALL_DOT_ON / 2 <= MAC_BOTTOM);
    /* dots: centered, evenly spaced, one pixel row apart from the tiles */
    CHECK(mac_wall_dot_x(2, 0) + mac_wall_dot_x(2, 1) == MAC_W);
    CHECK(mac_wall_dot_x(3, 1) == MAC_W / 2);
    CHECK(mac_wall_dot_x(3, 2) - mac_wall_dot_x(3, 1) == MAC_WALL_DOT_PITCH);
}

static void test_apps(void)
{
    uint8_t l[MAC_APP_MAX];
    CHECK(mac_apps_list(0, l) == MAC_APP_COUNT - 1);
    CHECK(mac_apps_list(1, l) == MAC_APP_COUNT);
    int has_pics = 0;
    for (int i = 0; i < MAC_APP_COUNT; i++) has_pics |= l[i] == MAC_APP_PICTURES;
    CHECK(has_pics);
    mac_apps_list(0, l);
    for (int i = 0; i < MAC_APP_COUNT - 1; i++) CHECK(l[i] != MAC_APP_PICTURES);
    CHECK(l[0] == MAC_APP_TIMERS && l[1] == MAC_APP_ALARMS && l[2] == MAC_APP_CLOCK && l[3] == MAC_APP_QUICK);   /* the order the owner listed */
    CHECK(l[MAC_APP_COUNT - 2] == MAC_APP_LOCK && l[MAC_APP_COUNT - 3] == MAC_APP_DANCE);
    CHECK(mac_wall_pages(mac_apps_list(1, l)) == 2 && mac_wall_pages(mac_apps_list(0, l)) == 2);
    for (int a = 0; a < MAC_APP_COUNT; a++) {
        CHECK(MAC_APP_NAMES[a][0] != '\0' && MAC_APP_TITLE[0][a][0] != '\0' && MAC_APP_TITLE[1][a][0] != '\0');
    }
    CHECK(mac_app_strip_page(MAC_APP_CLOCK) == MPG_P_CLOCK && mac_app_strip_page(MAC_APP_QUICK) == MPG_P_ACTIONS);
    CHECK(mac_app_strip_page(MAC_APP_PICTURES) == MPG_P_FRAME && mac_app_strip_page(MAC_APP_DASHBOARD) == MPG_P_TILES);
    CHECK(mac_app_strip_page(MAC_APP_TIMERS) == -1 && mac_app_strip_page(MAC_APP_LOCK) == -1 && mac_app_strip_page(MAC_APP_DANCE) == -1);
}

static void test_timers_alarms(void)
{
    int x, y, w, h, x2, y2, w2, h2;
    /* patch NX09: a scrolling column of presets on the left (7 and Custom), tall timer rows on the right */
    CHECK(MAC_PRESETS == 7 && MAC_PRESET_MIN[0] == 1 && MAC_PRESET_MIN[3] == 15 && MAC_PRESET_MIN[4] == 30 && MAC_PRESET_MIN[5] == 45 && MAC_PRESET_MIN[6] == 60 && MAC_PRESET_CUSTOM == 7);
    CHECK(MAC_TL_X + MAC_TL_W + 6 <= MAC_TR_X && MAC_TR_X + MAC_TR_W <= MAC_W && MAC_TL_Y >= MAC_DRAG_DEAD_Y - 4 && MAC_TL_Y + MAC_TL_H == MAC_BOTTOM);   /* safe area y 28 to 224, the scroll bar fits between */
    for (int i = 0; i <= MAC_PRESETS; i++) {
        mac_preset_box(i, &x, &y, &w, &h);
        CHECK(w >= 100 - 4 && h >= 56 && y == i * MAC_TL_PITCH && x == 0 && w <= MAC_TL_W);
        if (i > 0) {
            int px, py, pw, ph;
            mac_preset_box(i - 1, &px, &py, &pw, &ph);
            CHECK(py + ph + (MAC_TL_PITCH - MAC_TL_BTN_H) == y);                                      /* 8 px apart (patch UX13f) */
        }
    }
    CHECK(mac_tl_content_h() == 8 * 64 - 8 && mac_tl_content_h() > MAC_TL_H && MAC_TL_PITCH - MAC_TL_BTN_H >= 8);   /* the column scrolls */
    int by, bh;
    CHECK(mac_scroll_bar(mac_tl_content_h(), MAC_TL_H, 0, &by, &bh) == 1);
    CHECK(MAC_TROW_H >= 64 && MAC_TROW_PITCH - MAC_TROW_H >= 8 && mac_trows_content_h(0) == 0 && mac_trows_content_h(1) == MAC_TROW_H && mac_trows_content_h(3) > MAC_TR_H);
    mac_trow_cancel_box(&x, &y, &w, &h);
    CHECK(w >= MAC_TARGET_MIN && h >= 56 && x + w <= MAC_TR_W && y + h <= MAC_TROW_H && x >= MAC_TROW_BAR_W + 8);   /* a big Cancel in each row, beside the bar */
    CHECK(mac_bar_fill(100, 100) == MAC_TROW_BAR_W && mac_bar_fill(150, 100) == MAC_TROW_BAR_W && mac_bar_fill(50, 100) == MAC_TROW_BAR_W / 2 && mac_bar_fill(0, 100) == 0 && mac_bar_fill(5, 0) == 0 && mac_bar_fill(1, 100000) == 2);
    CHECK(MAC_COUNTDOWN_READY == 0);
    CHECK(MAC_ROW_TOP >= MAC_BTN_ROW_Y + MAC_BTN_ROW_H);                 /* the list starts under the buttons */
    for (int i = 0; i < MAC_ROWS_VISIBLE; i++) {
        mac_row_box(i, &x, &y, &w, &h);
        CHECK(h >= MAC_TARGET_MIN && y + h <= MAC_BOTTOM);
        mac_cancel_box(i, &x2, &y2, &w2, &h2);
        CHECK(w2 >= MAC_TARGET_MIN && h2 >= MAC_TARGET_MIN && x2 >= x && x2 + w2 <= x + w && y2 == y);   /* a big Cancel in each row */
    }
    CHECK(!mac_list_scrolls(0) && !mac_list_scrolls(1) && !mac_list_scrolls(2) && mac_list_scrolls(3) && mac_list_scrolls(MAC_ACTIVE_MAX));   /* patch UX13f: two 56 px rows show, the rest scroll */
    CHECK(mac_list_content_h(2) <= MAC_LIST_H && mac_list_content_h(0) == 0 && MAC_ROW_H >= 56 && MAC_ROW_PITCH - MAC_ROW_H >= 8 && MAC_BTN_ROW_H >= 56 && MAC_ROW_TOP - (MAC_BTN_ROW_Y + MAC_BTN_ROW_H) >= 8);
    char b[24];
    mac_fmt_left(b, sizeof(b), 272); CHECK(strcmp(b, "4:32") == 0);
    mac_fmt_left(b, sizeof(b), 3725); CHECK(strcmp(b, "1:02:05") == 0);
    mac_fmt_left(b, sizeof(b), -4); CHECK(strcmp(b, "0:00") == 0);
    mac_fmt_time(b, sizeof(b), 7, 30, 0); CHECK(strcmp(b, "7:30 AM") == 0);
    mac_fmt_time(b, sizeof(b), 0, 5, 0); CHECK(strcmp(b, "12:05 AM") == 0);
    mac_fmt_time(b, sizeof(b), 12, 0, 0); CHECK(strcmp(b, "12:00 PM") == 0);
    mac_fmt_time(b, sizeof(b), 21, 9, 0); CHECK(strcmp(b, "9:09 PM") == 0);
    mac_fmt_time(b, sizeof(b), 7, 5, 1); CHECK(strcmp(b, "07:05") == 0);

    /* the time picker */
    mac_pick_t p;
    mac_pick_default(&p, 1, 10); CHECK(p.hour == 11 && p.minute == 0);
    mac_pick_default(&p, 1, 23); CHECK(p.hour == 0);
    mac_pick_default(&p, 0, 5); CHECK(p.hour == 7 && p.minute == 0);
    p.hour = 23; mac_pick_hour(&p, 1); CHECK(p.hour == 0);
    mac_pick_hour(&p, -1); CHECK(p.hour == 23);
    p.minute = 59; mac_pick_minute(&p, 1); CHECK(p.minute == 0 && p.hour == 23);   /* minutes wrap without carrying into the hour */
    mac_pick_minute(&p, -1); CHECK(p.minute == 59);
    p.hour = 0; CHECK(mac_pick_shown_hour(&p, 0) == 12 && mac_pick_shown_hour(&p, 1) == 0 && !mac_pick_is_pm(&p));
    p.hour = 12; CHECK(mac_pick_shown_hour(&p, 0) == 12 && mac_pick_is_pm(&p));
    p.hour = 15; CHECK(mac_pick_shown_hour(&p, 0) == 3 && mac_pick_is_pm(&p));
    mac_pick_set_pm(&p, 0); CHECK(p.hour == 3);
    mac_pick_set_pm(&p, 1); CHECK(p.hour == 15);
    p.hour = 0; mac_pick_set_pm(&p, 1); CHECK(p.hour == 12);                      /* 12 AM to PM is noon */
    p.hour = 12; mac_pick_set_pm(&p, 0); CHECK(p.hour == 0);
    for (int c24 = 0; c24 < 2; c24++) {
        for (int col = 0; col < (c24 ? 2 : 3); col++) {
            mac_pick_plus_box(col, c24, &x, &y, &w, &h); CHECK(w >= MAC_TARGET_MIN && h >= MAC_TARGET_MIN && x >= 0 && x + w <= MAC_W && y >= MAC_DRAG_DEAD_Y);
            mac_pick_minus_box(col, c24, &x2, &y2, &w2, &h2); CHECK(w2 >= MAC_TARGET_MIN && h2 >= MAC_TARGET_MIN && y2 + h2 <= MAC_PICK_BTN_Y);
            CHECK(y + h <= MAC_PICK_VAL_Y && MAC_PICK_VAL_Y + MAC_PICK_VAL_H <= y2);
        }
    }
    mac_pick_ampm_box(0, &x, &y, &w, &h); mac_pick_ampm_box(1, &x2, &y2, &w2, &h2);
    CHECK(h >= MAC_TARGET_MIN && h2 >= MAC_TARGET_MIN && y + h <= y2 && y2 + h2 <= MAC_PICK_BTN_Y);
    mac_pick_cancel_box(&x, &y, &w, &h); mac_pick_save_box(&x2, &y2, &w2, &h2);
    CHECK(h >= MAC_TARGET_MIN && h2 >= MAC_TARGET_MIN && x + w <= x2 && y2 + h2 <= MAC_BOTTOM);
}

static void test_settings(void)
{
    mac_row_t r[MAC_SET_ROWS_MAX];
    int n;
    for (unsigned flags = 0; flags < 16; flags++) {
        for (int tab = 0; tab < MAC_TAB_COUNT; tab++) {
            n = mac_set_rows(tab, flags, r);
            CHECK(n >= 2 && n <= MAC_SET_ROWS_MAX);   /* patch UX13: the Faces tab is two tile rows */
            int y = 0;
            for (int i = 0; i < n; i++) {
                CHECK(r[i].y == y && r[i].h > 0);
                y += r[i].h;
                const int box_h = r[i].h - mac_row_gap(r[i].kind);
                if (r[i].kind != MAC_K_SLIDER) CHECK(box_h >= MAC_ROW_BOX_H && r[i].h - box_h >= 8);   /* patch UX13: every row is 56 px with an 8 px gap */
                CHECK(r[i].kind == mac_row_kind(r[i].id));
                for (int k = i + 1; k < n; k++) CHECK(r[i].id != r[k].id);       /* no row twice */
            }
            CHECK(mac_rows_total_h(r, n) == y);
        }
    }
    /* a slider row keeps 20 px of empty room under the knob (patch QS01): label 18, slider at y 28 (16 high, the knob 8 more each side) */
    CHECK(MAC_SLIDER_ROW_H - (MAC_SLIDER_Y + 16 + 8) >= 20 && MAC_SLIDER_Y >= 20 + 2);   /* patch UX13: the 20 px label above, the slider at y 30; the grab area is 56 px (20 px of extended area each side) */
    /* the rows of each tab, with every flag set */
#ifdef MAC_UX30_ROWS   /* patch UX30 (docs/plan/unit-settings-simplification.md): five rows in General, the two switches on the Look tab, no repeated Wi-Fi rows */
    n = mac_set_rows(MAC_TAB_GENERAL, MAC_SF_LOCK | MAC_SF_TAILNET | MAC_SF_PICTURES, r);
    CHECK(n == 6 && r[0].id == MAC_R_VOLUME && r[1].id == MAC_R_BRIGHT && r[2].id == MAC_R_NIGHT && r[3].id == MAC_R_LANGUAGE && r[4].id == MAC_R_AUTOLOCK && r[5].id == MAC_R_MORE);
    CHECK(mac_row_kind(MAC_R_LISTEN_LIGHT) == MAC_K_SWITCH && strcmp(mac_row_label(MAC_R_LISTEN_LIGHT, 0), "Listening light") == 0);
    CHECK(mac_set_rows(MAC_TAB_GENERAL, 0, r) == 5);                     /* no lock built in: no auto lock */
    for (unsigned f = 0; f < 16; f++) {                                  /* no tab has more than six rows, whatever the flags say */
        for (int tab = 0; tab < MAC_TAB_COUNT; tab++) {
            n = mac_set_rows(tab, f, r);
            if (tab != MAC_TAB_FACES) CHECK(n <= 6);
        }
    }
    n = mac_set_rows(MAC_TAB_NETWORK, MAC_SF_TAILNET, r);
    CHECK(n == 4 && r[0].id == MAC_R_WIFI_PAGE && r[1].id == MAC_R_SSID && r[2].id == MAC_R_TAILNET && r[3].id == MAC_R_HUB);
    CHECK(mac_set_rows(MAC_TAB_NETWORK, 0, r) == 3);
    n = mac_set_rows(MAC_TAB_FACES, 0, r);                               /* the tile rows, then the two switches */
    CHECK(n == (MPG_SET_STYLES + 1) / 2 + 2 && r[n - 2].id == MAC_R_STATUS_ICONS && r[n - 1].id == MAC_R_LISTEN_LIGHT);
    CHECK(mac_set_rows(MAC_TAB_FACES, MAC_SF_PICTURES, r) == (MPG_SET_STYLES + 2) / 2 + 2);
    for (unsigned f = 0; f < 16; f++) {
        n = mac_set_rows(MAC_TAB_INFO, f, r);
        CHECK(n == 6 && r[0].id == MAC_R_I_TAG && r[1].id == MAC_R_I_IMAGE && r[2].id == MAC_R_I_SLOT && r[3].id == MAC_R_I_MEM && r[4].id == MAC_R_I_HOST && r[5].id == MAC_R_I_UP);
        for (int i = 0; i < n; i++) CHECK(r[i].kind == MAC_K_INFO);
    }
#else
    n = mac_set_rows(MAC_TAB_GENERAL, MAC_SF_LOCK | MAC_SF_TAILNET | MAC_SF_PICTURES, r);
    CHECK(n == 9 && r[0].id == MAC_R_VOLUME && r[1].id == MAC_R_BRIGHT && r[2].id == MAC_R_NIGHT && r[3].id == MAC_R_STATUS_ICONS && r[4].id == MAC_R_LISTEN_LIGHT && r[5].id == MAC_R_AUTOLOCK && r[6].id == MAC_R_LOCK_NOW && r[7].id == MAC_R_LANGUAGE && r[8].id == MAC_R_MORE);
    CHECK(mac_row_kind(MAC_R_LISTEN_LIGHT) == MAC_K_SWITCH && strcmp(mac_row_label(MAC_R_LISTEN_LIGHT, 0), "Listening light") == 0);   /* patch NX01: the switch moved here from the sheet */
    n = mac_set_rows(MAC_TAB_GENERAL, 0, r);
    CHECK(n == 7);                                                       /* no lock built in: no auto lock and no Lock now */
    n = mac_set_rows(MAC_TAB_NETWORK, MAC_SF_TAILNET, r);
    CHECK(n == 5 && r[0].id == MAC_R_WIFI_PAGE && r[1].id == MAC_R_SSID && r[2].id == MAC_R_SIGNAL && r[3].id == MAC_R_TAILNET && r[4].id == MAC_R_HUB);
    CHECK(mac_set_rows(MAC_TAB_NETWORK, 0, r) == 4);
    n = mac_set_rows(MAC_TAB_FACES, 0, r);
    CHECK(n == (MPG_SET_STYLES + 1) / 2);                                /* patch UX13: only the tile rows that hold a tile (two styles a row) */
    CHECK(mac_set_rows(MAC_TAB_FACES, MAC_SF_PICTURES, r) == (MPG_SET_STYLES + 2) / 2);   /* a picture pack adds one tile */
    if (MPG_SET_STYLES <= 3) CHECK(mac_rows_total_h(r, mac_set_rows(MAC_TAB_FACES, 0, r)) <= MAC_PANE_H + 8);   /* three styles (decision 22) fit the list with no scrolling */
    n = mac_set_rows(MAC_TAB_INFO, 0, r);
    /* patch NX02: every Info row shows at once, whatever the flags say: no hint row, no ten-tap details */
    for (unsigned f = 0; f < 16; f++) {
        n = mac_set_rows(MAC_TAB_INFO, f, r);
        CHECK(n == 8 && r[0].id == MAC_R_I_TAG && r[1].id == MAC_R_I_IMAGE && r[2].id == MAC_R_I_SLOT && r[3].id == MAC_R_I_MEM && r[4].id == MAC_R_I_HOST &&
              r[5].id == MAC_R_SSID && r[6].id == MAC_R_SIGNAL && r[7].id == MAC_R_I_UP);
        for (int i = 0; i < n; i++) CHECK(r[i].kind == MAC_K_INFO);
    }
#endif
    char up[24];
    mac_uptime_text(up, sizeof(up), 45, 0); CHECK(strcmp(up, "45 s") == 0);
    mac_uptime_text(up, sizeof(up), 59 * 60 + 59, 0); CHECK(strcmp(up, "59 min") == 0);
    mac_uptime_text(up, sizeof(up), 3 * 3600 + 12 * 60 + 9, 1); CHECK(strcmp(up, "3 h 12 min") == 0);
    mac_uptime_text(up, sizeof(up), 2 * 86400 + 5 * 3600 + 900, 0); CHECK(strcmp(up, "2 d 5 h") == 0);
    CHECK(mac_set_rows(MAC_TAB_COUNT + 3, 0, r) >= 1);                    /* an unknown tab reads as Info, never crashes */

    /* tabs: four, always visible, on the left, at least 44 by 44, inside the zone, not touching the pane */
    int x, y, w, h, x2, y2, w2, h2;
    for (int t = 0; t < MAC_TAB_COUNT; t++) {
        mac_tab_box(t, &x, &y, &w, &h);
        CHECK(w >= 56 && h >= 56 && x >= 0 && x + w < MAC_DIV_X - MAC_TAB_X && y >= 0 && y + h <= MAC_TAB_PITCH * MAC_TAB_COUNT);   /* patch UX13: boxes are inside the scrolling column, 56 px tabs */
        CHECK(MAC_TAB_Y0 >= MAC_DRAG_DEAD_Y - 4 && MAC_TAB_Y0 + MAC_TAB_COL_H <= MAC_BOTTOM && MAC_TAB_PITCH - MAC_TAB_H >= 8);   /* the column starts below the drag bar; tabs are 8 px apart; three show */
        if (t > 0) { int px, py, pw, ph; mac_tab_box(t - 1, &px, &py, &pw, &ph); CHECK(py + ph <= y); }
        CHECK(MAC_TAB_TITLE[0][t][0] != '\0' && MAC_TAB_TITLE[1][t][0] != '\0' && MAC_TAB_NAMES[t][0] != '\0');
    }
    mac_done_box(&x, &y, &w, &h);
    CHECK(w >= MAC_TARGET_MIN && h >= MAC_TARGET_MIN && x >= MAC_PANE_X && x + w <= MAC_W && y + h <= MAC_PANE_Y);
    CHECK(MAC_PANE_X > MAC_DIV_X && MAC_PANE_X + MAC_PANE_W <= MAC_W && MAC_PANE_Y + MAC_PANE_H == MAC_BOTTOM && MAC_PANE_ROW_W + 12 <= MAC_PANE_W);
    (void)x2; (void)y2; (void)w2; (void)h2;

    /* the tab state */
    mac_set_t s;
    mac_set_init(&s);
    CHECK(s.tab == MAC_TAB_GENERAL);
    CHECK(mac_set_tab(&s, MAC_TAB_FACES) == 1 && s.tab == MAC_TAB_FACES);
    CHECK(mac_set_tab(&s, MAC_TAB_FACES) == 0);                          /* the same tab again changes nothing */
    CHECK(mac_set_tab(&s, 9) == 0 && mac_set_tab(&s, -1) == 0 && s.tab == MAC_TAB_FACES);

    /* scrolling */
    CHECK(mac_scroll_clamp(-5, 300, 138) == 0 && mac_scroll_clamp(500, 300, 138) == 162 && mac_scroll_clamp(40, 300, 138) == 40 && mac_scroll_clamp(40, 100, 138) == 0);
    int by, bh;
    CHECK(mac_scroll_bar(100, 138, 0, &by, &bh) == 0);                   /* everything fits: no indicator */
    CHECK(mac_scroll_bar(276, 138, 0, &by, &bh) == 1 && by == 0 && bh == 69);
    CHECK(mac_scroll_bar(276, 138, 138, &by, &bh) == 1 && by + bh == 138);   /* at the end the bar touches the bottom of the track */
    CHECK(mac_scroll_bar(276, 138, 999, &by, &bh) == 1 && by + bh == 138);
    CHECK(mac_scroll_bar(5000, 138, 100, &by, &bh) == 1 && bh >= 16);
    CHECK(mac_scroll_bar(276, 138, 69, &by, &bh) == 1 && by == (138 - 69) / 2 + 0);

    /* auto lock: the choices follow the lock core, a tap goes to the next and wraps to Off */
    CHECK(MAC_AUTO_COUNT == LK_AUTO_COUNT);
    for (int i = 0; i < MAC_AUTO_COUNT; i++) CHECK(MAC_AUTO_MIN[i] == LK_AUTO_MINUTES[i] && mlk_auto_ok(MAC_AUTO_MIN[i]));
    CHECK(mac_auto_next(0) == 1 && mac_auto_next(1) == 15 && mac_auto_next(15) == 0 && mac_auto_next(30) == 0 && mac_auto_next(7) == 0); /* a saved 5, 30 or 60 wraps to Off on the next tap */
    char b[16];
    mac_auto_text(b, sizeof(b), 0, 0); CHECK(strcmp(b, "Off") == 0);
    mac_auto_text(b, sizeof(b), 0, 1); CHECK(strcmp(b, "No") == 0);
    mac_auto_text(b, sizeof(b), 15, 0); CHECK(strcmp(b, "15 min") == 0);

    /* the style tiles: five face styles then Pictures while a pack is held */
    CHECK(mac_pair_tiles(0, 0) == 2 && mac_pair_tiles(MPG_SET_STYLES / 2, 1) == (MPG_SET_STYLES % 2 ? 2 : 1) && mac_pair_tiles(MPG_SET_STYLES / 2 + 1, 1) == 0);   /* the face styles then Pictures while a pack is held */
    CHECK(mac_signal_word(-1) == 0 && mac_signal_word(1) == 1 && mac_signal_word(2) == 2 && mac_signal_word(3) == 3 && mac_signal_word(4) == 3);
}

static void test_words_and_sheet(void)
{
    for (int i = 0; i < MAC_S_COUNT; i++) {
        const char* en = MAC_STR[i][0];
        const char* es = MAC_STR[i][1];
        CHECK(en[0] != '\0' && es[0] != '\0');
        CHECK(strlen(en) < 64 && strlen(es) < 64);
        for (const char* p = en; *p; p++) CHECK((unsigned char)*p >= 0x20 && (unsigned char)*p < 0x7F);    /* English stays plain ASCII */
        /* Spanish: ASCII plus the Latin-1 letters as UTF-8 (patch UX07a: the Noto screen fonts draw U+00A1 to U+00FF) */
        for (const unsigned char* p = (const unsigned char*)es; *p; p++) {
            if (*p >= 0x20 && *p < 0x7F) continue;
            CHECK((*p == 0xC2 || *p == 0xC3) && p[1] != 0 && (p[1] & 0xC0) == 0x80 && (*p == 0xC3 || p[1] >= 0xA1));
            p++;
        }
    }
    CHECK(strcmp(mac_str(MAC_S_CANCEL, 0), "Cancel") == 0 && strcmp(mac_str(MAC_S_CANCEL, 1), "Cancelar") == 0);
    CHECK(strcmp(mac_str(-1, 0), "") == 0 && strcmp(mac_str(MAC_S_COUNT, 1), "") == 0);
    CHECK(strcmp(mac_row_label(MAC_R_VOLUME, 1), "Volumen") == 0 && mac_row_label(MAC_R_PAIR0, 0)[0] == '\0');
    for (int row = 0; row < MAC_R_COUNT; row++) {
        const int k = mac_row_kind(row);
        if (k != MAC_K_PAIR) CHECK(mac_row_label(row, 0)[0] != '\0' && mac_row_label(row, 1)[0] != '\0');
    }
    /* the sheet: the saved key "timers" is the Apps tile, "apps" reads as the same, the tile's title says Apps */
    CHECK(mpg_sheet_by_name("timers") == MPG_S_TIMERS && mpg_sheet_by_name("apps") == MPG_S_TIMERS);
    CHECK(strcmp(MPG_SHEET_TITLE[0][MPG_S_TIMERS], "Apps") == 0 && strcmp(MPG_SHEET_TITLE[1][MPG_S_TIMERS], "Apps") == 0);
    mpg_cfg_t c;
    CHECK(mpg_cfg_from_text(&c, "L=clock;R=games;S=10;I=20;A=beep,dance,game,hello;C=volume,brightness,mute,quiet,light,apps,games,wifi,battery") == 1);
    CHECK(c.n_items == 9 && c.items[5] == MPG_S_TIMERS);
    mpg_shape_t sh[MPG_ICON_SHAPES_MAX];
    CHECK(mpg_sheet_icon_shapes(MPG_S_TIMERS, sh) == 4);                 /* four squares */
    /* the sheet stays one row of six tiles (Mute, Quiet, Lock, Apps, Games, Settings; patch NX01: Lock took the place of Light) */
    mpg_sheet_t L;
    mpg_defaults(&c);
    mpg_sheet_layout(&c, &L);
    int tiles = 0, sliders = 0;
    for (int i = 0; i < L.n; i++) {
        if (L.r[i].item < MPG_S_MUTE) sliders++; else tiles++;
        CHECK(L.r[i].item <= MPG_S_COUNT);
    }
    CHECK(sliders == 2 && tiles == 6 && L.r[L.n - 1].item == MPG_S_COUNT);
    CHECK(c.items[4] == MPG_S_LOCK && strcmp(MPG_SHEET_TITLE[0][MPG_S_LOCK], "Lock") == 0 && strcmp(MPG_SHEET_TITLE[1][MPG_S_LOCK], "Bloqueo") == 0);
    CHECK(strcmp(mac_str(MAC_S_LOCK_HINT, 0), "Set a code on the settings page") == 0);   /* the one line the Lock tile and the Apps Lock tile show with no code */
}

/* Patch NX08: every item has its own accent, and the tile background (a quarter of it) stays dark so the light label on its plate always reads. */
static void test_tile_colors(void)
{
    for (int a = 0; a < MAC_APP_COUNT; a++) {
        CHECK(MAC_APP_ACCENT[a] != 0 && mac_luma_pct(MAC_APP_ACCENT[a], MAC_TILE_BG_PCT + 16) < 90);
        for (int b = a + 1; b < MAC_APP_COUNT; b++) CHECK(MAC_APP_ACCENT[a] != MAC_APP_ACCENT[b]);
    }
    const char* games[] = {"memory", "whack", "tictactoe", "bopit", "rps", "eightball", "dice"};
    for (int g = 0; g < 7; g++) {
        CHECK(mac_luma_pct(mac_game_accent(games[g]), MAC_TILE_BG_PCT + 16) < 90);
        for (int h = g + 1; h < 7; h++) CHECK(mac_game_accent(games[g]) != mac_game_accent(games[h]));
    }
    CHECK(mac_game_accent("unknown") == 0x8C96AA && mac_game_accent(NULL) == 0x8C96AA);
    CHECK(MAC_TILE_BG_PCT < MAC_TILE_PRESSED_PCT && MAC_TILE_PRESSED_PCT < MAC_TILE_BORDER_PCT);   /* a press brightens */
}

int main(void)
{
    test_touch();
    test_wall();
    test_tile_colors();
    test_apps();
    test_timers_alarms();
    test_settings();
    test_words_and_sheet();
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("apps core: all checks passed\n");
    return 0;
}

