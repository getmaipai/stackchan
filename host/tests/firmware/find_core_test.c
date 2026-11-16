/* Host test for the find-my-robot sound rule (patch Y02): the full sounds core with the find bypass. */
#include <stdio.h>
#include "maipai_sounds_core.h"

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
    ms_policy_t p = {0};
    p.enabled = 0; /* sounds off */
    p.muted   = 1; /* and muted */
    CHECK(ms_decide(&p, MS_SND_POPUP, 0, 1, 0) == MS_MUTED);            /* a normal sound is silent */
    CHECK(ms_decide(&p, MS_SND_POPUP, 0, 1, 1) == MS_MUTED);            /* the self-test never beats the mute */
    CHECK(ms_decide(&p, MS_SND_EXCLAMATION, 0, 1, MS_BYPASS_FIND) == MS_OK); /* find sounds through mute, off and night */
    CHECK(ms_decide(&p, -1, 0, 0, MS_BYPASS_FIND) == MS_NO_SUCH_SOUND);
    if (failures == 0) {
        printf("find core: ok\n");
    }
    return failures != 0;
}
