/* Host test for the second floor of the remote gate (patch FM03): a call with no source "remote" is gated too while a
 * remote session is on. cc -std=c99 -Wall -Wextra -Werror -I<dir with maipai_remote_core.h as FM03 leaves it> remote_floor_test.c */
#include <stdio.h>
#include "maipai_remote_core.h"

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); failures++; } } while (0)

static const char* const CUED[] = {"move", "find", "photo", "dance", "game", "listen"};
#define NCUED ((int)(sizeof(CUED) / sizeof(CUED[0])))
#define HOST 777123u

int main(void)
{
    mr_t r;
    uint32_t t = 1000, tok = 0;
    mr_init(&r);

    /* No session: nothing to protect, every source passes with no token and nothing is logged. */
    for (int i = 0; i < NCUED; i++) {
        CHECK(mr_gate_call(&r, NULL, CUED[i], 0, t) == MR_OK);
        CHECK(mr_gate_call(&r, "user", CUED[i], 0, t) == MR_OK);
    }
    CHECK(r.hist_n == 0);

    /* A session from an older host that announced no id: the floor cannot tell hosts apart, so it stays open. */
    mr_session(&r, 1, "Phone", t);
    CHECK(mr_gate_call(&r, NULL, "dance", 0, t + 1) == MR_OK);

    /* The host announces its id with the heartbeat. Now every cued kind with no source and no token is refused and logged. */
    mr_set_host(&r, HOST);
    for (int i = 0; i < NCUED; i++) {
        CHECK(mr_gate_call(&r, NULL, CUED[i], 0, t + 2) == MR_NOT_HOST);
        CHECK(mr_gate_call(&r, "", CUED[i], 0, t + 2) == MR_NOT_HOST);
        CHECK(mr_gate_call(&r, "user", CUED[i], 0, t + 2) == MR_NOT_HOST);
        CHECK(mr_recent(&r, 0)->reason == MR_NOT_HOST);
    }
    CHECK(r.hist_n == MR_HISTORY);

    /* A wrong id is no id. */
    CHECK(mr_gate_call(&r, NULL, "find", HOST + 1, t + 3) == MR_NOT_HOST);

    /* The host's own id opens every cued kind for a call that is not a controller's, again and again (it is not used up). */
    for (int i = 0; i < NCUED; i++) {
        CHECK(mr_gate_call(&r, NULL, CUED[i], HOST, t + 4) == MR_OK);
        CHECK(mr_gate_call(&r, "user", CUED[i], HOST, t + 5) == MR_OK);
    }

    /* A valid cue token for the same kind also opens it, once. */
    CHECK(mr_action(&r, "photo", t + 6, &tok) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "photo", tok, t + 7) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "photo", tok, t + 8) == MR_NOT_HOST); /* used up */
    CHECK(mr_action(&r, "dance", t + 9, &tok) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "game", tok, t + 10) == MR_NOT_HOST); /* another kind's cue */

    /* The kinds that are not cued, and a head move inside the safe range ("move_near"), pass with no id. */
    CHECK(mr_gate_call(&r, NULL, "move_near", 0, t + 11) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "sound", 0, t + 11) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "light", 0, t + 11) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "setting", 0, t + 11) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "look", 0, t + 11) == MR_OK);
    CHECK(mr_gate_call(&r, NULL, "nonsense", 0, t + 11) == MR_OK);

    /* The remote path is unchanged: a "remote" call still needs its own cue token, and the host id is no cue token. */
    CHECK(mr_gate_call(&r, "remote", "dance", HOST, t + 12) == MR_BAD_TOKEN);
    CHECK(mr_gate_call(&r, "remote", "dance", 0, t + 12) == MR_NO_TOKEN);

    /* The id belongs to its session: when the session ends or the dead-man timer runs out, the id is gone with it. */
    mr_session(&r, 0, "", t + 20);
    CHECK(r.host_id == 0);
    CHECK(mr_gate_call(&r, NULL, "dance", 0, t + 21) == MR_OK); /* no session: nothing to protect */
    mr_session(&r, 1, "Phone", t + 30);
    CHECK(mr_gate_call(&r, NULL, "dance", 0, t + 31) == MR_OK); /* a new session with no id announced yet */
    mr_set_host(&r, HOST + 5);
    mr_set_host(&r, 0); /* a heartbeat without an id does not erase it */
    CHECK(r.host_id == HOST + 5);
    CHECK(mr_gate_call(&r, NULL, "dance", 0, t + 32) == MR_NOT_HOST);
    CHECK(mr_gate_call(&r, NULL, "dance", HOST, t + 32) == MR_NOT_HOST); /* the old id is not the new session's */
    CHECK(mr_gate_call(&r, NULL, "dance", 0, t + 30 + MR_DEAD_MAN_MS + 1) == MR_OK); /* the host died: session and id are gone */
    CHECK(r.host_id == 0);

    /* The reason's wire name is stable. */
    CHECK(MR_REASONS[MR_NOT_HOST][0] == 'n' && MR_REASONS[MR_NOT_HOST][4] == 'h');

    if (failures == 0) printf("remote_floor_test: all passed\n");
    return failures == 0 ? 0 : 1;
}
