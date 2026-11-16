/* Host test for the music mood faces (patch V03): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_music_mood_core.h"

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
    /* The two faces are real faces of the unit's avatar. */
    CHECK(MMM_FACE_COUNT == 2);
    CHECK(strcmp(MMM_FACES[0], "happy") == 0);
    CHECK(strcmp(MMM_FACES[1], "laughing") == 0);

    /* A calm song or no tempo keeps the plain happy face, whatever the time. */
    for (uint32_t t = 0; t < 200; t += 7) {
        CHECK(mmm_face(0, 900, t) == 0);
        CHECK(mmm_face(70, 3000, t) == 0);
        CHECK(mmm_face(94, 3000, t) == 0);
    }
    /* A fast loud song laughs from the first second. */
    CHECK(mmm_face(125, 1500, 0) == 1);
    CHECK(mmm_face(180, 8000, 33) == 1);
    /* Fast but quiet is a middling song. */
    CHECK(mmm_face(150, 800, 0) == 0);
    /* A middling song swaps every 12 s: happy, laughing, happy ... */
    CHECK(mmm_face(100, 900, 0) == 0);
    CHECK(mmm_face(100, 900, 11) == 0);
    CHECK(mmm_face(100, 900, 12) == 1);
    CHECK(mmm_face(100, 900, 23) == 1);
    CHECK(mmm_face(100, 900, 24) == 0);
    /* Always a valid index. */
    for (int bpm = 0; bpm < 250; bpm += 5) {
        for (int lv = 0; lv < 20000; lv += 500) {
            for (uint32_t t = 0; t < 120; t += 5) {
                const int f = mmm_face(bpm, lv, t);
                CHECK(f >= 0 && f < MMM_FACE_COUNT);
            }
        }
    }
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
