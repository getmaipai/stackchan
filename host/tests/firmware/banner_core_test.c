/* Host test for the banner row logic (patch N01): the queue, priorities, minimum display time, replace-in-place tags, the
 * session chip, the strip, fitting, the marquee and the eased shift of the face.
 * cc -std=c99 -Wall -Wextra -Werror -I<headers> banner_core_test.c */
#include <stdio.h>
#include <string.h>

#include "maipai_banner_core.h"

static int fails;
#define CHECK(c)                                        \
    do {                                                \
        if (!(c)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #c); \
            fails++;                                    \
        }                                               \
    } while (0)

static const char* shown(const mb_t* b, int* kind)
{
    const char* t;
    int icon, prio;
    *kind = mb_content(b, &t, &icon, &prio);
    return t;
}

static void test_one_message(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    shown(&b, &k);
    CHECK(k == 0);
    CHECK(mb_post(&b, 1000, "Remote: moving", MB_ICON_REMOTE, MB_PRIO_PRIVACY, MB_TAG_CUE, 4000) == 1);
    CHECK(strcmp(shown(&b, &k), "Remote: moving") == 0 && k == 1);
    mb_tick(&b, 4900);
    CHECK(strcmp(shown(&b, &k), "Remote: moving") == 0); /* still inside its 4 s */
    mb_tick(&b, 5001);
    shown(&b, &k);
    CHECK(k == 0); /* auto-hide */
    CHECK(mb_post(&b, 6000, "", 0, 0, 0, 100) == 0);   /* empty text is not a message */
}

static void test_minimum_time(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    mb_post(&b, 0, "Volume 40", MB_ICON_NONE, MB_PRIO_NOTICE, MB_TAG_VOLUME, 100); /* asks for 100 ms */
    mb_tick(&b, 500);
    shown(&b, &k);
    CHECK(k == 1);                       /* a short ask still shows MB_MIN_MS */
    mb_tick(&b, MB_MIN_MS + 1);
    shown(&b, &k);
    CHECK(k == 0);
}

static void test_priority_and_requeue(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    mb_post(&b, 0, "Here I am!", MB_ICON_RING, MB_PRIO_NOTICE, MB_TAG_FIND, 6000);
    mb_post(&b, 100, "Remote: photo", MB_ICON_REMOTE, MB_PRIO_PRIVACY, MB_TAG_CUE, 3000);
    CHECK(strcmp(shown(&b, &k), "Here I am!") == 0);          /* the minimum time of the first one is respected */
    CHECK(b.nq == 1);
    mb_tick(&b, MB_MIN_MS + 10);
    CHECK(strcmp(shown(&b, &k), "Remote: photo") == 0);       /* then the privacy cue takes the row */
    CHECK(b.nq == 1 && strcmp(b.q[0].text, "Here I am!") == 0); /* and the notice it displaced waits */
    mb_tick(&b, MB_MIN_MS + 10 + 3100);
    CHECK(strcmp(shown(&b, &k), "Here I am!") == 0);          /* it comes back when the cue is over */
    /* a post that is more urgent after the minimum time preempts at once */
    mb_post(&b, 10000, "Remote: moving", MB_ICON_REMOTE, MB_PRIO_PRIVACY, MB_TAG_CUE, 2000);
    CHECK(strcmp(shown(&b, &k), "Remote: moving") == 0);
}

static void test_tag_replaces(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    mb_post(&b, 0, "Volume 30", 0, MB_PRIO_NOTICE, MB_TAG_VOLUME, 1600);
    mb_post(&b, 200, "Volume 40", 0, MB_PRIO_NOTICE, MB_TAG_VOLUME, 1600);
    CHECK(strcmp(shown(&b, &k), "Volume 40") == 0 && b.nq == 0);
    /* the same words again only extend the hold */
    mb_post(&b, 1500, "Volume 40", 0, MB_PRIO_NOTICE, MB_TAG_VOLUME, 1600);
    mb_tick(&b, 3000);
    CHECK(strcmp(shown(&b, &k), "Volume 40") == 0);
    mb_tick(&b, 3200);
    shown(&b, &k);
    CHECK(k == 0);
}

static void test_captions(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    mb_post(&b, 0, "Hello there", MB_ICON_SPEECH, MB_PRIO_CAPTION, MB_TAG_CAPTION, 2600);
    mb_post(&b, 50, "How are you today", MB_ICON_SPEECH, MB_PRIO_CAPTION, MB_TAG_CAPTION, 2600);
    CHECK(strcmp(shown(&b, &k), "How are you today") == 0 && b.nq == 0); /* the newest caption wins */
    mb_post(&b, 60, "Offline", MB_ICON_WIFI_OFF, MB_PRIO_NOTICE, MB_TAG_LINK, 0);
    CHECK(strcmp(shown(&b, &k), "How are you today") == 0 && b.nq == 1);  /* the caption keeps its minimum time first... */
    mb_tick(&b, 1700);
    CHECK(strcmp(shown(&b, &k), "Offline") == 0 && b.nq == 0);            /* ...then the notice outranks it (a caption is not kept) */
    mb_post(&b, 1800, "Another caption", MB_ICON_SPEECH, MB_PRIO_CAPTION, MB_TAG_CAPTION, 2600);
    CHECK(strcmp(shown(&b, &k), "Offline") == 0 && b.nq == 1);            /* a caption waits behind a notice */
    mb_clear_tag(&b, 5000, MB_TAG_LINK);
    mb_tick(&b, 5001);
    CHECK(strcmp(shown(&b, &k), "Another caption") == 0);
    CHECK(mb_clear_tag(&b, 5002, MB_TAG_CAPTION) == 1);                   /* cleared before its minimum time ends: it ends by itself */
    mb_tick(&b, 5001 + MB_MIN_MS + 5);
    shown(&b, &k);
    CHECK(k == 0);
}

static void test_sticky_and_clear(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    mb_post(&b, 0, "Remote: please come here", MB_ICON_REMOTE, MB_PRIO_PRIVACY, MB_TAG_SAY, 0);
    mb_tick(&b, 600000);
    CHECK(strcmp(shown(&b, &k), "Remote: please come here") == 0); /* sticky: until cleared */
    mb_clear_tag(&b, 600001, MB_TAG_SAY);
    shown(&b, &k);
    CHECK(k == 0);
}

static void test_queue_full(void)
{
    mb_t b;
    mb_init(&b);
    mb_post(&b, 0, "a", 0, MB_PRIO_PRIVACY, 0, 5000);
    for (int i = 0; i < MB_QUEUE; i++) {
        char t[8] = "n";
        t[1] = (char)('0' + i);
        t[2] = 0;
        CHECK(mb_post(&b, 10, t, 0, MB_PRIO_NOTICE, 0, 2000) == 1);
    }
    CHECK(b.nq == MB_QUEUE);
    CHECK(mb_post(&b, 20, "late caption", 0, MB_PRIO_CAPTION, 0, 2000) == 0); /* a full queue of notices drops a caption */
    CHECK(mb_post(&b, 20, "urgent", 0, MB_PRIO_PRIVACY, 0, 2000) == 1);       /* but makes room for a privacy cue */
    CHECK(b.nq == MB_QUEUE);
}

static void test_session_chip(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    mb_session(&b, 1, "remote");
    CHECK(strcmp(shown(&b, &k), "Remote connected") == 0 && k == 2);
    CHECK((b.strip & (1u << MB_FLAG_REMOTE)) != 0);
    mb_session(&b, 1, "Kitchen tablet in the hall");
    CHECK(strcmp(shown(&b, &k), "Remote connected: Kitchen tablet in th") == 0);   /* long labels are cut to 20 letters */
    mb_post(&b, 100, "Remote: moving", MB_ICON_REMOTE, MB_PRIO_PRIVACY, MB_TAG_CUE, 2000);
    CHECK(strcmp(shown(&b, &k), "Remote: moving") == 0 && k == 1); /* a message takes the row from the chip */
    mb_tick(&b, 3000);
    CHECK(strcmp(shown(&b, &k), "Remote connected: Kitchen tablet in th") == 0 && k == 2); /* and the chip returns, steady */
    mb_session(&b, 0, "");
    shown(&b, &k);
    CHECK(k == 0 && (b.strip & (1u << MB_FLAG_REMOTE)) == 0);
}

static void test_strip(void)
{
    mb_t b;
    mb_init(&b);
    const uint32_t r0 = b.rev;
    mb_flag(&b, MB_FLAG_CAMERA, 1, 0, 2000);
    CHECK(b.rev != r0 && (b.strip & (1u << MB_FLAG_CAMERA)));
    mb_tick(&b, 1999);
    CHECK(b.strip & (1u << MB_FLAG_CAMERA));
    mb_tick(&b, 2001);
    CHECK(!(b.strip & (1u << MB_FLAG_CAMERA)));
    CHECK(mb_strip_w(0) == 0 && mb_strip_w(1u << MB_FLAG_MIC) == MB_STRIP_GLYPH_W);
    CHECK(mb_strip_w(3u) == 2 * MB_STRIP_GLYPH_W + MB_STRIP_GAP);
    /* battery: under 20 percent and not charging, or a cable blip, or always; never when unknown */
    CHECK(mb_battery_shown(19, 0, 0, MB_BAR_HIDDEN, 0) == 1);
    CHECK(mb_battery_shown(20, 0, 0, MB_BAR_HIDDEN, 0) == 0);
    CHECK(mb_battery_shown(10, 1, 1, MB_BAR_HIDDEN, 0) == 0);
    CHECK(mb_battery_shown(80, 1, 1, MB_BAR_HIDDEN, 1) == 1);
    CHECK(mb_battery_shown(80, 0, 0, MB_BAR_ALWAYS, 0) == 1);
    CHECK(mb_battery_shown(-1, 0, 0, MB_BAR_ALWAYS, 0) == 0);
    CHECK(mb_wifi_shown(1, 1, MB_BAR_HIDDEN) == 0 && mb_wifi_shown(0, 1, MB_BAR_HIDDEN) == 1 && mb_wifi_shown(1, 0, MB_BAR_HIDDEN) == 1);
    CHECK(mb_wifi_shown(1, 1, MB_BAR_ALWAYS) == 1);
    CHECK((MB_FLAG_ALWAYS_ON & (1u << MB_FLAG_MIC)) && (MB_FLAG_ALWAYS_ON & (1u << MB_FLAG_CAMERA)) && (MB_FLAG_ALWAYS_ON & (1u << MB_FLAG_REMOTE)));
}

static void test_fit_and_marquee(void)
{
    CHECK(mb_fit(100, 200) == MB_FIT_ONE && mb_fit(200, 200) == MB_FIT_ONE);
    CHECK(mb_fit(201, 200) == MB_FIT_MARQUEE && mb_fit(900, 200) == MB_FIT_MARQUEE); /* no second tier: a long text scrolls */
    CHECK(mb_marquee_x(0, 100) == 0 && mb_marquee_x(MB_SCROLL_PAUSE_MS - 1, 100) == 0); /* waits first */
    const int mid = mb_marquee_x(MB_SCROLL_PAUSE_MS + 1000, 100);
    CHECK(mid > 30 && mid < 40);                                                      /* 36 px a second */
    CHECK(mb_marquee_x(MB_SCROLL_PAUSE_MS + 100 * 1000 / MB_SCROLL_PX_S + 10, 100) == 100); /* waits at the end */
    int last = 0, mono = 1;
    for (uint32_t t = 0; t < mb_marquee_pass_ms(100); t += 33) {
        const int x = mb_marquee_x(t, 100);
        if (x < last) mono = 0;
        last = x;
    }
    CHECK(mono && last == 100);
    CHECK(mb_marquee_x(5000, 0) == 0 && mb_marquee_pass_ms(0) == 0);
}

/* The one rectangle: the same for every message, every chip, every length of text, every strip and every fade step. */
static void test_row_rect_is_constant(void)
{
    const mb_rect_t row = mb_row_rect();
    CHECK(row.x0 == MB_ROW_X && row.y0 == MB_ROW_Y && row.x1 == MB_ROW_X + MB_ROW_W && row.y1 == MB_ROW_Y + MB_ROW_H);
    /* the row is full width with equal margins and sits inside the banner zone, centered vertically */
    CHECK(row.x0 == MB_SCREEN_W - row.x1);
    CHECK(mb_rect_inside(row, mb_zone_banner()));
    CHECK(row.y0 - mb_zone_banner().y0 == mb_zone_banner().y1 - row.y1);
    const char* texts[] = {"Hi", "Remote: finding me", "Remote message: please come to the kitchen when you hear this, dinner is ready", "Offline"};
    for (int t = 0; t < 4; t++)
        for (unsigned bits = 0; bits < (1u << MB_FLAG_COUNT); bits++)
            for (int icon = 0; icon < MB_ICON_COUNT; icon++) {
                mb_t b;
                mb_init(&b);
                mb_post(&b, 100, texts[t], icon, MB_PRIO_NOTICE, 0, 3000);
                for (int f = 0; f < MB_FLAG_COUNT; f++) mb_flag(&b, f, (bits >> f) & 1, 100, 0);
                const mb_rect_t r = mb_row_rect();
                CHECK(memcmp(&r, &row, sizeof r) == 0); /* the row has no state: nothing in b can move it */
                const int room = mb_text_room(mb_strip_visible(&b), icon);
                CHECK(room > 60 && room < MB_ROW_W);    /* the text area is always inside the row */
            }
    /* the fade changes only the opacity, in steps that arrive */
    int opa = 0, frames = 0;
    while (opa != 255 && frames < 100) {
        const int next = mb_fade_step(opa, 1, 33);
        CHECK(next > opa);
        opa = next;
        frames++;
    }
    CHECK(opa == 255 && frames >= 3 && frames <= 8); /* about 150 ms */
    while (opa != 0 && frames < 200) {
        const int next = mb_fade_step(opa, 0, 33);
        CHECK(next < opa);
        opa = next;
        frames++;
    }
    CHECK(opa == 0);
}

/* The zones never overlap and the row, the face and the subtitles each live in their own. */
static void test_zones(void)
{
    const mb_rect_t b = mb_zone_banner(), f = mb_zone_face(), s = mb_zone_sub();
    CHECK(!mb_rect_overlap(b, f) && !mb_rect_overlap(f, s) && !mb_rect_overlap(b, s));
    CHECK(b.y1 == f.y0 && f.y1 == s.y0 && b.y0 == 0 && s.y1 == MB_SCREEN_H); /* together they are the whole screen */
    CHECK(b.y1 == 28 && f.y1 == 184 && f.y1 - f.y0 == 156 && s.y1 - s.y0 == 56);
    CHECK(mb_rect_inside(mb_row_rect(), b));
}

/* A heartbeat renewal (the host repeats self.remote.session about every 3 s) changes nothing: the row is not redrawn. */
static void test_heartbeat_does_not_redraw(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    mb_session(&b, 1, "Settings page");
    CHECK(strcmp(shown(&b, &k), "Remote connected: Settings page") == 0 && k == 2);
    const uint32_t rev = b.rev;
    const mb_rect_t row = mb_row_rect();
    for (int i = 0; i < 50; i++) {
        mb_session(&b, 1, "Settings page");
        mb_tick(&b, 1000u + (uint32_t)i * 3000u);
    }
    CHECK(b.rev == rev);                                          /* no invalidation at all */
    mb_rect_t r = mb_row_rect();
    CHECK(memcmp(&r, &row, sizeof r) == 0);
    CHECK(strcmp(shown(&b, &k), "Remote connected: Settings page") == 0);
    /* a real change of label or state does redraw, once */
    mb_session(&b, 1, "Phone app");
    CHECK(b.rev == rev + 1 && strcmp(shown(&b, &k), "Remote connected: Phone app") == 0);
    mb_session(&b, 1, "Phone app");
    CHECK(b.rev == rev + 1);
    /* a controller with no name of its own: just "Remote connected" */
    mb_session(&b, 1, "remote");
    CHECK(strcmp(shown(&b, &k), "Remote connected") == 0);
    mb_session(&b, 0, "remote");
    shown(&b, &k);
    CHECK(k == 0);
    /* a temporary message replaces the chip and the chip returns (lowest priority) */
    mb_session(&b, 1, "Home hub");
    mb_post(&b, 100, "Here I am!", MB_ICON_RING, MB_PRIO_NOTICE, MB_TAG_FIND, 2000);
    CHECK(strcmp(shown(&b, &k), "Here I am!") == 0 && k == 1);
    mb_tick(&b, 4000);
    CHECK(strcmp(shown(&b, &k), "Remote connected: Home hub") == 0 && k == 2);
}

static void test_time_wrap(void)
{
    mb_t b;
    mb_init(&b);
    int k;
    const uint32_t t0 = 0xFFFFFFFFu - 500u;
    mb_post(&b, t0, "Wrap", 0, MB_PRIO_NOTICE, 0, 3000);
    mb_tick(&b, t0 + 2900u);
    CHECK(strcmp(shown(&b, &k), "Wrap") == 0);
    mb_tick(&b, t0 + 3100u);
    shown(&b, &k);
    CHECK(k == 0);
}

static void test_captions_hold(void)
{
    CHECK(mb_caption_hold(5) == 2600u && mb_caption_hold(100) == 5500u && mb_caption_hold(1000) == 12000u);
}

int main(void)
{
    test_one_message();
    test_minimum_time();
    test_priority_and_requeue();
    test_tag_replaces();
    test_captions();
    test_sticky_and_clear();
    test_queue_full();
    test_session_chip();
    test_strip();
    test_fit_and_marquee();
    test_row_rect_is_constant();
    test_zones();
    test_heartbeat_does_not_redraw();
    test_time_wrap();
    test_captions_hold();
    if (fails) {
        printf("%d failures\n", fails);
        return 1;
    }
    printf("banner_core_test: all passed\n");
    return 0;
}
