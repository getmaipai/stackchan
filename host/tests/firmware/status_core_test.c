/* Host test for the banner status icons (patch UI04): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> status_core_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_banner_core.h"
#include "maipai_status_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

int main(void)
{
    /* words and icons exist in both languages and fit the banner's text room */
    for (int k = 0; k < MST_COUNT; k++) {
        CHECK(strlen(mst_text(k, 0)) > 0 && strlen(mst_text(k, 1)) > 0 && strlen(mst_text(k, 0)) < 16);
        CHECK(mst_icon(k) == MB_ICON_CHECK || mst_icon(k) == MB_ICON_SPEECH);
        CHECK(mst_hold_ms(k) > 0 && mst_hold_ms(k) <= MB_MAX_HOLD_MS + 25000u);
    }
    CHECK(MST_ICON[MST_WAKE] == MB_ICON_CHECK && MST_ICON[MST_LISTEN] == MB_ICON_SPEECH);
    CHECK(strcmp(mst_text(MST_LISTEN, 0), "Listening") == 0 && strcmp(mst_text(MST_THINK, 1), "Pensando") == 0);
    CHECK(mst_text(99, 0)[0] == '\0' && mst_icon(-1) == 0);

    /* the mic glyph: a listen shorter than the old 2 s poll is still seen, for MST_MIC_HOLD_MS after it ends */
    const uint32_t t0 = 1000u;
    CHECK(mst_mic_shown(1, 0, t0, 0));
    const uint32_t until = mst_mic_hold_until(t0);
    CHECK(until == t0 + MST_MIC_HOLD_MS);
    CHECK(mst_mic_shown(0, until, t0 + 1, 0) && mst_mic_shown(0, until, until - 1, 0));
    CHECK(!mst_mic_shown(0, until, until, 0) && !mst_mic_shown(0, until, until + 5000u, 0) && !mst_mic_shown(0, 0, t0, 0));
    CHECK(mst_mic_shown(0, 0, t0, 1));  /* the device-state poll still counts */
    /* a clock that wraps does not break the hold */
    const uint32_t late = 0xFFFFFF00u;
    CHECK(mst_mic_shown(0, mst_mic_hold_until(late), late + 100u, 0));

    /* the regression for "the icon sometimes does not show": a status message has the privacy priority and its own tag, so it
     * is not queued behind a steady notice (the link message), and a short state still shows for the row's minimum time */
    mb_t b;
    mb_init(&b);
    CHECK(mb_post(&b, 100, "Offline", MB_ICON_WIFI_OFF, MB_PRIO_NOTICE, MB_TAG_LINK, 0)); /* steady notice on the row */
    CHECK(mb_post(&b, 120, "Listening", MB_ICON_SPEECH, MB_PRIO_PRIVACY, MB_TAG_STATUS, mst_hold_ms(MST_LISTEN)));
    mb_tick(&b, 120 + MB_MIN_MS);
    const char* text;
    int icon, prio;
    CHECK(mb_content(&b, &text, &icon, &prio) != 0 && strcmp(text, "Listening") == 0 && icon == MB_ICON_SPEECH);
    /* a second status replaces the first in place (no queue growth), the state change clears it once its minimum time is up */
    CHECK(mb_post(&b, 120 + MB_MIN_MS + 10, "Thinking", MB_ICON_SPEECH, MB_PRIO_PRIVACY, MB_TAG_STATUS, mst_hold_ms(MST_THINK)));
    CHECK(b.nq == 1 && strcmp(b.cur.text, "Thinking") == 0);  /* only the steady link notice waits */
    mb_clear_tag(&b, 120 + MB_MIN_MS + 20, MB_TAG_STATUS);
    mb_tick(&b, 120 + 3 * MB_MIN_MS + 100);
    CHECK(mb_content(&b, &text, &icon, &prio) != 0 && strcmp(text, "Offline") == 0);  /* the notice comes back */
    /* patch NX05: the face-seen glyph. The hold is 3 s by default, at most 10 s, and a report closer than half a second to the last is ignored */
    CHECK(mst_face_hold_ms(0) == 3000u && mst_face_hold_ms(-4) == 3000u && mst_face_hold_ms(1) == 1000u && mst_face_hold_ms(10) == 10000u && mst_face_hold_ms(99) == 10000u);
    CHECK(mst_face_due(0, 5000u) && !mst_face_due(5000u, 5000u) && !mst_face_due(5000u, 5000u + MST_FACE_RATE_MS - 1u) && mst_face_due(5000u, 5000u + MST_FACE_RATE_MS));
    CHECK(mst_face_due(0xFFFFFF00u, 0xFFFFFF00u + MST_FACE_RATE_MS) && !mst_face_due(0xFFFFFF00u, 0xFFFFFF00u + 10u));  /* a clock that wraps */
    /* the glyph sits next to the mic glyph and is its own bit: the camera cue, the remote chip and the battery and Wi-Fi glyphs keep theirs */
    CHECK(MB_FLAG_FACE == MB_FLAG_MIC + 1 && MB_FLAG_COUNT == 6 && !(MB_FLAG_ALWAYS_ON & (1u << MB_FLAG_FACE)));
    mb_t f;
    mb_init(&f);
    mb_flag(&f, MB_FLAG_CAMERA, 1, 1000, 0);
    mb_session(&f, 1, "remote");
    mb_flag(&f, MB_FLAG_MIC, 1, 1000, 0);
    mb_flag(&f, MB_FLAG_FACE, 1, 1000, mst_face_hold_ms(0));
    const uint32_t all = (1u << MB_FLAG_MIC) | (1u << MB_FLAG_FACE) | (1u << MB_FLAG_CAMERA) | (1u << MB_FLAG_REMOTE);
    CHECK((mb_strip_visible(&f) & all) == all && mb_strip_w(all) == 4 * MB_STRIP_GLYPH_W + 3 * MB_STRIP_GAP);   /* four glyphs side by side, none over another */
    mb_tick(&f, 1000 + 2999);
    CHECK(mb_strip_visible(&f) & (1u << MB_FLAG_FACE));                         /* still there just before 3 s */
    mb_tick(&f, 1000 + 3001);
    CHECK(!(mb_strip_visible(&f) & (1u << MB_FLAG_FACE)));                      /* gone by itself after 3 s ... */
    CHECK((mb_strip_visible(&f) & (1u << MB_FLAG_CAMERA)) && (mb_strip_visible(&f) & (1u << MB_FLAG_REMOTE)) && (mb_strip_visible(&f) & (1u << MB_FLAG_MIC)));   /* ... the others stay */
    mb_flag(&f, MB_FLAG_FACE, 1, 5000, 3000);                                   /* a newer report renews the time */
    mb_flag(&f, MB_FLAG_FACE, 1, 7500, 3000);
    mb_tick(&f, 5000 + 3500);
    CHECK(mb_strip_visible(&f) & (1u << MB_FLAG_FACE));
    if (failures == 0) {
        printf("status_core_test: all passed\n");
        return 0;
    }
    printf("%d failure(s)\n", failures);
    return 1;
}
