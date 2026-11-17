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
    if (failures == 0) {
        printf("status_core_test: all passed\n");
        return 0;
    }
    printf("%d failure(s)\n", failures);
    return 1;
}
