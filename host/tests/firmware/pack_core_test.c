/* Host test for the face style packs, the six languages and the caption size (patch U06):
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include <string.h>
#include "maipai_face_core.h"
#include "maipai_face_clock_core.h"
#include "maipai_face_timers_core.h"
#include "maipai_pack_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void test_style_names_and_table(void)
{
    mf_config_t c;
    mf_default(&c);
    static const char* const want[9] = {"classic", "big_eyes", "minimal", "round", "cat",
                                        "robot",   "sleepy",   "retro_pixel", "heart_eyes"};
    CHECK(MF_STYLE_COUNT == 9);
    for (int i = 0; i < 9; i++) {
        CHECK(strcmp(MF_STYLE_NAMES[i], want[i]) == 0);
        CHECK(mf_set_style_name(&c, want[i]) == MF_OK && c.style == i);
        CHECK(mf_valid(&c));
        CHECK(mp_pack(i)->radius_pct <= 100 && mp_pack(i)->lid_cap >= 30 && mp_pack(i)->lid_cap <= 100);
        CHECK(mf_style_eye_offset(i) >= -60 && mf_style_eye_offset(i) <= 60);
    }
    CHECK(mf_set_style_name(&c, "pirate") == MF_ERR_STYLE);
    /* the first three keep their old look */
    CHECK(mf_style_eye_offset(MF_STYLE_CLASSIC) == 0 && mf_style_eye_offset(MF_STYLE_BIG_EYES) == 60 &&
          mf_style_eye_offset(MF_STYLE_MINIMAL) == -40);
    CHECK(mp_pack(MF_STYLE_CLASSIC)->extras == MP_X_NONE && mp_pack(MF_STYLE_CLASSIC)->radius_pct == 100);
    /* unknown styles fall back to the classic row */
    CHECK(mp_pack(99) == mp_pack(MF_STYLE_CLASSIC) && mp_pack(-1) == mp_pack(MF_STYLE_CLASSIC));
    c.style = 9;
    CHECK(!mf_valid(&c));
}

static void test_pack_shapes(void)
{
    CHECK(mp_pack(MF_STYLE_PIXEL)->radius_pct == 0); /* square eyes */
    CHECK(mp_pack(MF_STYLE_ROBOT)->radius_pct > 0 && mp_pack(MF_STYLE_ROBOT)->radius_pct < 100);
    CHECK(mp_pack(MF_STYLE_SLEEPY)->lid_cap < 100);
    CHECK(mp_lid_cap(MF_STYLE_SLEEPY, 100) == mp_pack(MF_STYLE_SLEEPY)->lid_cap);
    CHECK(mp_lid_cap(MF_STYLE_SLEEPY, 40) == 40); /* the band can still make it sleepier */
    CHECK(mp_lid_cap(MF_STYLE_CLASSIC, 70) == 70);
    CHECK(mp_eye_radius(100, 32) == 0x7FFF);
    CHECK(mp_eye_radius(0, 32) == 0);
    CHECK(mp_eye_radius(22, 32) == 3);
    CHECK(mp_pack(MF_STYLE_ROUND)->gap_off < 0 && mp_pack(MF_STYLE_ROBOT)->gap_off > 0);
}

static void test_extras_stay_on_screen(void)
{
    const int kinds[3] = {MP_X_CAT, MP_X_ROBOT, MP_X_HEARTS};
    const int counts[3] = {10, 4, 6};
    for (int k = 0; k < 3; k++) {
        md_part_t parts[MP_MAX_EXTRA_PARTS];
        const int n = mp_extra_parts(kinds[k], parts, MP_MAX_EXTRA_PARTS);
        CHECK(n == counts[k]);
        for (int i = 0; i < n; i++) {
            CHECK(parts[i].x - parts[i].w / 2 >= -160 && parts[i].x + parts[i].w / 2 <= 160);
            CHECK(parts[i].y - parts[i].h / 2 >= -120 && parts[i].y + parts[i].h / 2 <= 120);
            CHECK(parts[i].opa == 255);
        }
    }
    md_part_t none[MP_MAX_EXTRA_PARTS];
    CHECK(mp_extra_parts(MP_X_NONE, none, MP_MAX_EXTRA_PARTS) == 0);
    CHECK(mp_extra_parts(MP_X_CAT, none, 3) == 0); /* a buffer that is too small writes nothing */
    /* cat whiskers stay clear of the mouth (centre, 26 down) and ears clear of the eyes (70 out, 16 up) */
    md_part_t cat[MP_MAX_EXTRA_PARTS];
    const int n = mp_extra_parts(MP_X_CAT, cat, MP_MAX_EXTRA_PARTS);
    for (int i = 0; i < n; i++) {
        CHECK(!(cat[i].x > -40 && cat[i].x < 40 && cat[i].y > 5));
        CHECK(cat[i].y < -80 || cat[i].y > 20);
    }
    CHECK(mp_extras_cover_eyes(MP_X_HEARTS) && !mp_extras_cover_eyes(MP_X_CAT) && !mp_extras_cover_eyes(MP_X_ROBOT));
}

static void test_languages(void)
{
    mf_config_t c;
    mf_default(&c);
    for (int i = 0; i < MF_LANG_COUNT; i++) {
        CHECK(mf_set_lang(&c, MF_LANG_CODES[i]) == MF_OK && c.lang == i && mf_valid(&c));
    }
    CHECK(mf_set_lang(&c, "fr") == MF_OK && c.lang == MF_LANG_FR);
    CHECK(mf_set_lang(&c, "de") == MF_OK && c.lang == MF_LANG_DE);
    CHECK(mf_set_lang(&c, "pt") == MF_OK && c.lang == MF_LANG_PT);
    CHECK(mf_set_lang(&c, "it") == MF_OK && c.lang == MF_LANG_IT);
    CHECK(mf_set_lang(&c, "ja") == MF_ERR_LANG && c.lang == MF_LANG_IT);
    CHECK(mf_set_lang(&c, NULL) == MF_ERR_LANG && mf_set_lang(&c, "") == MF_ERR_LANG && mf_set_lang(&c, "EN") == MF_ERR_LANG);
    c.lang = 6;
    CHECK(!mf_valid(&c));
    CHECK(strstr(mf_err_word(MF_ERR_LANG), "fr, de, pt or it") != NULL);
}

static void test_date_lines_are_plain_ascii(void)
{
    char out[32];
    mf_date_line(out, sizeof(out), MF_LANG_EN, 0, 15, 10);
    CHECK(strcmp(out, "Sun Nov 15") == 0);
    mf_date_line(out, sizeof(out), MF_LANG_ES, 0, 15, 10);
    CHECK(strcmp(out, "dom 15 nov") == 0);
    mf_date_line(out, sizeof(out), MF_LANG_FR, 1, 3, 7);
    CHECK(strcmp(out, "lun 3 aou") == 0);
    mf_date_line(out, sizeof(out), MF_LANG_DE, 3, 24, 11);
    CHECK(strcmp(out, "Mi 24 Dez") == 0);
    mf_date_line(out, sizeof(out), MF_LANG_PT, 2, 1, 8);
    CHECK(strcmp(out, "ter 1 set") == 0);
    mf_date_line(out, sizeof(out), MF_LANG_IT, 6, 9, 4);
    CHECK(strcmp(out, "sab 9 mag") == 0);
    mf_date_line(out, sizeof(out), 9, 0, 15, 10); /* an unknown language reads as English */
    CHECK(strcmp(out, "Sun Nov 15") == 0);
    mf_date_line(out, sizeof(out), MF_LANG_FR, 9, 15, 10);
    CHECK(out[0] == '\0');
    for (int l = 0; l < MF_LANG_COUNT; l++) {
        for (int d = 0; d < 7; d++) {
            CHECK(strlen(MF_WEEKDAY[l][d]) >= 2 && strlen(MF_WEEKDAY[l][d]) <= 3);
            for (const unsigned char* p = (const unsigned char*)MF_WEEKDAY[l][d]; *p; p++) CHECK(*p < 128);
        }
        for (int m = 0; m < 12; m++) {
            CHECK(strlen(MF_MONTH[l][m]) == 3);
            for (const unsigned char* p = (const unsigned char*)MF_MONTH[l][m]; *p; p++) CHECK(*p < 128);
        }
    }
    /* Spanish stays at index 1: older code and tests read it there */
    CHECK(strcmp(MF_WEEKDAY[1][0], "dom") == 0 && strcmp(MF_MONTH[1][0], "ene") == 0);
}

static void test_timer_words(void)
{
    for (int l = 0; l < MF_LANG_COUNT; l++) {
        CHECK(strlen(mf_kind_word(l, 1)) >= 4 && strlen(mf_kind_word(l, 2)) >= 4);
        for (const unsigned char* p = (const unsigned char*)mf_kind_word(l, 2); *p; p++) CHECK(*p < 128);
    }
    CHECK(strcmp(mf_kind_word(MF_LANG_EN, 2), "Alarm") == 0 && strcmp(mf_kind_word(MF_LANG_ES, 1), "Tiempo") == 0);
    CHECK(strcmp(mf_kind_word(MF_LANG_DE, 2), "Wecker") == 0 && strcmp(mf_kind_word(MF_LANG_IT, 2), "Sveglia") == 0);
    CHECK(strcmp(mf_kind_word(77, 2), "Alarm") == 0); /* unknown reads as English */
}

static void test_caption_size(void)
{
    mf_config_t c;
    mf_default(&c);
    CHECK(c.caption_size == 1 && MF_CAPTION_PX[c.caption_size] == 16);
    CHECK(mf_set_caption_size(&c, "small") == MF_OK && c.caption_size == 0 && MF_CAPTION_PX[0] == 14);
    CHECK(mf_set_caption_size(&c, "large") == MF_OK && c.caption_size == 2 && MF_CAPTION_PX[2] == 20);
    CHECK(mf_set_caption_size(&c, "huge") == MF_ERR_RANGE && c.caption_size == 2);
    CHECK(mf_set_caption_size(&c, NULL) == MF_ERR_RANGE);
    c.caption_size = 3;
    CHECK(!mf_valid(&c));
}

static void test_blob_v2_and_old_v1(void)
{
    mf_config_t a, b;
    mf_default(&a);
    mf_set_style_name(&a, "heart_eyes");
    mf_set_lang(&a, "de");
    mf_set_caption_size(&a, "large");
    uint8_t buf[MF_BLOB_MAX];
    const size_t n = mf_save(&a, buf, sizeof(buf));
    CHECK(n == 22 && buf[0] == 2);
    CHECK(mf_load(&b, buf, n) == MF_OK);
    CHECK(b.style == MF_STYLE_HEARTS && b.lang == MF_LANG_DE && b.caption_size == 2);
    /* a saved record from before this patch (version 1, 21 bytes, no caption size) still loads, with the medium size */
    uint8_t v1[21];
    memcpy(v1, buf, 19);
    v1[0] = 1;
    v1[2 - 1 + 0] = MF_STYLE_CAT; /* the style byte */
    const uint16_t crc = mf_crc16(v1, 19);
    v1[19] = (uint8_t)(crc >> 8);
    v1[20] = (uint8_t)(crc & 0xFF);
    CHECK(mf_load(&b, v1, sizeof(v1)) == MF_OK && b.style == MF_STYLE_CAT && b.caption_size == 1);
    /* the wrong length for a version, a bad check and a bad version are refused */
    CHECK(mf_load(&b, v1, sizeof(v1) - 1) == MF_ERR_RANGE);
    uint8_t bad[MF_BLOB_MAX];
    memcpy(bad, buf, n);
    bad[10] ^= 1;
    CHECK(mf_load(&b, bad, n) == MF_ERR_RANGE);
    memcpy(bad, buf, n);
    bad[0] = 3;
    CHECK(mf_load(&b, bad, n) == MF_ERR_RANGE);
    CHECK(mf_load(&b, buf, 2) == MF_ERR_RANGE && mf_load(&b, NULL, 0) == MF_ERR_RANGE);
}

int main(void)
{
    test_style_names_and_table();
    test_pack_shapes();
    test_extras_stay_on_screen();
    test_languages();
    test_date_lines_are_plain_ascii();
    test_timer_words();
    test_caption_size();
    test_blob_v2_and_old_v1();
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
