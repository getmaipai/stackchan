/* Host test of the question-and-answer game state machine with a scripted host (patch SF88). */
#include <stdio.h>
#include "maipai_qa_state_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

int main(void)
{
    qs_t s;
    uint32_t t = 1000;
    /* trivia, three rounds: question, tap an answer, verdict, wait, next question, end */
    qs_start(&s, QS_TRIVIA, 3, t);
    CHECK(s.phase == QS_WAIT && s.total == 3);
    CHECK(qs_question(&s, 1, 5, 0, t) == QR_BAD_CHOICES);          /* trivia needs two to four choices */
    CHECK(qs_question(&s, 1, 4, 0, t) == QR_OK && s.phase == QS_ASK && s.n == 1);
    CHECK(qs_question(&s, 2, 4, 0, t) == QR_WRONG_PHASE);          /* the first question is unanswered */
    CHECK(qs_tap(&s, MQA_B_NONE, t) == QE_NONE);
    CHECK(qs_tap(&s, MQA_B_YES, t) == QE_NONE);                    /* a button of another game does nothing */
    CHECK(qs_tap(&s, MQA_B_ANSWER2, t + 500) == QE_CHOICE && s.chosen == 2 && s.phase == QS_SENT);
    CHECK(qs_tap(&s, MQA_B_ANSWER1, t + 600) == QE_NONE);          /* one answer only */
    CHECK(qs_verdict(&s, 9, 1, -1, 0, 1, t + 700) == QR_BAD_ID);
    CHECK(qs_verdict(&s, 1, 0, 3, 0, 0, t + 700) == QR_OK && s.result == 2 && s.right == 3 && s.phase == QS_VERDICT);
    CHECK(qs_tick(&s, t + 700 + 1000) == QT_NONE);                 /* 1.0 s: still showing */
    CHECK(qs_tick(&s, t + 700 + 1200) == QT_VERDICT_DONE && s.phase == QS_WAIT);
    CHECK(qs_question(&s, 2, 3, 0, t + 2500) == QR_OK && s.n == 2);
    CHECK(qs_tap(&s, MQA_B_ANSWER3, t + 2600) == QE_NONE);         /* only three answers here */
    CHECK(qs_tap(&s, MQA_B_ANSWER0, t + 2700) == QE_CHOICE);
    CHECK(qs_verdict(&s, 2, 1, -1, 1, 1, t + 2800) == QR_OK && s.result == 1 && s.right == 0 && s.score == 1);
    CHECK(qs_end(&s, 1, t + 4100) == QR_OK && s.phase == QS_OVER);
    CHECK(qs_question(&s, 3, 3, 0, t + 4200) == QR_NOT_RUNNING);
    CHECK(qs_tick(&s, t + 4100 + 59000) == QT_NONE);
    CHECK(qs_tick(&s, t + 4100 + 60000) == QT_OVER_IDLE);
    qs_again(&s, t + 5000);                                        /* Play again: back to waiting, fresh counters, same game */
    CHECK(s.phase == QS_WAIT && s.kind == QS_TRIVIA && s.total == 3 && s.n == 0 && s.score == 0);

    /* riddle: Reveal asks the host, the answer stays until Next */
    qs_start(&s, QS_RIDDLE, 0, t);
    CHECK(qs_question(&s, 1, 0, 0, t) == QR_OK);
    CHECK(qs_tap(&s, MQA_B_REVEAL, t + 10) == QE_GIVEUP && s.phase == QS_SENT);
    CHECK(qs_verdict(&s, 1, 0, -1, 1, 0, t + 20) == QR_OK && s.revealed == 1);
    CHECK(qs_tick(&s, t + 20 + 5000) == QT_NONE);                  /* the answer stays */
    CHECK(qs_tap(&s, MQA_B_NEXT, t + 6000) == QE_NEXT && s.phase == QS_WAIT);
    CHECK(qs_question(&s, 2, 0, 0, t + 6100) == QR_OK);
    CHECK(qs_tap(&s, MQA_B_NEXT, t + 6200) == QE_NEXT);            /* a one-liner joke: Next from the start */
    CHECK(qs_question(&s, 3, 0, 0, t + 6300) == QR_OK);            /* the host may answer Next with a question at once */

    /* 20 Questions: the tiles report, Stop works in every phase */
    qs_start(&s, QS_TWENTY, 0, t);
    CHECK(s.total == 20);
    CHECK(qs_tap(&s, MQA_B_STOP, t) == QE_STOP);                   /* even while waiting */
    CHECK(qs_question(&s, 1, 0, 1, t) == QR_OK && s.guess == 1);
    CHECK(qs_tap(&s, MQA_B_MAYBE, t + 1) == QE_MAYBE);
    CHECK(qs_question(&s, 2, 0, 0, t + 2) == QR_OK);
    CHECK(qs_tap(&s, MQA_B_GIVE_UP, t + 3) == QE_GIVEUP);
    CHECK(qs_tap(&s, MQA_B_STOP, t + 4) == QE_STOP);

    /* the host goes away: two minutes with no message */
    qs_start(&s, QS_TWENTY, 0, t);
    CHECK(qs_tick(&s, t + 119999) == QT_NONE);
    CHECK(qs_tick(&s, t + 120000) == QT_HOST_GONE);
    qs_t idle; memset(&idle, 0, sizeof(idle));
    CHECK(qs_question(&idle, 1, 0, 0, t) == QR_NOT_RUNNING);
    CHECK(qs_tap(&idle, MQA_B_STOP, t) == QE_NONE);
    CHECK(qs_shown(&s, 40, 0) == 40);                              /* not asking: whole */
    /* typed caption pace: 14 characters a second */
    qs_start(&s, QS_TWENTY, 0, 0);
    CHECK(qs_question(&s, 1, 0, 0, 100) == QR_OK);
    CHECK(qs_shown(&s, 60, 100) == 0 && qs_shown(&s, 60, 1100) == 14 && qs_shown(&s, 60, 100 + 5000) == 60);
    qs_show_whole(&s);
    CHECK(qs_shown(&s, 60, 200) == 60);
    printf(fails ? "qa_state_core_test FAILED\n" : "qa_state_core_test ok\n");
    return fails ? 1 : 0;
}
