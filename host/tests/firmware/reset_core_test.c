/* Host test for the reset core (patch R01): cc -std=c99 -Wall -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_reset_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    /* nothing is erased before 3 s */
    CHECK(!mrc_hold_complete(1000, 1000));
    CHECK(!mrc_hold_complete(1000, 3999));
    CHECK(mrc_hold_complete(1000, 4000));
    CHECK(mrc_hold_percent(1000, 1000) == 0);
    CHECK(mrc_hold_percent(1000, 2500) == 50);
    CHECK(mrc_hold_percent(1000, 9000) == 100);
    /* a tick counter that wrapped still measures the hold */
    CHECK(mrc_hold_complete(0xFFFFFF00u, 0x00000E00u));
    CHECK(!mrc_hold_complete(0xFFFFFF00u, 0x00000100u));

    /* what survives a reset: only the mark, the head calibration and the radio calibration */
    CHECK(mrc_keep_namespace("mp_reset") && mrc_keep_namespace("servo") && mrc_keep_namespace("phy"));
    CHECK(!mrc_keep_namespace("wifi") && !mrc_keep_namespace("nvs.net80211") && !mrc_keep_namespace("websocket"));
    CHECK(!mrc_keep_namespace("maipai_priv") && !mrc_keep_namespace("mp_timers") && !mrc_keep_namespace(NULL));

    /* both languages say something for every line, and the text is plain ASCII (the screen font has no accents) */
    CHECK(mrc_lang_from_code("es-ES") == MRC_LANG_ES && mrc_lang_from_code("en-US") == MRC_LANG_EN);
    CHECK(mrc_lang_from_code(NULL) == MRC_LANG_EN);
    for (int l = 0; l < 2; l++) {
        for (int s = 0; s < MRC_STR_COUNT; s++) {
            const char* t = mrc_text((mrc_lang_t)l, (mrc_str_t)s);
            CHECK(t != NULL && strlen(t) > 3);
            for (const char* c = t; *c; c++) CHECK((unsigned char)*c < 0x80);
        }
    }
    CHECK(strstr(mrc_text(MRC_LANG_EN, MRC_STR_BODY), "Wi-Fi") && strstr(mrc_text(MRC_LANG_EN, MRC_STR_BODY), "3 seconds"));
    CHECK(strstr(mrc_text(MRC_LANG_ES, MRC_STR_BODY), "3 segundos"));
    CHECK(strcmp(mrc_text(MRC_LANG_EN, MRC_STR_BUTTON), mrc_text(MRC_LANG_ES, MRC_STR_BUTTON)) != 0);
    CHECK(mrc_text(MRC_LANG_EN, MRC_STR_COUNT)[0] == '\0');

    if (failures) {
        printf("%d failed\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
