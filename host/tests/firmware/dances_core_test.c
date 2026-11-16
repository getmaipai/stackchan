/* Host test for the named dances (patch V04): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_dances_core.h"

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
    static const char* const expect[MDN_COUNT] = {"sway", "nod_yes", "shake_no", "wiggle", "bow", "groove"};
    CHECK(MDN_COUNT == 6);
    for (int i = 0; i < MDN_COUNT; i++) {
        const mdn_dance_t* d = &MDN_DANCES[i];
        CHECK(strcmp(d->name, expect[i]) == 0);
        CHECK(mdn_check(d) == NULL);       /* every shipped row is inside the limits */
        CHECK(mdn_find(d->name) == d);
        /* the rows are centred at both ends and never stand still: some step moves the head */
        int moves = 0;
        for (int k = 0; k < d->count; k++) {
            moves += (d->step[k].yaw != 0 || d->step[k].pitch != 0);
        }
        CHECK(moves >= 1);
        CHECK(d->step[d->count - 1].pitch > -100 && d->step[d->count - 1].pitch < 100);
        for (int k = i + 1; k < MDN_COUNT; k++) {
            CHECK(strcmp(d->name, MDN_DANCES[k].name) != 0); /* no duplicate names */
        }
    }
    /* The four built-in names are not taken by a data row. */
    CHECK(mdn_find("happy") == NULL && mdn_find("robot") == NULL && mdn_find("panic") == NULL &&
          mdn_find("look_around") == NULL);
    CHECK(mdn_find("") == NULL && mdn_find(NULL) == NULL && mdn_find("Sway") == NULL);

    /* The checker refuses every kind of bad row. */
    mdn_dance_t bad = MDN_DANCES[1];
    CHECK(mdn_check(&bad) == NULL);
    bad.step[1].yaw = MDN_YAW_MAX + 1;
    CHECK(mdn_check(&bad) != NULL && strcmp(mdn_check(&bad), "yaw") == 0);
    bad = MDN_DANCES[1];
    bad.step[1].pitch = MDN_PITCH_MIN - 1;
    CHECK(strcmp(mdn_check(&bad), "pitch") == 0);
    bad = MDN_DANCES[1];
    bad.step[1].speed = MDN_SPEED_MAX + 1;
    CHECK(strcmp(mdn_check(&bad), "speed") == 0);
    bad = MDN_DANCES[1];
    bad.step[1].speed = 0;
    CHECK(strcmp(mdn_check(&bad), "speed") == 0);
    bad = MDN_DANCES[1];
    bad.step[1].ms = 5;
    CHECK(strcmp(mdn_check(&bad), "time") == 0);
    bad = MDN_DANCES[1];
    bad.step[1].eye_w = 101;
    CHECK(strcmp(mdn_check(&bad), "weight") == 0);
    bad = MDN_DANCES[1];
    bad.count = 1;
    CHECK(strcmp(mdn_check(&bad), "steps") == 0);
    bad = MDN_DANCES[1];
    bad.step[5].yaw = 200; /* ends off centre */
    CHECK(strcmp(mdn_check(&bad), "centre") == 0);
    bad = MDN_DANCES[3];
    for (int k = 0; k < bad.count; k++) {
        bad.step[k].ms = 1500;
    }
    CHECK(strcmp(mdn_check(&bad), "length") == 0);
    CHECK(mdn_check(NULL) != NULL);

    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
