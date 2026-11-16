/* Host test for "While it thinks" (patch TB03): the delay rule, the pick, the index reader, mu-law and the tone.
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> filler_core_test.c -lm. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_filler_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static uint32_t rs = 7;
static uint32_t rnd(void)
{
    rs = rs * 1664525u + 1013904223u;
    return rs >> 4;
}

static const char* INDEX =
    "{\"rate\":16000,\"codec\":\"mulaw\",\"lang\":\"en\",\"clips\":["
    "{\"name\":\"hmm\",\"file\":\"hmm_1.ulaw\",\"ms\":420},{\"name\":\"hmm\",\"file\":\"hmm_2.ulaw\",\"ms\":500},"
    "{\"name\":\"uh\",\"file\":\"uh_1.ulaw\",\"ms\":300},{\"name\":\"ah\",\"file\":\"ah_1.ulaw\",\"ms\":280},"
    "{\"name\":\"sigh\",\"file\":\"sigh_1.ulaw\",\"ms\":900},{\"name\":\"laugh\",\"file\":\"laugh_1.ulaw\",\"ms\":600}]}";

int main(void)
{
    /* Preferences: the page's words and seconds. */
    tf_prefs_t p;
    tf_prefs_default(&p);
    CHECK(p.mode == TF_MODE_TONE && p.wait_ms == 400);
    uint8_t m = 9;
    CHECK(tf_parse_mode("phrase", &m) && m == TF_MODE_PHRASE && tf_parse_mode("none", &m) && m == TF_MODE_NONE);
    CHECK(!tf_parse_mode("loud", &m) && m == TF_MODE_NONE && !tf_parse_mode(NULL, &m));
    uint16_t w = 1;
    CHECK(tf_parse_wait("0.4", &w) && w == 400 && tf_parse_wait("1.5", &w) && w == 1500 && tf_parse_wait("0.2", &w) && w == 200);
    CHECK(tf_parse_wait("0.05", &w) && w == 200 && tf_parse_wait("9", &w) && w == 1500); /* kept inside the range */
    CHECK(!tf_parse_wait("abc", &w) && !tf_parse_wait("", &w) && !tf_parse_wait(NULL, &w) && !tf_parse_wait("0.4x", &w) && w == 1500);

    /* The delay rule. A turn: speaking ends, thinking starts, the wait passes, one tone plays, only once. */
    tf_rule_t r;
    tf_env_t e = {0, 1, 0, 0};
    uint8_t play = 0;
    tf_rule_init(&r);
    CHECK(tf_poll(&r, 1000, &p, &e, 0, &play) == TF_SKIP_NO_TURN); /* nothing is being waited for */
    tf_turn_start(&r);
    tf_thinking(&r, 1000);
    CHECK(tf_poll(&r, 1100, &p, &e, 0, &play) == TF_SKIP_NOT_YET);
    CHECK(tf_poll(&r, 1399, &p, &e, 0, &play) == TF_SKIP_NOT_YET);
    CHECK(tf_poll(&r, 1400, &p, &e, 0, &play) == TF_SKIP_NONE && play == TF_MODE_TONE);
    CHECK(tf_poll(&r, 1500, &p, &e, 0, &play) == TF_SKIP_NO_TURN || tf_poll(&r, 1500, &p, &e, 0, &play) == TF_SKIP_ONCE); /* once per turn */
    tf_thinking(&r, 1600); /* thinking again in the same turn: still no second one */
    CHECK(tf_poll(&r, 5000, &p, &e, 0, &play) == TF_SKIP_ONCE);
    /* The next turn plays again. */
    tf_turn_start(&r);
    tf_thinking(&r, 9000);
    CHECK(tf_poll(&r, 9400, &p, &e, 0, &play) == TF_SKIP_NONE);

    /* An answer that starts within the wait cancels it: no filler is ever played over or after the answer's audio. */
    tf_turn_start(&r);
    tf_thinking(&r, 2000);
    tf_answer_audio(&r);
    CHECK(tf_poll(&r, 2399, &p, &e, 0, &play) == TF_SKIP_AUDIO);
    CHECK(tf_poll(&r, 9999, &p, &e, 0, &play) == TF_SKIP_AUDIO);
    tf_thinking(&r, 3000); /* late thinking mark after audio: ignored */
    CHECK(tf_poll(&r, 9999, &p, &e, 0, &play) == TF_SKIP_AUDIO);

    /* The wait is the person's: 200 ms and 1500 ms, to the millisecond, across a clock wrap. */
    tf_prefs_t q = p;
    q.wait_ms = 200;
    tf_turn_start(&r);
    tf_thinking(&r, 0xFFFFFF00u);
    CHECK(tf_poll(&r, 0xFFFFFF00u + 199, &q, &e, 0, &play) == TF_SKIP_NOT_YET);
    CHECK(tf_poll(&r, 0xFFFFFF00u + 200, &q, &e, 0, &play) == TF_SKIP_NONE);
    q.wait_ms = 1500;
    tf_turn_start(&r);
    tf_thinking(&r, 10);
    CHECK(tf_poll(&r, 1509, &q, &e, 0, &play) == TF_SKIP_NOT_YET && tf_poll(&r, 1510, &q, &e, 0, &play) == TF_SKIP_NONE);

    /* Modes: none never plays; phrase plays a phrase when the pack has sounds, else the tone. */
    q = p;
    q.mode = TF_MODE_NONE;
    tf_turn_start(&r);
    tf_thinking(&r, 0);
    CHECK(tf_poll(&r, 5000, &q, &e, 1, &play) == TF_SKIP_MODE);
    q.mode = TF_MODE_PHRASE;
    CHECK(tf_poll(&r, 5000, &q, &e, 1, &play) == TF_SKIP_NONE && play == TF_MODE_PHRASE);
    tf_turn_start(&r);
    tf_thinking(&r, 0);
    CHECK(tf_poll(&r, 5000, &q, &e, 0, &play) == TF_SKIP_NONE && play == TF_MODE_TONE);

    /* Silenced by the mute, by sounds off or quiet hours (the policy bit), by full quiet, and while it speaks. */
    for (int k = 0; k < 4; k++) {
        tf_env_t s = {0, 1, 0, 0};
        if (k == 0) s.muted = 1;
        if (k == 1) s.sound_ok = 0;
        if (k == 2) s.full_quiet = 1;
        if (k == 3) s.speaking = 1;
        tf_turn_start(&r);
        tf_thinking(&r, 0);
        CHECK(tf_poll(&r, 5000, &p, &s, 1, &play) == TF_SKIP_ENV);
        CHECK(!r.played); /* a silenced filler does not use up the turn */
    }

    /* The host asks for one (it ran the delay): the same guards, once per turn. */
    tf_turn_start(&r);
    CHECK(tf_play_now(&r, TF_MODE_PHRASE, &e, 1, &play) == TF_SKIP_NONE && play == TF_MODE_PHRASE);
    CHECK(tf_play_now(&r, TF_MODE_TONE, &e, 1, &play) == TF_SKIP_ONCE);
    tf_turn_start(&r);
    e.muted = 1;
    CHECK(tf_play_now(&r, TF_MODE_TONE, &e, 1, &play) == TF_SKIP_ENV);
    e.muted = 0;
    CHECK(tf_play_now(&r, TF_MODE_NONE, &e, 1, &play) == TF_SKIP_MODE);
    /* the unit's own filler already played this turn: the host's later request is refused, not doubled */
    tf_turn_start(&r);
    tf_thinking(&r, 0);
    CHECK(tf_poll(&r, 900, &p, &e, 0, &play) == TF_SKIP_NONE);
    CHECK(tf_play_now(&r, TF_MODE_TONE, &e, 0, &play) == TF_SKIP_ONCE);

    /* The pack index. */
    static tf_index_t x;
    CHECK(tf_parse_index(INDEX, strlen(INDEX), &x) == 6 && x.rate == 16000 && strcmp(x.clip[0].name, "hmm") == 0 && strcmp(x.clip[1].file, "hmm_2.ulaw") == 0 && x.clip[2].ms == 300);
    CHECK(tf_parse_index("{\"rate\":16000,\"codec\":\"alaw\",\"clips\":[]}", 38, &x) == 0); /* only mu-law */
    CHECK(tf_parse_index("", 0, &x) == 0 && tf_parse_index(NULL, 0, &x) == 0 && tf_parse_index("{}", 2, &x) == 0);
    {
        const char* bad = "{\"rate\":16000,\"codec\":\"mulaw\",\"clips\":[{\"name\":\"hmm\",\"file\":\"../x\",\"ms\":5},{\"name\":\"uh\",\"file\":\"a/b\",\"ms\":5},"
                          "{\"name\":\"ah\",\"file\":\"ok.ulaw\",\"ms\":-3},{\"name\":\"oh\",\"file\":\"ok.ulaw\",\"ms\":300}]}";
        CHECK(tf_parse_index(bad, strlen(bad), &x) == 1 && strcmp(x.clip[0].name, "oh") == 0); /* the bad ones are dropped */
    }
    /* Fuzz the reader: byte flips, truncation, junk. It never reads outside the text and keeps only well-formed clips. */
    {
        char buf[600];
        for (int k = 0; k < 40000; k++) {
            size_t len = strlen(INDEX);
            memcpy(buf, INDEX, len + 1);
            const int flips = 1 + (int)(rnd() % 5);
            for (int i = 0; i < flips; i++) buf[rnd() % len] = (char)(rnd() % 256);
            if (rnd() % 4 == 0) len = rnd() % (len + 1);
            const int n = tf_parse_index(buf, len, &x);
            CHECK(n >= 0 && n <= TF_MAX_CLIPS);
            for (int i = 0; i < x.n; i++) {
                CHECK(x.clip[i].name[0] != 0 && strchr(x.clip[i].file, '/') == NULL && x.clip[i].ms > 0 && x.clip[i].ms <= 5000);
            }
        }
    }

    /* The pick: never the same sound twice in a row; sighs and laughs are not picked for a wait; every fitting sound comes up;
     * a sound with two takes is not twice as likely. */
    tf_parse_index(INDEX, strlen(INDEX), &x);
    int last = -1, counts[8] = {0}, repeats = 0;
    for (int k = 0; k < 20000; k++) {
        const int pick = tf_pick(&x, last, rnd());
        CHECK(pick >= 0 && pick < x.n && tf_name_fits(x.clip[pick].name));
        if (last >= 0 && strcmp(x.clip[pick].name, x.clip[last].name) == 0) repeats++;
        counts[pick]++;
        last = pick;
    }
    CHECK(repeats == 0);
    CHECK(counts[4] == 0 && counts[5] == 0);                     /* sigh, laugh */
    CHECK(counts[0] > 0 && counts[1] > 0 && counts[2] > 0 && counts[3] > 0); /* both hmm takes, uh, ah */
    const int hmm = counts[0] + counts[1];
    CHECK(hmm > 4500 && hmm < 8500 && counts[2] > 4500 && counts[3] > 4500 && counts[0] > 1500 && counts[1] > 1500); /* about a third each of three sounds */
    /* one sound only: it may repeat (there is nothing else); an empty pack picks nothing; no fitting name: any clip */
    tf_index_t one;
    memset(&one, 0, sizeof(one));
    one.n = 1;
    strcpy(one.clip[0].name, "hmm");
    CHECK(tf_pick(&one, 0, 5) == 0 && tf_pick(&one, -1, 5) == 0);
    one.n = 0;
    CHECK(tf_pick(&one, -1, 5) == -1);
    one.n = 1;
    strcpy(one.clip[0].name, "sigh");
    CHECK(tf_pick(&one, -1, 5) == 0);
    /* a stale `last` (a pack swapped in between) is harmless */
    CHECK(tf_pick(&x, 99, 1) >= 0 && tf_pick(&x, -5, 1) >= 0);

    /* The host's mu-law (not G.711): the table matches the host formula at its anchor points and is monotonic. */
    int16_t t[256];
    tf_ulaw_table(t);
    CHECK(t[0] == -32767 || t[0] == -32766);
    CHECK(abs(t[255] - 32767) <= 1 || t[255] == 32767);
    CHECK(abs(t[127]) < 150 && abs(t[128]) < 150);
    int mono = 1;
    for (int i = 1; i < 256; i++) mono &= t[i] >= t[i - 1];
    CHECK(mono);
    /* a host-encoded sample decodes back close: y = log1p(255 x)/log1p(255) */
    {
        double worst = 0;
        for (int k = -100; k <= 100; k++) {
            const double v = k / 100.0;
            const double y = (v < 0 ? -1 : 1) * log1p(255.0 * fabs(v)) / log1p(255.0);
            const int b    = (int)((y + 1.0) * 127.5 + 0.5);
            const double d = fabs(t[b] / 32767.0 - v);
            if (d > worst) worst = d;
        }
        CHECK(worst < 0.06);
    }

    /* The tone: 210 ms, two notes, soft (peak 0.18), starts and ends at silence. */
    static int16_t tone[TF_TONE_SAMPLES + 8];
    CHECK(tf_render_tone(tone, TF_TONE_SAMPLES + 8) == TF_TONE_SAMPLES);
    int pk = 0;
    for (int i = 0; i < TF_TONE_SAMPLES; i++) {
        const int a = abs(tone[i]);
        if (a > pk) pk = a;
    }
    CHECK(pk > 4500 && pk < 6200 && abs(tone[0]) < 20 && abs(tone[TF_TONE_SAMPLES - 1]) < 60);
    CHECK(tf_render_tone(tone, 100) == 100);

    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
