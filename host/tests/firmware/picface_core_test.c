/* Host test for the picture face core (patch H03): limits, refusals in two languages, slot choice, fade, cache, overlay. */
#include <stdio.h>
#include <string.h>

#include "maipai_picface_core.h"

static int fails;
#define CHECK(c)                                                    \
    do {                                                            \
        if (!(c)) {                                                 \
            printf("FAIL line %d: %s\n", __LINE__, #c);             \
            fails++;                                                \
        }                                                           \
    } while (0)

static void test_names_and_text(void)
{
    CHECK(pf_slot_by_name("neutral") == PF_SLOT_NEUTRAL);
    CHECK(pf_slot_by_name("speaking") == PF_SLOT_SPEAKING);
    CHECK(pf_slot_by_name("Neutral") == -1);
    CHECK(pf_slot_by_name(NULL) == -1);
    CHECK(pf_mode_by_name("overlay") == PF_MODE_OVERLAY);
    CHECK(pf_mode_by_name("film") == -1);
    for (int e = 0; e < PF_ERR_COUNT; e++) {
        const char* en = pf_say((pf_err_t)e, 0);
        const char* es = pf_say((pf_err_t)e, 1);
        CHECK(en != NULL && es != NULL && strlen(en) > 4 && strlen(es) > 4);
        CHECK(strcmp(en, es) != 0);
        CHECK(strcmp(PF_ERR_CODES[e], "") != 0);
        /* plain words: every refusal says what to do (a verb of doing), never a bare code */
        if (e != PF_OK) {
            CHECK(strstr(en, "again") || strstr(en, "first") || strstr(en, "Choose") || strstr(en, "Use") ||
                  strstr(en, "Add") || strstr(en, "Remove") || strstr(en, "Resize") || strstr(en, "Keep") || strstr(en, "Send"));
        }
        for (const char* p = en; *p; p++) CHECK((unsigned char)*p < 128 && *p != '\n');
    }
    CHECK(strstr(pf_say(PF_ERR_TOO_BIG, 1), "imagenes") != NULL);
}

static void test_start(void)
{
    CHECK(pf_start_ok(PF_MODE_PICTURE, 6) == PF_OK);
    CHECK(pf_start_ok(3, 6) == PF_ERR_MODE);
    CHECK(pf_start_ok(-1, 6) == PF_ERR_MODE);
    CHECK(pf_start_ok(PF_MODE_SEQUENCE, 0) == PF_ERR_FPS);
    CHECK(pf_start_ok(PF_MODE_SEQUENCE, 13) == PF_ERR_FPS);
    CHECK(pf_start_ok(PF_MODE_SEQUENCE, 12) == PF_OK);
}

static void test_admit(void)
{
    pf_plan_t p;
    pf_plan_init(&p, PF_MODE_PICTURE, 6);
    CHECK(pf_admit(&p, PF_SLOT_NEUTRAL, 0, 100000, 0) == PF_OK);
    CHECK(pf_admit(&p, 7, 0, 1000, 0) == PF_ERR_SLOT);
    CHECK(pf_admit(&p, -1, 0, 1000, 0) == PF_ERR_SLOT);
    CHECK(pf_admit(&p, PF_SLOT_HAPPY, 1, 1000, 0) == PF_ERR_INDEX); /* picture mode: one per expression */
    CHECK(pf_admit(&p, PF_SLOT_HAPPY, 0, 0, 0) == PF_ERR_FRAME_SIZE);
    CHECK(pf_admit(&p, PF_SLOT_HAPPY, 0, PF_FRAME_BYTES + 1, 0) == PF_ERR_FRAME_SIZE);
    CHECK(pf_admit(&p, PF_SLOT_HAPPY, 0, PF_FRAME_BYTES, 0) == PF_OK);

    /* the byte budget: seven raw pictures do not fit, six do not either, but a replaced frame counts once */
    pf_plan_init(&p, PF_MODE_PICTURE, 6);
    for (int s = 0; s < 6; s++) {
        CHECK(pf_admit(&p, s, 0, PF_FRAME_BYTES, 0) == PF_OK);
        p.bytes += PF_FRAME_BYTES;
        p.frames[s] = 1;
    }
    CHECK(p.bytes == 6u * PF_FRAME_BYTES);
    CHECK(pf_admit(&p, PF_SLOT_SPEAKING, 0, PF_FRAME_BYTES, 0) == PF_ERR_TOO_BIG);
    CHECK(pf_admit(&p, PF_SLOT_SPEAKING, 0, PF_MAX_STORE_BYTES - p.bytes, 0) == PF_OK);
    CHECK(pf_admit(&p, PF_SLOT_SPEAKING, 0, PF_MAX_STORE_BYTES - p.bytes + 1, 0) == PF_ERR_TOO_BIG);
    CHECK(pf_admit(&p, PF_SLOT_HAPPY, 0, PF_FRAME_BYTES, PF_FRAME_BYTES) == PF_OK); /* a replacement */

    /* sequence: six per expression, fourteen in all */
    pf_plan_init(&p, PF_MODE_SEQUENCE, 8);
    CHECK(pf_admit(&p, PF_SLOT_NEUTRAL, 5, 1000, 0) == PF_OK);
    CHECK(pf_admit(&p, PF_SLOT_NEUTRAL, 6, 1000, 0) == PF_ERR_INDEX);
    p.frames[PF_SLOT_NEUTRAL] = 6;
    p.frames[PF_SLOT_HAPPY]   = 6;
    p.total_frames            = 12;
    CHECK(pf_admit(&p, PF_SLOT_SAD, 1, 1000, 0) == PF_OK);  /* 12 + 2 = 14 */
    CHECK(pf_admit(&p, PF_SLOT_SAD, 2, 1000, 0) == PF_ERR_TOO_MANY_FRAMES); /* 12 + 3 = 15 */
    CHECK(pf_admit(&p, PF_SLOT_HAPPY, 3, 1000, 0) == PF_OK); /* already there: no new frame */
}

static void test_complete(void)
{
    pf_plan_t p;
    pf_plan_init(&p, PF_MODE_PICTURE, 6);
    CHECK(pf_complete(&p) == PF_ERR_NO_NEUTRAL);
    p.frames[PF_SLOT_HAPPY] = 1;
    p.received[PF_SLOT_HAPPY][0] = 1;
    CHECK(pf_complete(&p) == PF_ERR_NO_NEUTRAL);
    p.frames[PF_SLOT_NEUTRAL] = 1;
    CHECK(pf_complete(&p) == PF_ERR_MISSING);
    p.received[PF_SLOT_NEUTRAL][0] = 1;
    CHECK(pf_complete(&p) == PF_OK);
    p.frames[PF_SLOT_SAD] = 2;
    p.received[PF_SLOT_SAD][0] = 1;
    CHECK(pf_complete(&p) == PF_ERR_MISSING);
}

static void test_slots(void)
{
    const unsigned all  = (1u << PF_SLOTS) - 1;
    const unsigned some = (1u << PF_SLOT_NEUTRAL) | (1u << PF_SLOT_HAPPY);
    CHECK(pf_slot_for_emotion(0) == PF_SLOT_NEUTRAL);
    CHECK(pf_slot_for_emotion(1) == PF_SLOT_HAPPY);
    CHECK(pf_slot_for_emotion(2) == PF_SLOT_ANGRY);
    CHECK(pf_slot_for_emotion(3) == PF_SLOT_SAD);
    CHECK(pf_slot_for_emotion(4) == PF_SLOT_DOUBT);
    CHECK(pf_slot_for_emotion(5) == PF_SLOT_SLEEPY);
    CHECK(pf_slot_for_emotion(99) == PF_SLOT_NEUTRAL);
    CHECK(pf_pick_slot(1, 0, all) == PF_SLOT_HAPPY);
    CHECK(pf_pick_slot(1, 1, all) == PF_SLOT_SPEAKING);          /* speaking wins */
    CHECK(pf_pick_slot(1, 1, some) == PF_SLOT_HAPPY);            /* no speaking picture: the emotion */
    CHECK(pf_pick_slot(3, 0, some) == PF_SLOT_NEUTRAL);          /* no sad picture: neutral */
    CHECK(pf_pick_slot(3, 1, some) == PF_SLOT_NEUTRAL);
}

static void test_seq_and_fade(void)
{
    CHECK(pf_seq_index(0, 6, 4) == 0);
    CHECK(pf_seq_index(166, 6, 4) == 0);
    CHECK(pf_seq_index(167, 6, 4) == 1);
    CHECK(pf_seq_index(1000, 6, 4) == 2);   /* 6 frames elapsed, mod 4 */
    CHECK(pf_seq_index(5000, 6, 1) == 0);
    CHECK(pf_seq_index(5000, 6, 0) == 0);
    int last = -1;
    for (uint32_t t = 0; t <= PF_FADE_MS + 100; t += 11) {
        const int o = pf_fade_opa(t);
        CHECK(o >= last && o >= 0 && o <= 255);
        last = o;
    }
    CHECK(pf_fade_opa(0) == 0);
    CHECK(pf_fade_opa(PF_FADE_MS) == 255);
    CHECK(pf_fade_opa(PF_FADE_MS / 2) > 100 && pf_fade_opa(PF_FADE_MS / 2) < 155); /* eased through the middle */
    CHECK(pf_fade_opa(PF_FADE_MS / 8) < 255 / 8 + 10);                              /* slow start */
}

static void test_cache(void)
{
    pf_cache_t c;
    pf_cache_init(&c);
    CHECK(pf_cache_find(&c, 5) == -1);
    int a = pf_cache_victim(&c, 0);
    CHECK(a == 0);
    pf_cache_put(&c, a, pf_key(1, 0));
    int b = pf_cache_victim(&c, 1u << a);
    CHECK(b == 1);
    pf_cache_put(&c, b, pf_key(2, 0));
    int d = pf_cache_victim(&c, 0);
    CHECK(d == 2);
    pf_cache_put(&c, d, pf_key(3, 0));
    /* all three full: the least recently used goes, a hit refreshes */
    CHECK(pf_cache_find(&c, pf_key(1, 0)) == 0); /* slot 1 is now the most recent */
    CHECK(pf_cache_victim(&c, 0) == 1);          /* slot 2 (position 1) is the oldest */
    CHECK(pf_cache_victim(&c, 1u << 1) == 2);    /* position 1 is on screen: the next oldest */
    CHECK(pf_cache_victim(&c, 7u) == -1);        /* everything pinned */
    /* never more than three entries */
    CHECK(PF_CACHE_SLOTS == 3);
}

static void test_overlay(void)
{
    pf_overlay_t o = pf_overlay_default();
    CHECK(pf_overlay_ok(&o));
    o.eye_w = 3;
    CHECK(!pf_overlay_ok(&o));
    o = pf_overlay_default();
    o.lx = PF_W;
    CHECK(!pf_overlay_ok(&o));
    o = pf_overlay_default();
    o.my = -1;
    CHECK(!pf_overlay_ok(&o));
    o = pf_overlay_default();
    o.mouth_h = 121;
    CHECK(!pf_overlay_ok(&o));
    /* eyes: open at 100, a thin line in a blink and when shut */
    CHECK(pf_eye_height(36, 100) == 36);
    CHECK(pf_eye_height(36, 25) <= 10);
    CHECK(pf_eye_height(36, 25) >= 3);
    CHECK(pf_eye_height(36, 0) == 3);
    CHECK(pf_eye_height(36, 70) < pf_eye_height(36, 100));
    int last = 0;
    for (int w = 0; w <= 100; w += 5) {
        const int h = pf_mouth_height(40, w);
        CHECK(h >= last);
        last = h;
    }
    CHECK(pf_mouth_height(40, 0) == 3);
    CHECK(pf_mouth_height(40, 100) == 40);
    CHECK(pf_mouth_width(70, 100) < pf_mouth_width(70, 0));
}

static void test_crc(void)
{
    const uint8_t text[] = "123456789";
    CHECK(pf_crc32(0, text, 9) == 0xCBF43926u); /* the standard check value */
    uint32_t c = pf_crc32(0, text, 4);
    c          = pf_crc32(c, text + 4, 5);
    CHECK(c == 0xCBF43926u); /* in pieces gives the same answer */
}

static void test_budget_numbers(void)
{
    /* the PSRAM bill of a full pack: stored bytes plus three decoded frames stays under 1.5 MB */
    CHECK(PF_MAX_STORE_BYTES + PF_CACHE_SLOTS * PF_FRAME_BYTES < 1500000u);
    CHECK(PF_FRAME_BYTES == 153600);
}

int main(void)
{
    test_names_and_text();
    test_start();
    test_admit();
    test_complete();
    test_slots();
    test_seq_and_fade();
    test_cache();
    test_overlay();
    test_crc();
    test_budget_numbers();
    if (fails) {
        printf("%d failed\n", fails);
        return 1;
    }
    printf("picface core: all passed\n");
    return 0;
}
