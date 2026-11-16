/* Host test for the offline phrase flow (patch V02): the link events and the pick, as maipai_sounds.cc drives them.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with maipai_sounds_core.h> */
#include <stdio.h>
#include <string.h>
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
    ms_link_t l;
    ms_phrases_t ph;
    ms_link_init(&l);
    ms_phrases_init(&ph);

    /* No Wi-Fi: the no_wifi group, a round robin over its four clips. */
    ms_link_down(&l, 0);
    ms_phrase_t p = ms_phrase_pick(&ph, ms_link_state(&l, 1000, 0, 0), 1000, 0, 0, -1);
    CHECK(p.kind == MS_PH_CLIP && p.group == MS_GRP_NO_WIFI && p.variant == 0);
    /* Connecting (Wi-Fi up, down under 10 s). The 10 s gap blocks a second clip: the tone. */
    CHECK(ms_link_state(&l, 5000, 1, 0) == MS_LINK_CONNECTING);
    p = ms_phrase_pick(&ph, MS_LINK_CONNECTING, 5000, 0, 0, -1);
    CHECK(p.kind == MS_PH_TONE);
    /* After 10 s down: no host. */
    CHECK(ms_link_state(&l, 12000, 1, 0) == MS_LINK_NO_HOST);
    p = ms_phrase_pick(&ph, MS_LINK_NO_HOST, 12000, 0, 0, -1);
    CHECK(p.kind == MS_PH_CLIP && p.group == MS_GRP_NO_HOST && p.variant == 0);
    p = ms_phrase_pick(&ph, MS_LINK_NO_HOST, 23000, 0, 0, -1);
    CHECK(p.kind == MS_PH_CLIP && p.group == MS_GRP_NO_HOST && p.variant == 1); /* never the same twice in a row */
    /* Three in any minute (1 s, 12 s, 23 s), then the tone; a minute after the first the limit lifts. */
    p = ms_phrase_pick(&ph, MS_LINK_NO_HOST, 34000, 0, 0, -1);
    CHECK(p.kind == MS_PH_TONE);
    p = ms_phrase_pick(&ph, MS_LINK_NO_HOST, 45000, 0, 0, -1);
    CHECK(p.kind == MS_PH_TONE);
    p = ms_phrase_pick(&ph, MS_LINK_NO_HOST, 62000, 0, 0, -1);
    CHECK(p.kind == MS_PH_CLIP && p.variant == 2);
    /* Refused only after two hello failures in a row; a slow host (counter reset) is not a refusal. */
    ms_link_hello_failed(&l);
    CHECK(ms_link_state(&l, 100000, 1, 0) == MS_LINK_NO_HOST);
    ms_link_hello_failed(&l);
    CHECK(ms_link_state(&l, 100000, 1, 0) == MS_LINK_REFUSED);
    l.hello_fails = 0; /* maipai_sounds.cc does this on MAIPAI_LINK_HELLO_SLOW */
    CHECK(ms_link_state(&l, 100000, 1, 0) == MS_LINK_NO_HOST);
    /* Night: the tone; muted: nothing. */
    ms_phrases_init(&ph);
    p = ms_phrase_pick(&ph, MS_LINK_NO_HOST, 200000, 1, 0, -1);
    CHECK(p.kind == MS_PH_TONE);
    p = ms_phrase_pick(&ph, MS_LINK_NO_HOST, 200000, 0, 1, -1);
    CHECK(p.kind == MS_PH_NONE);
    /* The link is up: no group, nothing to say (the caller then plays the old tone). */
    p = ms_phrase_pick(&ph, MS_LINK_UP, 200000, 0, 0, -1);
    CHECK(p.kind == MS_PH_NONE);
    /* "I'm back": only after an outage of over a minute that sounded the offline tone. */
    ms_link_t l2;
    ms_link_init(&l2);
    ms_link_down(&l2, 0);
    ms_link_return_t r = ms_link_up(&l2, 90000);
    CHECK(!r.back_clip);
    ms_link_down(&l2, 100000);
    ms_link_mark_offline(&l2);
    r = ms_link_up(&l2, 100000 + 30000);
    CHECK(r.back_online && !r.back_clip);
    ms_link_down(&l2, 200000);
    ms_link_mark_offline(&l2);
    r = ms_link_up(&l2, 200000 + 190000);
    CHECK(r.back_online && r.back_clip);
    p = ms_phrase_pick(&ph, MS_LINK_UP, 500000, 0, 0, MS_GRP_BACK);
    CHECK(p.kind == MS_PH_CLIP && p.group == MS_GRP_BACK && p.variant == 0);
    /* Every group and variant maps to a file name the build embeds. */
    char name[32];
    int n = 0;
    for (int g = 0; g < MS_GRP_COUNT; g++) {
        for (int v = 0; v < MS_GROUP_SIZE[g]; v++) {
            CHECK(ms_phrase_file(name, sizeof(name), g, v));
            n++;
        }
        CHECK(!ms_phrase_file(name, sizeof(name), g, MS_GROUP_SIZE[g]));
    }
    CHECK(n == 16);

    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
