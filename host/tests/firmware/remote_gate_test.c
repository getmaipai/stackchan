/* Host test for the remote token gate on the other remote-facing tools (patch TC01).
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with maipai_remote_core.h as TB05 and TC01 leave it> remote_gate_test.c */
#include <stdio.h>
#include <string.h>
#include "maipai_remote_core.h"

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

static const char* const KINDS[] = {"move", "find", "photo", "dance", "game", "listen"};

int main(void)
{
    mr_t r;
    uint32_t tok = 0, t = 1000;
    mr_init(&r);

    /* Local and person-asked calls are never gated and never logged, with or without a session. */
    CHECK(mr_gate_call(&r, NULL, "move", 0, t) == MR_OK);
    CHECK(mr_gate_call(&r, "", "move", 0, t) == MR_OK);
    CHECK(mr_gate_call(&r, "user", "move", 0, t) == MR_OK);
    CHECK(mr_gate_call(&r, "local", "photo", 0, t) == MR_OK);
    CHECK(r.hist_n == 0);

    /* A remote call with no session, then with a session but no token, is refused and logged, for every kind. */
    for (unsigned i = 0; i < sizeof(KINDS) / sizeof(KINDS[0]); i++) {
        CHECK(mr_gate_call(&r, "remote", KINDS[i], 0, t) == MR_NO_TOKEN);
    }
    CHECK(r.hist_n == MR_HISTORY || r.hist_n == 6);
    CHECK(mr_recent(&r, 0)->reason == MR_NO_TOKEN);

    mr_session(&r, 1, "Phone", t);
    for (unsigned i = 0; i < sizeof(KINDS) / sizeof(KINDS[0]); i++) {
        mr_t q = r;
        CHECK(mr_action(&q, KINDS[i], t, &tok) == MR_OK);
        CHECK(mr_gate_call(&q, "remote", KINDS[i], 0, t) == MR_NO_TOKEN);        /* no token */
        CHECK(mr_gate_call(&q, "remote", KINDS[i], tok + 2, t) == MR_BAD_TOKEN); /* wrong token */
        CHECK(mr_gate_call(&q, "remote", KINDS[(i + 1) % 6], tok, t) == MR_WRONG_KIND); /* another kind's cue */
        CHECK(mr_gate_call(&q, "remote", KINDS[i], tok, t + 16000) == MR_BAD_TOKEN);    /* too old (15 s) */
    }

    /* The good path: one cue, one use. The kind then stays open for the banner time, for calls with no token. */
    CHECK(mr_action(&r, "find", t, &tok) == MR_OK);
    mr_set_window(&r, 5);
    CHECK(mr_gate_call(&r, "remote", "find", tok, t + 100) == MR_OK);
    CHECK(mr_gate_call(&r, "remote", "find", tok, t + 200) == MR_BAD_TOKEN);  /* a used token is not a token */
    CHECK(mr_gate_call(&r, "remote", "find", 0, t + 4000) == MR_OK);          /* inside the window */
    CHECK(mr_gate_call(&r, "remote", "move", 0, t + 4000) == MR_NO_TOKEN);    /* another kind stays shut */
    CHECK(mr_gate_call(&r, "remote", "find", 0, t + 5200) == MR_NO_TOKEN);    /* the window ran out */
    CHECK(mr_gate_call(&r, "user", "move", 0, t + 5200) == MR_OK);            /* user-marked is unchanged */

    /* The window needs the session: end it and the kind shuts at once. */
    CHECK(mr_action(&r, "dance", t + 6000, &tok) == MR_OK);
    mr_set_window(&r, 30);
    CHECK(mr_gate_call(&r, "remote", "dance", tok, t + 6001) == MR_OK);
    CHECK(mr_gate_call(&r, "remote", "dance", 0, t + 6002) == MR_OK);
    mr_session(&r, 0, "", t + 6003);
    CHECK(mr_gate_call(&r, "remote", "dance", 0, t + 6004) == MR_NO_TOKEN);
    /* The dead-man timeout closes it too. */
    mr_session(&r, 1, "Phone", t + 7000);
    CHECK(mr_action(&r, "game", t + 7000, &tok) == MR_OK);
    CHECK(mr_gate_call(&r, "remote", "game", tok, t + 7001) == MR_OK);
    CHECK(mr_gate_call(&r, "remote", "game", 0, t + 7000 + MR_DEAD_MAN_MS + 1) == MR_NO_TOKEN);

    /* A refusal is in the history with its kind and reason. */
    CHECK(mr_recent(&r, 0)->kind == MR_GAME && mr_recent(&r, 0)->reason == MR_NO_TOKEN);

    /* The Remote page's beep, flash, mute and overlay buttons have kinds of their own, so the unit shows a banner for them too (TC04). */
    {
        static const char* const extra[] = {"sound", "light", "setting", "look"};
        mr_session(&r, 1, "Phone", t + 9000);
        for (unsigned i = 0; i < 4; i++) {
            CHECK(mr_kind_by_name(extra[i]) >= 0);
            CHECK(mr_action(&r, extra[i], t + 9000, &tok) == MR_OK && tok != 0);
            CHECK(strlen(MR_BANNERS[mr_kind_by_name(extra[i])]) > 8);
        }
        CHECK(mr_action(&r, "explode", t + 9000, &tok) == MR_BAD_KIND);
    }

    /* The window seconds are clamped to 1 to 30. */
    mr_set_window(&r, 0);
    CHECK(r.window_ms == 1000u);
    mr_set_window(&r, 99);
    CHECK(r.window_ms == 30000u);

    if (failures) { printf("%d failed\n", failures); return 1; }
    printf("all passed\n");
    return 0;
}
