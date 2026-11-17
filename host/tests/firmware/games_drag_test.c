/* Host test for the game drag bar (patch GM02) and the widened safe area (patches GM01 and GM03). */
#include <stdio.h>
#include "maipai_games_core.h"
#include "maipai_games_input_core.h"
#include "maipai_games_sfx_core.h"

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
    /* the safe area runs to y 224 and the bottom edge starts there */
    CHECK(MG_SAFE_TOP == 28 && MG_SAFE_BOTTOM == 224 && MG_EDGE_B == 224 && 240 - MG_SAFE_BOTTOM == 16);
    /* the strip is the top 16 px of the content zone; a press above y 36 is the bar's, y 36 and below is the game's */
    CHECK(MG_DRAG_TOP == 28 && MG_DRAG_BOTTOM == 44 && MG_DRAG_BOTTOM - MG_DRAG_TOP == 16);
    CHECK(!mg_drag_press_dead(27) && mg_drag_press_dead(28) && mg_drag_press_dead(35) && !mg_drag_press_dead(36) && !mg_drag_press_dead(100));
    /* the grabber is inside the strip and the same size as the sheet's (48 by 5) */
    CHECK(MG_DRAG_GRAB_W == 48 && MG_DRAG_GRAB_H == 5 && MG_DRAG_GRAB_Y >= MG_DRAG_TOP && MG_DRAG_GRAB_Y + MG_DRAG_GRAB_H <= MG_DRAG_DEAD_Y);
    CHECK(MG_DRAG_GRAB_X * 2 + MG_DRAG_GRAB_W == 320);
    /* a swipe down that begins on the strip dismisses */
    CHECK(mg_drag_dismiss(160, 30, 160, 90, 300));
    CHECK(mg_drag_dismiss(160, 43, 170, 80, 400));
    CHECK(mg_drag_dismiss(160, 28, 160, 52, 200) && !mg_drag_dismiss(160, 28, 160, 51, 200)); /* at least 24 px */
    /* a swipe that begins anywhere else never does: in-game swipes, taps and the rest of the screen are the game's */
    CHECK(!mg_drag_dismiss(160, 44, 160, 200, 300));
    CHECK(!mg_drag_dismiss(160, 27, 160, 200, 300));
    CHECK(!mg_drag_dismiss(160, 120, 160, 200, 300));
    CHECK(!mg_drag_dismiss(40, 30, 200, 60, 300)); /* sideways: Do It's swipe left or right that began high */
    CHECK(!mg_drag_dismiss(160, 30, 160, 20, 300) && !mg_drag_dismiss(160, 30, 160, 30, 300)); /* up and still */
    CHECK(!mg_drag_dismiss(160, 30, 160, 90, 1501)); /* a slow drag is not a swipe */
    /* a tile may begin at y 28 and still gets every tap from y 36 down */
    CHECK(!mg_drag_press_dead(36) && 36 >= MG_DRAG_DEAD_Y);

    /* every synthesized effect peaks at the chime level and none clips */
    static int16_t buf[MGS_SFX_MAX_SAMPLES];
    int clips = 0;
    for (int c = 0; c < MGS_CLIPS; c++) {
        const size_t n = mgs_render(c, buf, MGS_SFX_MAX_SAMPLES);
        if (n == 0) continue;
        clips++;
        int peak = 0;
        double sum = 0;
        for (size_t i = 0; i < n; i++) {
            const int a = buf[i] < 0 ? -buf[i] : buf[i];
            if (a > peak) peak = a;
            sum += (double)buf[i] * buf[i];
        }
        CHECK(peak >= MGS_SFX_PEAK - 2 && peak <= MGS_SFX_PEAK && peak < 32767);
        CHECK(sum > 0);
        CHECK(MGS_SFX_PEAK >= 18000 && MGS_SFX_PEAK <= 25000); /* the chimes' own peaks */
    }
    CHECK(clips >= 10);
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("games drag ok\n");
    return 0;
}
