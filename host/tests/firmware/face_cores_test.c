/* Host test for the face cores (patches F01 to F06): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_face_core.h"
#include "maipai_face_tod_core.h"
#include "maipai_face_clock_core.h"
#include "maipai_face_think_core.h"
#include "maipai_face_timers_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

/* ---- F01: configuration ---- */

static void test_default_is_neutral(void)
{
    mf_config_t c; mf_default(&c);
    uint8_t r, g, b;
    mf_foreground(&c, &r, &g, &b);
#ifdef MF_STYLE_EYES_ONLY /* patch X02: Big eyes is the default */
    CHECK(c.style == MF_STYLE_BIG_EYES && c.colour_mode == MF_COLOUR_NONE);
#else
    CHECK(c.style == MF_STYLE_CLASSIC && c.colour_mode == MF_COLOUR_NONE);
#endif
    CHECK(r == 255 && g == 255 && b == 255);
    CHECK(c.captions == 0 && c.tod == 0 && c.clock_idle_s == 0 && c.thinking_tone == 1);
    CHECK(mf_valid(&c));
#ifndef MF_STYLE_EYES_ONLY
    CHECK(mf_style_eye_offset(c.style) == 0);
#endif
}

static void test_style_and_colour(void)
{
    mf_config_t c; mf_default(&c);
    CHECK(mf_set_style_name(&c, "big_eyes") == MF_OK && c.style == MF_STYLE_BIG_EYES);
#ifndef MF_STYLE_EYES_ONLY
    CHECK(mf_style_eye_offset(MF_STYLE_BIG_EYES) > 0 && mf_style_eye_offset(MF_STYLE_MINIMAL) < 0);
#endif
    CHECK(mf_set_style_name(&c, "huge") == MF_ERR_STYLE && c.style == MF_STYLE_BIG_EYES);
    CHECK(mf_set_style_name(&c, NULL) == MF_ERR_STYLE);
    CHECK(mf_set_colour(&c, "mint") == MF_OK && c.colour_mode == MF_COLOUR_PALETTE);
    uint8_t r, g, b;
    mf_foreground(&c, &r, &g, &b);
    CHECK(r == MF_PALETTE_RGB[0][0] && g == MF_PALETTE_RGB[0][1] && b == MF_PALETTE_RGB[0][2]);
    CHECK(mf_set_colour(&c, "#ff8800") == MF_OK && c.colour_mode == MF_COLOUR_CUSTOM);
    mf_foreground(&c, &r, &g, &b);
    CHECK(r == 0xff && g == 0x88 && b == 0x00);
    CHECK(mf_set_colour(&c, "#FF8800") == MF_OK);
    CHECK(mf_set_colour(&c, "#101010") == MF_ERR_DARK && c.colour_mode == MF_COLOUR_CUSTOM && c.r == 0xFF);
    CHECK(mf_set_colour(&c, "#ff88") == MF_ERR_COLOUR);
    CHECK(mf_set_colour(&c, "ff8800") == MF_ERR_COLOUR);
    CHECK(mf_set_colour(&c, "#gg8800") == MF_ERR_COLOUR);
    CHECK(mf_set_colour(&c, "purple") == MF_ERR_COLOUR);
    CHECK(mf_set_colour(&c, "none") == MF_OK && c.colour_mode == MF_COLOUR_NONE);
    for (int i = 0; i < MF_PALETTE_COUNT; i++) {
        CHECK(mf_luma(MF_PALETTE_RGB[i][0], MF_PALETTE_RGB[i][1], MF_PALETTE_RGB[i][2]) >= MF_MIN_LUMA);
    }
}

#ifdef MF_STYLE_EYES_ONLY
/* ---- X02: five styles, the dropped ones, the screen colour, the emotion tint, blob version 3 ---- */
static void test_x02_styles_and_colours(void)
{
    mf_config_t c; mf_default(&c);
    CHECK(c.style == MF_STYLE_BIG_EYES && c.emotion_tint == 1 && c.bg_mode == MF_COLOUR_NONE);
    CHECK(mf_set_style_name(&c, "eyes_only") == MF_OK && c.style == MF_STYLE_EYES_ONLY);
    CHECK(mf_set_style_name(&c, "stock") == MF_OK && c.style == MF_STYLE_STOCK);
    CHECK(mf_set_style_name(&c, "classic") == MF_OK && c.style == MF_STYLE_CLASSIC);
    /* the dropped names are accepted and mean Big eyes, so an old setting never errors */
    static const char* const gone[] = {"round", "cat", "robot", "sleepy", "retro_pixel", "heart_eyes"};
    for (int i = 0; i < 6; i++) {
        CHECK(mf_set_style_name(&c, gone[i]) == MF_OK && c.style == MF_STYLE_BIG_EYES);
    }
    CHECK(mf_set_style_name(&c, "huge") == MF_ERR_STYLE);
    for (int s = 0; s < MF_STYLE_COUNT; s++) {
        CHECK((mf_style_ok(s) != 0) == (s == 0 || s == 1 || s == 2 || s == 9 || s == 10));
        if (mf_style_ok(s)) CHECK(mf_look_id(s) >= 0 && mf_look_id(s) <= 4);
    }
    CHECK(mf_look_id(MF_STYLE_STOCK) == 2 && mf_look_id(MF_STYLE_BIG_EYES) == 0 && mf_look_id(MF_STYLE_EYES_ONLY) == 1);
    CHECK(mf_look_id(5) == 0 && mf_look_id(99) == 0); /* a dropped or unknown style draws as Big eyes */
    /* the screen colour: black, a palette colour dimmed, or the person's own dark colour; never one that hides white eyes */
    uint8_t r, g, b;
    mf_background(&c, &r, &g, &b);
    CHECK(r == 0 && g == 0 && b == 0);
    CHECK(mf_set_background(&c, "mint") == MF_OK && c.bg_mode == MF_COLOUR_PALETTE);
    mf_background(&c, &r, &g, &b);
    CHECK(r == MF_PALETTE_RGB[0][0] * MF_BG_PCT / 100 && g > r && mf_luma(r, g, b) <= MF_MAX_BG_LUMA);
    CHECK(mf_set_background(&c, "#102030") == MF_OK && c.bg_mode == MF_COLOUR_CUSTOM);
    CHECK(mf_set_background(&c, "#f0f0f0") == MF_ERR_BRIGHT && c.bg_r == 0x10);
    CHECK(mf_set_background(&c, "blue") == MF_ERR_COLOUR);
    CHECK(mf_set_background(&c, "none") == MF_OK && c.bg_mode == MF_COLOUR_NONE);
    for (int i = 0; i < MF_PALETTE_COUNT; i++) {
        mf_config_t p; mf_default(&p);
        p.bg_mode = MF_COLOUR_PALETTE; p.bg_palette = (uint8_t)i;
        mf_background(&p, &r, &g, &b);
        CHECK(mf_luma(r, g, b) <= MF_MAX_BG_LUMA && mf_luma(r, g, b) >= 20); /* dark, but a colour you can see */
    }
}

static void test_x02_blob_versions_and_migration(void)
{
    mf_config_t c; mf_default(&c);
    mf_set_style_name(&c, "stock"); mf_set_background(&c, "lilac"); c.emotion_tint = 0;
    uint8_t buf[MF_BLOB_MAX];
    size_t n = mf_save(&c, buf, sizeof(buf));
    CHECK(n > 0 && n <= MF_BLOB_MAX && buf[0] == 3);
    mf_config_t d;
    CHECK(mf_load(&d, buf, n) == MF_OK && memcmp(&c, &d, sizeof(c)) == 0);
    /* a version 2 blob (no tint, no screen colour) is still read: the defaults fill in */
    uint8_t old[MF_BLOB_MAX];
    memcpy(old, buf, 20);
    old[0] = 2;
    old[1] = MF_STYLE_MINIMAL;
    const uint16_t crc = mf_crc16(old, 20);
    old[20] = (uint8_t)(crc >> 8); old[21] = (uint8_t)(crc & 0xFF);
    CHECK(mf_load(&d, old, 22) == MF_OK && d.style == MF_STYLE_MINIMAL && d.emotion_tint == 1 && d.bg_mode == MF_COLOUR_NONE);
    /* a saved dropped style (ids 3 to 8) loads as Big eyes and the rest of the saved face survives */
    for (int s = MF_STYLE_DROPPED_FIRST; s <= MF_STYLE_DROPPED_LAST; s++) {
        old[1] = (uint8_t)s;
        const uint16_t c2 = mf_crc16(old, 20);
        old[20] = (uint8_t)(c2 >> 8); old[21] = (uint8_t)(c2 & 0xFF);
        CHECK(mf_load(&d, old, 22) == MF_OK && d.style == MF_STYLE_BIG_EYES && d.captions == c.captions);
    }
    /* an id that never existed is refused */
    old[1] = 77;
    const uint16_t c3 = mf_crc16(old, 20);
    old[20] = (uint8_t)(c3 >> 8); old[21] = (uint8_t)(c3 & 0xFF);
    CHECK(mf_load(&d, old, 22) == MF_ERR_RANGE);
}
#endif

static void test_hours_and_language(void)
{
    mf_config_t c; mf_default(&c);
    CHECK(mf_set_hours(&c, 5, 8, 17, 22) == MF_OK && c.tod_from[3] == 22);
    CHECK(mf_set_hours(&c, 8, 8, 17, 22) == MF_ERR_HOURS);
    CHECK(mf_set_hours(&c, 5, 8, 17, 24) == MF_ERR_HOURS);
    CHECK(mf_set_hours(&c, -1, 8, 17, 22) == MF_ERR_HOURS);
    CHECK(c.tod_from[0] == 5);
    CHECK(mf_set_lang(&c, "es") == MF_OK && c.lang == MF_LANG_ES);
    CHECK(mf_set_lang(&c, "xx") == MF_ERR_LANG && c.lang == MF_LANG_ES); /* "fr" is a language since patch U06 */
    CHECK(strlen(mf_err_word(MF_ERR_DARK)) > 20);
}

static void test_save_load(void)
{
    mf_config_t c; mf_default(&c);
    mf_set_style_name(&c, "minimal"); mf_set_colour(&c, "#40c0ff"); c.captions = 1; c.tod = 1;
    mf_set_hours(&c, 7, 10, 19, 22); mf_set_lang(&c, "es"); c.clock24 = 1; c.clock_style = 1; c.clock_idle_s = 300;
    uint8_t buf[MF_BLOB_MAX];
    size_t n = mf_save(&c, buf, sizeof(buf));
    CHECK(n > 0 && n <= MF_BLOB_MAX);
    mf_config_t d;
    CHECK(mf_load(&d, buf, n) == MF_OK);
    CHECK(memcmp(&c, &d, sizeof(c)) == 0);
    buf[3] ^= 0x01; /* a damaged byte */
    CHECK(mf_load(&d, buf, n) == MF_ERR_RANGE);
    mf_config_t plain; mf_default(&plain);
    CHECK(memcmp(&plain, &d, sizeof(d)) == 0); /* back to the plain face */
    CHECK(mf_load(&d, buf, n - 1) == MF_ERR_RANGE);
    CHECK(mf_load(&d, NULL, 0) == MF_ERR_RANGE);
    CHECK(mf_save(&c, buf, 4) == 0);
    /* a blob with a good check but a style that does not exist is refused */
    mf_save(&c, buf, sizeof(buf));
    buf[1] = 99;
    const uint16_t crc = mf_crc16(buf, n - 2);
    buf[n - 2] = (uint8_t)(crc >> 8); buf[n - 1] = (uint8_t)(crc & 0xFF);
    CHECK(mf_load(&d, buf, n) == MF_ERR_RANGE);
}

/* ---- F03: time of day ---- */

static void test_bands(void)
{
    mf_config_t c; mf_default(&c);
    CHECK(mf_band_for_minute(&c, 23 * 60) == MF_BAND_DAY); /* off: always the day look */
    c.tod = 1; /* 6, 9, 18, 21 */
    CHECK(mf_band_for_minute(&c, 6 * 60) == MF_BAND_MORNING);
    CHECK(mf_band_for_minute(&c, 8 * 60 + 59) == MF_BAND_MORNING);
    CHECK(mf_band_for_minute(&c, 9 * 60) == MF_BAND_DAY);
    CHECK(mf_band_for_minute(&c, 17 * 60 + 59) == MF_BAND_DAY);
    CHECK(mf_band_for_minute(&c, 18 * 60) == MF_BAND_EVENING);
    CHECK(mf_band_for_minute(&c, 21 * 60) == MF_BAND_NIGHT);
    CHECK(mf_band_for_minute(&c, 0) == MF_BAND_NIGHT);   /* night runs through midnight */
    CHECK(mf_band_for_minute(&c, 5 * 60 + 59) == MF_BAND_NIGHT);
    CHECK(mf_band_for_minute(&c, -1) == MF_BAND_DAY);    /* clock never set */
    CHECK(mf_band_for_minute(&c, 1440) == MF_BAND_DAY);
    CHECK(mf_band_lid_cap(MF_BAND_NIGHT) < mf_band_lid_cap(MF_BAND_EVENING));
    CHECK(mf_band_lid_cap(MF_BAND_DAY) == 100 && mf_band_dim_pct(MF_BAND_DAY) == 100);
    CHECK(mf_band_dim_pct(MF_BAND_NIGHT) < mf_band_dim_pct(MF_BAND_EVENING));
    CHECK(mf_band_dim_pct(MF_BAND_NIGHT) >= 70);   /* patch UI11: the night colors stay readable (55 was too dim) */
    CHECK(mf_scale_channel(255, 55) == 140 && mf_scale_channel(0, 55) == 0 && mf_scale_channel(255, 100) == 255);
    /* even the dimmest night colour of the dimmest palette colour stays visible */
    for (int i = 0; i < MF_PALETTE_COUNT; i++) {
        const int l = mf_luma(mf_scale_channel(MF_PALETTE_RGB[i][0], 55), mf_scale_channel(MF_PALETTE_RGB[i][1], 55),
                              mf_scale_channel(MF_PALETTE_RGB[i][2], 55));
        CHECK(l >= 40);
    }
}

/* ---- F04: clock ---- */

static void test_clock_digits(void)
{
    int d[4];
    CHECK(mf_clock_digits(0, 5, 0, d) == MF_AMPM_AM && d[0] == 1 && d[1] == 2 && d[2] == 0 && d[3] == 5);
    CHECK(mf_clock_digits(12, 0, 0, d) == MF_AMPM_PM && d[0] == 1 && d[1] == 2);
    CHECK(mf_clock_digits(9, 41, 0, d) == MF_AMPM_AM && d[0] == MF_DIGIT_BLANK && d[1] == 9 && d[2] == 4 && d[3] == 1);
    CHECK(mf_clock_digits(21, 7, 0, d) == MF_AMPM_PM && d[0] == MF_DIGIT_BLANK && d[1] == 9 && d[2] == 0 && d[3] == 7);
    CHECK(mf_clock_digits(9, 41, 1, d) == MF_AMPM_NONE && d[0] == 0 && d[1] == 9);
    CHECK(mf_clock_digits(23, 59, 1, d) == MF_AMPM_NONE && d[0] == 2 && d[1] == 3 && d[2] == 5 && d[3] == 9);
}

static void test_segments(void)
{
    CHECK(mf_digit_segments(8) == 0x7F);
    CHECK(mf_digit_segments(1) == 0x06);
    CHECK(mf_digit_segments(MF_DIGIT_BLANK) == 0 && mf_digit_segments(-1) == 0);
    for (int ring = 0; ring < 2; ring++) {
        mf_clock_layout_t l = mf_clock_layout(ring);
        CHECK((l.digit_h - 3 * l.bar) % 2 == 0);
        const int len = (l.digit_h - 3 * l.bar) / 2;
        CHECK(len > 0);
        for (int s = 0; s < 7; s++) {
            int x, y, w, h;
            mf_seg_rect(s, 10, 20, l.digit_w, l.digit_h, l.bar, &x, &y, &w, &h);
            CHECK(x >= 10 && y >= 20 && x + w <= 10 + l.digit_w && y + h <= 20 + l.digit_h && w > 0 && h > 0);
        }
        CHECK(mf_clock_width(&l) <= 320);
    }
    /* every digit mask lights only real bars and 8 lights all seven */
    for (int dgt = 0; dgt < 10; dgt++) {
        CHECK((mf_digit_segments(dgt) & ~0x7F) == 0);
    }
    /* the ring layout fits inside the ring: the farthest corner of the digits is inside 106 px of the centre */
    mf_clock_layout_t r = mf_clock_layout(1);
    const int half_w = mf_clock_width(&r) / 2, half_h = r.digit_h / 2 + 20;
    CHECK(half_w * half_w + half_h * half_h < 106 * 106);
}

/* Patch K11: only English is built in; every other language is a language pack. These are the Spanish words a pack carries. */
static const char ES_WORDS[] =
    "lang=es\norder=dmy\nweekdays=dom,lun,mar,mie,jue,vie,sab\n"
    "months=ene,feb,mar,abr,may,jun,jul,ago,sep,oct,nov,dic\nalarm=Alarma\ntimer=Tiempo\n";

static void test_date_line(void)
{
    char out[24];
    mlw_t es;
    CHECK(mlw_parse(ES_WORDS, sizeof(ES_WORDS) - 1, &es) == MLW_OK);
    mf_date_line(out, sizeof(out), &MLW_EN, 0, 15, 10);
    CHECK(strcmp(out, "Sun Nov 15") == 0);
    mf_date_line(out, sizeof(out), NULL, 0, 15, 10); /* no words: English */
    CHECK(strcmp(out, "Sun Nov 15") == 0);
    mf_date_line(out, sizeof(out), &es, 0, 15, 10);
    CHECK(strcmp(out, "dom 15 nov") == 0);
    mf_date_line(out, sizeof(out), &es, 3, 2, 2);
    CHECK(strcmp(out, "mie 2 mar") == 0);
    mf_date_line(out, sizeof(out), &MLW_EN, 9, 15, 10);
    CHECK(out[0] == '\0');
    /* the built-in words are plain ASCII, and the date line of a face whose language has no pack is the English one */
    for (int d = 0; d < 7; d++) { for (const unsigned char* p = (const unsigned char*)MLW_EN.wd[d]; *p; p++) CHECK(*p < 128); }
    for (int m = 0; m < 12; m++) { for (const unsigned char* p = (const unsigned char*)MLW_EN.mon[m]; *p; p++) CHECK(*p < 128); }
    CHECK(mlw_for(&es, "es") == &es && mlw_for(&es, "fr") == &MLW_EN && mlw_for(NULL, "es") == &MLW_EN && mlw_for(&es, "en") == &MLW_EN);
}

static void test_clock_wanted(void)
{
    mf_clock_state_t s = {100, 0};
    CHECK(!mf_clock_wanted(&s, 1000, 0, 1, 0, 1));          /* clock_idle_s 0: never by itself */
    CHECK(!mf_clock_wanted(&s, 159, 60, 1, 0, 1));          /* idle only 59 s */
    CHECK(mf_clock_wanted(&s, 160, 60, 1, 0, 1));
    CHECK(!mf_clock_wanted(&s, 160, 60, 0, 0, 1));          /* busy */
    CHECK(!mf_clock_wanted(&s, 160, 60, 1, 1, 1));          /* blocked: a privacy look or a ring is never covered */
    CHECK(!mf_clock_wanted(&s, 160, 60, 1, 0, 0));          /* the time is not set */
    s.forced_until_s = 500;
    CHECK(mf_clock_wanted(&s, 200, 0, 1, 0, 1));            /* asked for, even with no idle setting */
    CHECK(!mf_clock_wanted(&s, 200, 0, 1, 1, 1));           /* but still never over a blocking state */
    CHECK(!mf_clock_wanted(&s, 500, 0, 1, 0, 1));           /* the ask ran out */
}

/* ---- F05: thinking cue ---- */

static void test_thinking(void)
{
    mf_think_t t; mf_think_init(&t);
    CHECK(mf_think_begin(&t, 1000, 1) == 1 && t.active);
    CHECK(mf_think_begin(&t, 1100, 1) == 0);               /* already on */
    CHECK(mf_think_end(&t) == 1 && !t.active);
    CHECK(mf_think_end(&t) == 0);
    CHECK(mf_think_begin(&t, 1000 + MF_THINK_TONE_GAP_MS - 1, 1) == 0 && t.active); /* the dots show, no second tone */
    mf_think_end(&t);
    CHECK(mf_think_begin(&t, 1000 + MF_THINK_TONE_GAP_MS, 1) == 1);
    mf_think_end(&t);
    mf_think_init(&t);
    CHECK(mf_think_begin(&t, 50, 0) == 0 && t.active);     /* tone off: dots only */
    CHECK(!mf_think_expired(&t, 50 + MF_THINK_MAX_MS - 1) && mf_think_expired(&t, 50 + MF_THINK_MAX_MS));
    mf_think_end(&t);
    CHECK(!mf_think_expired(&t, 999999999u));
    /* the clock wrapping at 2^32 ms does not break the limit */
    mf_think_init(&t);
    mf_think_begin(&t, 0xFFFFFF00u, 0);
    CHECK(!mf_think_expired(&t, 0xFFFFFF00u + 1000u) && mf_think_expired(&t, 0xFFFFFF00u + MF_THINK_MAX_MS));
    for (uint32_t ms = 0; ms < 3000; ms += 50) {
        for (int i = 0; i < MF_THINK_DOTS; i++) {
            const int l = mf_think_dot_level(ms, i);
            CHECK(l >= 60 && l <= 255);
        }
    }
    CHECK(mf_think_dot_level(0, 0) != mf_think_dot_level(0, 1)); /* a wave, not all dots at once */
}

/* ---- F06: timer chips ---- */

static mf_tchip_t chip(uint32_t id, int kind, int32_t left, const char* label)
{
    mf_tchip_t c; memset(&c, 0, sizeof(c));
    c.id = id; c.kind = (uint8_t)kind; c.left_s = left; strncpy(c.label, label, sizeof(c.label) - 1);
    return c;
}

static void test_countdown_text(void)
{
    char out[16];
    mf_fmt_left(out, sizeof(out), 272); CHECK(strcmp(out, "4:32") == 0);
    mf_fmt_left(out, sizeof(out), 3723); CHECK(strcmp(out, "1:02:03") == 0);
    mf_fmt_left(out, sizeof(out), 0); CHECK(strcmp(out, "0:00") == 0);
    mf_fmt_left(out, sizeof(out), -5); CHECK(strcmp(out, "0:00") == 0);
    mf_fmt_left(out, sizeof(out), 59); CHECK(strcmp(out, "0:59") == 0);
    mf_fmt_left(out, sizeof(out), 86400); CHECK(strcmp(out, "24:00:00") == 0);
}

static void test_chip_text_and_words(void)
{
    char out[40];
    mlw_t es;
    CHECK(mlw_parse(ES_WORDS, sizeof(ES_WORDS) - 1, &es) == MLW_OK);
    mf_tchip_t a = chip(1, 1, 272, "tea");
    mf_chip_text(out, sizeof(out), &MLW_EN, &a); CHECK(strcmp(out, "tea 4:32") == 0);
    mf_tchip_t b = chip(2, 1, 60, "");
    mf_chip_text(out, sizeof(out), &MLW_EN, &b); CHECK(strcmp(out, "Timer 1:00") == 0);
    mf_chip_text(out, sizeof(out), NULL, &b); CHECK(strcmp(out, "Timer 1:00") == 0);
    mf_chip_text(out, sizeof(out), &es, &b); CHECK(strcmp(out, "Tiempo 1:00") == 0);
    mf_tchip_t c = chip(3, 2, 30, "");
    mf_chip_text(out, sizeof(out), &es, &c); CHECK(strcmp(out, "Alarma 0:30") == 0);
    mf_tchip_t d = chip(4, 1, 5025, "a very long label indeed");
    mf_chip_text(out, sizeof(out), &MLW_EN, &d); CHECK(strcmp(out, "a very lo 1:23:45") == 0);
}

static void test_pick_and_place(void)
{
    mf_tchip_t in[8], out[MF_CHIP_MAX];
    int more = -1;
    in[0] = chip(1, 1, 600, "pasta"); in[1] = chip(2, 1, 180, "tea"); in[2] = chip(3, 1, 180, "egg");
    CHECK(mf_tchips_pick(in, 3, out, &more) == 3 && more == 0);
    CHECK(out[0].id == 2 && out[1].id == 3 && out[2].id == 1); /* soonest first, ties by id */
    in[3] = chip(4, 1, 30, "a"); in[4] = chip(5, 1, 40, "b");
    CHECK(mf_tchips_pick(in, 4, out, &more) == 4 && more == 0);
    CHECK(mf_tchips_pick(in, 5, out, &more) == 3 && more == 2);
    CHECK(out[0].id == 4 && out[1].id == 5 && out[2].id == 2);
    CHECK(mf_tchips_pick(in, 0, out, &more) == 0 && more == 0);
    /* placement: every slot of every layout is on screen, nothing overlaps, and the grid sits below the mouth (y 196) */
    for (int slots = 1; slots <= MF_CHIP_MAX; slots++) {
        for (int k = 0; k < slots; k++) {
            int x, y;
            mf_chip_place(slots, k, &x, &y);
            CHECK(x >= 0 && x + MF_CHIP_W <= 320 && y >= 190 && y + MF_CHIP_H <= 240);
            for (int j = 0; j < k; j++) {
                int x2, y2;
                mf_chip_place(slots, j, &x2, &y2);
                CHECK(!(x < x2 + MF_CHIP_W && x2 < x + MF_CHIP_W && y < y2 + MF_CHIP_H && y2 < y + MF_CHIP_H));
            }
        }
    }
    int x, y;
    mf_chip_place(1, 0, &x, &y); CHECK(x == 86 && y == 216);
    mf_chip_place(3, 2, &x, &y); CHECK(x == 86);            /* the lone chip of an odd count is centred */
}

int main(void)
{
    test_default_is_neutral();
    test_style_and_colour();
#ifdef MF_STYLE_EYES_ONLY
    test_x02_styles_and_colours();
    test_x02_blob_versions_and_migration();
#endif
    test_hours_and_language();
    test_save_load();
    test_bands();
    test_clock_digits();
    test_segments();
    test_date_line();
    test_clock_wanted();
    test_thinking();
    test_countdown_text();
    test_chip_text_and_words();
    test_pick_and_place();
    if (failures) { printf("%d failure(s)\n", failures); return 1; }
    printf("face cores: all passed\n");
    return 0;
}
