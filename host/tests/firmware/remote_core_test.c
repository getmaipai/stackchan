/* Host test for visible remote control (patch TB06). cc -std=c99 -Wall -Wextra -Werror -I<dir> remote_core_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_remote_core.h"

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

int main(void)
{
    mr_t r;
    uint32_t tok = 0, t = 1000;
    mr_init(&r);
    CHECK(r.speaking == MR_SPEAK_ASK); /* the default is ask first */

    /* No session: no token, and the refusal is logged. */
    CHECK(mr_action(&r, "move", t, &tok) == MR_NO_SESSION && tok == 0);
    CHECK(mr_recent(&r, 0)->reason == MR_NO_SESSION);
    /* A bad kind. */
    CHECK(mr_action(&r, "explode", t, &tok) == MR_BAD_KIND);

    /* Token required: an action with none, a wrong one, or one for another kind is refused and logged. */
    mr_session(&r, 1, "Home page", t);
    CHECK(mr_gate(&r, "move", 0, t) == MR_NO_TOKEN);
    CHECK(mr_action(&r, "move", t, &tok) == MR_OK && tok != 0);
    CHECK(mr_gate(&r, "move", tok + 2, t) == MR_BAD_TOKEN);
    CHECK(mr_gate(&r, "photo", tok, t) == MR_WRONG_KIND);
    CHECK(mr_gate(&r, "move", tok, t) == MR_OK);          /* used */
    CHECK(mr_gate(&r, "move", tok, t) == MR_BAD_TOKEN);   /* one use only */
    CHECK(strcmp(mr_recent(&r, 0)->who, "Home page") == 0);
    /* a token ages out */
    CHECK(mr_action(&r, "find", t, &tok) == MR_OK);
    mr_session(&r, 1, NULL, t + 9000);
    CHECK(mr_gate(&r, "find", tok, t + MR_TOKEN_LIFE_MS + 1) == MR_BAD_TOKEN);

    /* Dead-man: no call for 10 s clears the session; a token then no longer works. */
    mr_init(&r);
    mr_session(&r, 1, "app", 0);
    CHECK(mr_action(&r, "dance", 5000, &tok) == MR_OK);
    CHECK(mr_session_on(&r, 9999));
    mr_session(&r, 1, "app", 9999);
    CHECK(mr_session_on(&r, 19000));
    CHECK(!mr_session_on(&r, 9999 + MR_DEAD_MAN_MS));
    CHECK(mr_gate(&r, "dance", tok, 20000) == MR_BAD_TOKEN || mr_gate(&r, "dance", tok, 20000) == MR_NO_SESSION);
    CHECK(mr_action(&r, "dance", 20000, &tok) == MR_NO_SESSION);
    mr_session(&r, 1, "again", 30000);
    mr_session(&r, 0, NULL, 31000);
    CHECK(mr_action(&r, "dance", 31000, &tok) == MR_NO_SESSION);

    /* SAY: notice 0.8 s, then ask first by default. */
    mr_init(&r);
    mr_session(&r, 1, "Sage's phone", 0);
    uint32_t now = 1000;
    CHECK(mr_say(&r, "hello", 0, now) == MR_NO_TOKEN);
    CHECK(mr_action(&r, "say", now, &tok) == MR_OK && mr_say(&r, "hello there", tok, now) == MR_OK);
    CHECK(mr_say_poll(&r, now + 799) == MR_SAY_NONE);
    CHECK(mr_say_poll(&r, now + 800) == MR_SAY_ASKING);
    CHECK(mr_say_poll(&r, now + 900) == MR_SAY_NONE);
    CHECK(mr_tap(&r, now + 1000) == MR_SAY_SPEAK);        /* a tap allows */
    CHECK(mr_say_poll(&r, now + 1100) == MR_SAY_NONE);
    /* ask first, nobody taps: gives up after 30 s and says nothing */
    now = 5000; mr_session(&r, 1, NULL, now);
    CHECK(mr_action(&r, "say", now, &tok) == MR_OK && mr_say(&r, "anyone", tok, now) == MR_OK);
    CHECK(mr_say_poll(&r, now + 800) == MR_SAY_ASKING);
    mr_session(&r, 1, NULL, now + 8000); mr_session(&r, 1, NULL, now + 16000); mr_session(&r, 1, NULL, now + 24000);
    CHECK(mr_say_poll(&r, now + 800 + MR_ASK_WAIT_MS - 1) == MR_SAY_NONE);
    mr_session(&r, 1, NULL, now + 30000);
    CHECK(mr_say_poll(&r, now + 800 + MR_ASK_WAIT_MS) == MR_SAY_CANCELLED);
    CHECK(mr_recent(&r, 0)->cancelled == 1);

    /* Mode on: speaks after the notice; a tap or the stop word in the notice cancels it. */
    mr_init(&r); r.speaking = MR_SPEAK_ON; mr_session(&r, 1, "x", 0);
    now = 100000;
    mr_session(&r, 1, NULL, now);
    CHECK(mr_action(&r, "say", now, &tok) == MR_OK && mr_say(&r, "one", tok, now) == MR_OK);
    CHECK(mr_say_poll(&r, now + 800) == MR_SAY_SPEAK);
    mr_session(&r, 1, NULL, now + 2000);
    CHECK(mr_action(&r, "say", now + 2000, &tok) == MR_OK && mr_say(&r, "two", tok, now + 2000) == MR_OK);
    CHECK(mr_tap(&r, now + 2300) == MR_SAY_CANCELLED && mr_say_poll(&r, now + 3000) == MR_SAY_NONE);
    mr_session(&r, 1, NULL, now + 4000);
    CHECK(mr_action(&r, "say", now + 4000, &tok) == MR_OK && mr_say(&r, "three", tok, now + 4000) == MR_OK);
    CHECK(mr_stop(&r) == MR_SAY_CANCELLED && mr_stop(&r) == MR_SAY_NONE);
    /* Rate: three a minute; the fourth is refused and logged, and the minute rolls. */
    mr_session(&r, 1, NULL, now + 5000);
    CHECK(mr_action(&r, "say", now + 5000, &tok) == MR_OK && mr_say(&r, "four", tok, now + 5000) == MR_RATE);
    CHECK(strcmp(MR_REASONS[mr_recent(&r, 0)->reason], "rate_limit") == 0);
    mr_session(&r, 1, NULL, now + 61000);
    CHECK(mr_action(&r, "say", now + 61000, &tok) == MR_OK);
    CHECK(mr_say(&r, "five", tok, now + 61000) == MR_OK);

    /* Off refuses; 200 characters allowed, 201 not; empty refused. */
    mr_init(&r); mr_session(&r, 1, "x", 0); r.speaking = MR_SPEAK_OFF;
    CHECK(mr_action(&r, "say", 10, &tok) == MR_OK && mr_say(&r, "hi", tok, 10) == MR_SAY_OFF);
    r.speaking = MR_SPEAK_ON;
    char big[300]; memset(big, 'a', 299); big[299] = 0;
    big[200] = 0;
    CHECK(mr_action(&r, "say", 20, &tok) == MR_OK && mr_say(&r, big, tok, 20) == MR_OK);
    mr_stop(&r);
    big[200] = 'a'; big[201] = 0;
    CHECK(mr_action(&r, "say", 30, &tok) == MR_OK && mr_say(&r, big, tok, 30) == MR_TOO_LONG);
    CHECK(mr_say(&r, "", tok, 30) == MR_EMPTY);
    CHECK(mr_parse_speaking("ask", &r.speaking) && r.speaking == MR_SPEAK_ASK && !mr_parse_speaking("maybe", &r.speaking));
    /* A second say while one is pending is busy. */
    CHECK(mr_action(&r, "say", 40, &tok) == MR_OK && mr_say(&r, "a", tok, 40) == MR_OK);
    CHECK(mr_action(&r, "say", 41, &tok) == MR_OK && mr_say(&r, "b", tok, 41) == MR_BUSY);
    /* the host dying during a notice cancels it */
    CHECK(mr_say_poll(&r, 40 + MR_DEAD_MAN_MS + 50) == MR_SAY_CANCELLED);

    /* History: the last 10, newest first, never cleared by use; control characters in the text are flattened. */
    mr_init(&r); mr_session(&r, 1, "who", 0);
    for (int i = 0; i < 25; i++) mr_gate(&r, "move", 0, (uint32_t)i);
    CHECK(r.hist_n == MR_HISTORY && mr_recent(&r, 0)->at_ms == 24 && mr_recent(&r, 9)->at_ms == 15 && mr_recent(&r, 10) == NULL);
    mr_log(&r, 99, MR_SAY, MR_OK, "a\nb", 0);
    CHECK(strcmp(mr_recent(&r, 0)->text, "a b") == 0);
    if (failures) { printf("%d failures\n", failures); return 1; }
    printf("all passed\n");
    return 0;
}
