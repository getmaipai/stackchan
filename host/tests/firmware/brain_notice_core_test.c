/* Host test of maipai_brain_notice_core.h (patch UX20): the "Hosted link removed" notice in six languages, and where its button sits. Placement: host-side test. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include "maipai_brain_notice_core.h"

#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)

int main(void)
{
    for (int l = 0; l < MBN_LANGS; l++) {
        CHECK(strlen(mbn_title(l)) > 8 && strlen(mbn_removed(l)) > 20 && strlen(mbn_now(l)) > 20 && strlen(mbn_console(l)) > 40 && strcmp(mbn_ok(l), "OK") == 0);
        CHECK(strstr(mbn_removed(l), "M5Stack/Xiaozhi") != NULL);                  /* every language names what was removed */
        for (int k = 0; k < l; k++) {
            CHECK(strcmp(mbn_title(l), mbn_title(k)) != 0 && strcmp(mbn_now(l), mbn_now(k)) != 0 && strcmp(mbn_console(l), mbn_console(k)) != 0);   /* translated, not copied */
        }
    }
    CHECK(strcmp(mbn_title(-1), mbn_title(0)) == 0 && strcmp(mbn_title(99), mbn_title(0)) == 0);   /* a bad language falls back to English */
    int x, y, w, h;
    mbn_ok_box(&x, &y, &w, &h);
    CHECK(w >= 70 && h >= 56 && x >= 0 && x + w <= MBN_W && y + h + 8 <= MBN_H);   /* a primary target, 8 px from the glass edge */
    CHECK(MBN_TEXT_Y + 6 * 21 + 8 <= y);                                           /* six 16 px lines (three sentences of two lines) end 8 px above the button */
    CHECK(MBN_TEXT_Y >= MBN_TITLE_Y + 28);
    puts("brain_notice_core_test: all passed");
    return 0;
}
