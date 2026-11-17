/* Host test for the unit's preferences table (patch TA01): keys match the host, flash keys fit, defaults, all-or-nothing
 * apply, the colour mode names, the bubble rule and the JSON out. cc -std=c99 -Wall -Wextra -Werror -I<headers> prefs_core_test.c */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "maipai_prefs_core.h"

static int fails;
#define CHECK(c)                                                \
    do {                                                        \
        if (!(c)) {                                             \
            printf("FAIL line %d: %s\n", __LINE__, #c);         \
            fails++;                                            \
        }                                                       \
    } while (0)

static void test_table(void)
{
    /* the host's PREFS keys, in its order (host/maipai_body/unit_prefs.py) */
    const char* host[] = {"emotion_faces", "overlays_enabled", "filler_mode", "filler_wait_s", "listen_sound", "listen_light",
                          "listen_light_colour", "listen_face", "fx_crt", "fx_colour_mode", "fx_night_dim", "fx_glow",
                          "speech_bubble", "thinking_dots", "captions_mode", "top_bar", "turn_to_faces"};
    CHECK(MP_COUNT == 19); /* the host's 17 (patch N01 added captions_mode and top_bar, patch S11 turn_to_faces) and pickup_reaction, which the pickup patch reads, and status_icons (patch UI04) */
    CHECK(strcmp(MP_DEFS[MP_CAPTIONS_MODE].key, "captions_mode") == 0 && MP_DEFS[MP_CAPTIONS_MODE].unit == 1 && MP_DEFS[MP_CAPTIONS_MODE].def == 0);
    CHECK(strcmp(MP_DEFS[MP_TOP_BAR].key, "top_bar") == 0 && MP_DEFS[MP_TOP_BAR].unit == 1 && MP_DEFS[MP_TOP_BAR].def == 0);
    CHECK(strcmp(MP_DEFS[MP_TURN_TO_FACES].key, "turn_to_faces") == 0 && MP_DEFS[MP_TURN_TO_FACES].unit == 1 && MP_DEFS[MP_TURN_TO_FACES].def == 1 && strlen(MP_DEFS[MP_TURN_TO_FACES].nvs) <= 15);
    CHECK(strcmp(MP_DEFS[MP_PICKUP_REACTION].key, "pickup_reaction") == 0 && MP_DEFS[MP_PICKUP_REACTION].unit == 0);
    for (int i = 0; i < MP_COUNT; i++) {
        if (i < 17) CHECK(strcmp(MP_DEFS[i].key, host[i]) == 0);
        CHECK(strlen(MP_DEFS[i].nvs) <= 15); /* a flash key is 15 characters at most */
        CHECK(strncmp(MP_DEFS[i].nvs, MP_DEFS[i].key, 15) == 0 && strlen(MP_DEFS[i].nvs) == (strlen(MP_DEFS[i].key) < 15 ? strlen(MP_DEFS[i].key) : 15)); /* the first 15 characters: the rule the other readers of the store share */
        for (int j = 0; j < i; j++) {
            CHECK(strcmp(MP_DEFS[i].nvs, MP_DEFS[j].nvs) != 0);
        }
        CHECK(MP_DEFS[i].def >= MP_DEFS[i].lo && MP_DEFS[i].def <= MP_DEFS[i].hi);
    }
    mp_prefs_t p;
    mp_defaults(&p);
    CHECK(p.v[MP_FX_CRT] == 0 && p.v[MP_FX_NIGHT_DIM] == 0 && p.v[MP_FX_GLOW] == 0 && p.v[MP_SPEECH_BUBBLE] == 0); /* risky items off */
    CHECK(p.v[MP_THINKING_DOTS] == 1 && p.v[MP_LISTEN_FACE] == 1 && p.v[MP_LISTEN_SOUND] == 1 && p.v[MP_LISTEN_LIGHT] == 2);
    CHECK(p.v[MP_LISTEN_LIGHT_COLOUR] == 0x40C0FF && p.v[MP_FILLER_WAIT_S] == 40 && p.v[MP_FILLER_MODE] == 1);
    CHECK(p.set == 0);
}

static void test_captions_mode(void)
{
    mp_prefs_t p;
    mp_defaults(&p);
    /* nothing chosen: the Stock style keeps its words (its bubble became the subtitles), the others show them when the face's
     * captions flag is on */
    CHECK(mp_captions_mode(&p, 0, 0) == 0 && mp_captions_mode(&p, 1, 0) == 1 && mp_captions_mode(&p, 0, 1) == 1 && mp_captions_mode(&p, 1, 1) == 1);
    char err[200] = "";
    uint32_t ch = 0;
    /* the older speech bubble choice still counts: on means subtitles, off means the Stock style no longer forces them */
    CHECK(mp_apply_json(&p, "{\"speech_bubble\":true}", err, sizeof err, &ch) == 0 && mp_captions_mode(&p, 0, 0) == 1);
    CHECK(mp_apply_json(&p, "{\"speech_bubble\":false}", err, sizeof err, &ch) == 0 && mp_captions_mode(&p, 0, 1) == 0 && mp_captions_mode(&p, 1, 1) == 1);
    /* the new setting wins over every older one */
    CHECK(mp_apply_json(&p, "{\"captions_mode\":\"banner\"}", err, sizeof err, &ch) == 0 && mp_captions_mode(&p, 0, 1) == 2 && mp_captions_mode(&p, 0, 0) == 2);
    CHECK(mp_apply_json(&p, "{\"captions_mode\":\"off\"}", err, sizeof err, &ch) == 0 && mp_captions_mode(&p, 1, 1) == 0);
    CHECK(mp_apply_json(&p, "{\"captions_mode\":\"subtitles\",\"top_bar\":\"always\"}", err, sizeof err, &ch) == 0 && mp_captions_mode(&p, 0, 0) == 1 && p.v[MP_TOP_BAR] == 1);
    CHECK(mp_apply_json(&p, "{\"captions_mode\":\"bubble\"}", err, sizeof err, &ch) == 1 && p.v[MP_CAPTIONS_MODE] == 1); /* the bubble is gone: a wrong name changes nothing */
    CHECK(strcmp(mp_enum_name(MP_TOP_BAR, 0), "hidden") == 0 && mp_enum_value(MP_TOP_BAR, "always") == 1);
    CHECK(strcmp(mp_enum_name(MP_CAPTIONS_MODE, 1), "subtitles") == 0 && strcmp(mp_enum_name(MP_CAPTIONS_MODE, 2), "banner") == 0);
}

static void test_apply(void)
{
    mp_prefs_t p;
    mp_defaults(&p);
    char err[200] = "";
    uint32_t ch = 0;
    CHECK(mp_apply_json(&p, "{\"fx_crt\":true,\"fx_colour_mode\":\"mono\",\"filler_wait_s\":0.75,\"listen_light_colour\":\"#AABBCC\"}", err, sizeof err, &ch) == 0);
    CHECK(p.v[MP_FX_CRT] == 1 && p.v[MP_FX_COLOUR_MODE] == MP_CM_MONO && p.v[MP_FILLER_WAIT_S] == 75 && p.v[MP_LISTEN_LIGHT_COLOUR] == 0xAABBCC);
    CHECK(ch == ((1u << MP_FX_CRT) | (1u << MP_FX_COLOUR_MODE) | (1u << MP_FILLER_WAIT_S) | (1u << MP_LISTEN_LIGHT_COLOUR)));
    CHECK((p.set & (1u << MP_FX_CRT)) != 0 && (p.set & (1u << MP_FX_GLOW)) == 0);
    /* the same again changes nothing */
    CHECK(mp_apply_json(&p, "{\"fx_crt\":true}", err, sizeof err, &ch) == 0 && ch == 0);
    /* sending a default for the first time marks it chosen */
    CHECK(mp_apply_json(&p, "{\"fx_glow\":false}", err, sizeof err, &ch) == 0 && ch == (1u << MP_FX_GLOW) && (p.set & (1u << MP_FX_GLOW)));
    /* all or nothing: one bad field leaves every field alone */
    mp_prefs_t before = p;
    CHECK(mp_apply_json(&p, "{\"fx_night_dim\":true,\"fx_colour_mode\":\"purple\"}", err, sizeof err, &ch) == 1);
    CHECK(memcmp(&before, &p, sizeof p) == 0);
    CHECK(strstr(err, "fx colour mode must be one of normal, mono") != NULL);
    CHECK(mp_apply_json(&p, "{\"fx_crt\":1}", err, sizeof err, &ch) == 1 && strstr(err, "on or off") != NULL);
    CHECK(mp_apply_json(&p, "{\"filler_wait_s\":3}", err, sizeof err, &ch) == 1 && strstr(err, "0.20 to 1.50") != NULL);
    CHECK(mp_apply_json(&p, "{\"filler_wait_s\":0.1}", err, sizeof err, &ch) == 1);
    CHECK(mp_apply_json(&p, "{\"filler_wait_s\":\"0.5\"}", err, sizeof err, &ch) == 1);
    CHECK(mp_apply_json(&p, "{\"listen_light_colour\":\"red\"}", err, sizeof err, &ch) == 1 && strstr(err, "#40c0ff") != NULL);
    CHECK(mp_apply_json(&p, "{\"listen_light_colour\":\"#12345\"}", err, sizeof err, &ch) == 1);
    CHECK(mp_apply_json(&p, "[1]", err, sizeof err, &ch) == 1);
    CHECK(mp_apply_json(&p, "{\"fx_crt\":", err, sizeof err, &ch) == 1);
    CHECK(memcmp(&before, &p, sizeof p) == 0);
    /* unknown keys are skipped, known ones in the same object still apply */
    CHECK(mp_apply_json(&p, "{ \"from_the_future\" : \"x\", \"thinking_dots\" : false }", err, sizeof err, &ch) == 0 && p.v[MP_THINKING_DOTS] == 0);
    CHECK(p.v[MP_STATUS_ICONS] == 0 && strcmp(MP_DEFS[MP_STATUS_ICONS].key, "status_icons") == 0 && MP_DEFS[MP_STATUS_ICONS].unit == 1);  /* off by default */
    CHECK(mp_apply_json(&p, "{\"status_icons\":true}", err, sizeof err, &ch) == 0 && p.v[MP_STATUS_ICONS] == 1);
    CHECK(mp_apply_json(&p, "{\"status_icons\":false}", err, sizeof err, &ch) == 0 && p.v[MP_STATUS_ICONS] == 0);
    CHECK(mp_apply_json(&p, "{\"pickup_reaction\":\"face_sound\"}", err, sizeof err, &ch) == 0 && p.v[MP_PICKUP_REACTION] == 2);
    CHECK(mp_apply_json(&p, "{\"pickup_reaction\":\"loud\"}", err, sizeof err, &ch) == 1);
    /* the other colour names */
    CHECK(mp_apply_json(&p, "{\"fx_colour_mode\":\"monotone\"}", err, sizeof err, &ch) == 0 && p.v[MP_FX_COLOUR_MODE] == MP_CM_MONO);
    CHECK(mp_apply_json(&p, "{\"fx_colour_mode\":\"full\"}", err, sizeof err, &ch) == 0 && p.v[MP_FX_COLOUR_MODE] == MP_CM_NORMAL);
    const char* ok[] = {"normal", "mono", "warm", "cool", "duotone", "amber", "green"};
    for (int i = 0; i < 7; i++) {
        char j[64];
        snprintf(j, sizeof j, "{\"fx_colour_mode\":\"%s\"}", ok[i]);
        CHECK(mp_apply_json(&p, j, err, sizeof err, &ch) == 0 && p.v[MP_FX_COLOUR_MODE] == i);
    }
    /* the exact host payload shape (sorted keys, compact) */
    CHECK(mp_apply_json(&p, "{\"fx_colour_mode\":\"normal\",\"fx_crt\":false,\"fx_glow\":false,\"fx_night_dim\":false,\"listen_face\":true,"
                            "\"listen_light\":\"normal\",\"listen_light_colour\":\"#40c0ff\",\"listen_sound\":\"chime\",\"speech_bubble\":false,"
                            "\"thinking_dots\":true}", err, sizeof err, &ch) == 0);
    CHECK(p.v[MP_FX_CRT] == 0 && p.v[MP_LISTEN_SOUND] == 1);
}

static void test_bubble_rule(void)
{
    mp_prefs_t p;
    mp_defaults(&p);
    CHECK(mp_bubble_on(&p, 0) == 0);
    CHECK(mp_bubble_on(&p, 1) == 1); /* Stock, never chosen: on */
    char err[100];
    CHECK(mp_apply_json(&p, "{\"speech_bubble\":false}", err, sizeof err, NULL) == 0);
    CHECK(mp_bubble_on(&p, 1) == 0); /* a person chose off: off even on Stock */
    CHECK(mp_apply_json(&p, "{\"speech_bubble\":true}", err, sizeof err, NULL) == 0);
    CHECK(mp_bubble_on(&p, 0) == 1);
}

static void test_json_out(void)
{
    mp_prefs_t p;
    mp_defaults(&p);
    char out[1200], err[100];
    CHECK(mp_apply_json(&p, "{\"fx_colour_mode\":\"amber\",\"filler_wait_s\":0.4}", err, sizeof err, NULL) == 0);
    const size_t n = mp_to_json(&p, out, sizeof out);
    CHECK(n > 0 && n == strlen(out));
    CHECK(strstr(out, "\"ok\":true") != NULL);
    CHECK(strstr(out, "\"fx_colour_mode\":\"amber\"") != NULL);
    CHECK(strstr(out, "\"filler_wait_s\":0.40") != NULL);
    CHECK(strstr(out, "\"listen_light_colour\":\"#40c0ff\"") != NULL);
    CHECK(strstr(out, "\"chosen\":[\"filler_wait_s\",\"fx_colour_mode\"]") != NULL);
    CHECK(strstr(out, "\"unit_keys\":[\"listen_sound\"") != NULL);
    CHECK(mp_to_json(&p, out, 50) == 0); /* too small: refused, not cut */
    /* what the unit writes can be read back by the same parser (the host sends this shape) */
    mp_prefs_t q;
    mp_defaults(&q);
    CHECK(mp_to_json(&p, out, sizeof out) > 0);
    const char* v = strstr(out, "\"values\":");
    CHECK(v != NULL);
    char body[1000];
    snprintf(body, sizeof body, "%s", v + 9);
    char* end = strstr(body, "},\"chosen\"");
    CHECK(end != NULL);
    end[1] = '\0';
    CHECK(mp_apply_json(&q, body, err, sizeof err, NULL) == 0);
    CHECK(memcmp(q.v, p.v, sizeof p.v) == 0);
}

int main(void)
{
    test_table();
    test_captions_mode();
    test_apply();
    test_bubble_rule();
    test_json_out();
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("prefs_core_test: all passed\n");
    return 0;
}
