#include <stdio.h>
#include "maipai_firstrun_core.h"

#define CHECK(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "CHECK failed at %s:%d: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

static int happy_path(int wifi_set)
{
    mfr_t m;
    mfr_init(&m, wifi_set, 0);
    CHECK(m.step == MFR_LANGUAGE && m.answered_mask == 0 && m.mode == MFR_MODE_NONE);
    CHECK(mfr_resume_step(&m) == MFR_LANGUAGE);
    CHECK(mfr_choose_language(&m, MFR_LANG_ES));
    CHECK(mfr_resume_step(&m) == MFR_NAME);
    CHECK(mfr_choose_name(&m, 3));
    CHECK(m.name == 3);
    if (wifi_set) {
        CHECK(m.step == MFR_BRAIN);
    } else {
        CHECK(m.step == MFR_WIFI);
        CHECK(mfr_resume_step(&m) == MFR_WIFI);
        CHECK(mfr_wifi_done(&m));
    }
    CHECK(m.step == MFR_BRAIN && mfr_resume_step(&m) == MFR_BRAIN);
    CHECK(mfr_choose_mode(&m, MFR_MODE_OWN));
    CHECK(m.step == MFR_PRIVACY && mfr_resume_step(&m) == MFR_PRIVACY);
    CHECK(mfr_ack_privacy(&m));
    CHECK(mfr_done(&m) && mfr_resume_step(&m) == MFR_DONE);
    CHECK(!mfr_back_visible(MFR_LANGUAGE));
    CHECK(mfr_back_visible(MFR_NAME) && mfr_back_visible(MFR_BRAIN) && mfr_back_visible(MFR_PRIVACY));
    CHECK(!mfr_back_visible(MFR_WIFI) && !mfr_back_visible(MFR_DONE));
    return 0;
}

static int check_boxes(const int (*b)[4], int n)
{
    for (int i = 0; i < n; i++) {
        CHECK(b[i][0] >= 8 && b[i][0] + b[i][2] <= 320 - 8 && b[i][1] >= 4 && b[i][1] + b[i][3] <= 240 - 4 && b[i][3] >= 48 && b[i][2] >= 56);   /* finger size on the glass */
        for (int j = 0; j < i; j++) {
            CHECK(b[i][0] + b[i][2] + 8 <= b[j][0] || b[j][0] + b[j][2] + 8 <= b[i][0] || b[i][1] + b[i][3] + 8 <= b[j][1] || b[j][1] + b[j][3] + 8 <= b[i][1]);   /* 8 px apart */
        }
    }
    return 0;
}

int main(void)
{
    mfr_t m;
    int i;
    CHECK(happy_path(0) == 0);
    CHECK(happy_path(1) == 0);

    mfr_init(&m, 1, 0);
    CHECK(mfr_choose_language(&m, MFR_LANG_EN));
    CHECK(mfr_choose_name(&m, 2));
    CHECK((m.answered_mask & (MFR_ANSWER_LANGUAGE | MFR_ANSWER_NAME)) ==
          (MFR_ANSWER_LANGUAGE | MFR_ANSWER_NAME));
    mfr_back(&m);
    CHECK(m.step == MFR_NAME && m.language == MFR_LANG_EN && m.name == 2);
    mfr_back(&m);
    CHECK(m.step == MFR_LANGUAGE);
    mfr_back(&m);
    CHECK(m.step == MFR_LANGUAGE);

    for (i = MFR_LANGUAGE; i <= MFR_DONE; ++i) {
        mfr_init(&m, 0, 0);
        m.step = (int8_t)i;
        CHECK(mfr_resume_step(&m) == MFR_LANGUAGE);
        m.answered_mask = MFR_ANSWER_LANGUAGE;
        CHECK(mfr_resume_step(&m) == MFR_NAME);
        m.answered_mask |= MFR_ANSWER_NAME;
        CHECK(mfr_resume_step(&m) == MFR_WIFI);
        m.answered_mask |= MFR_ANSWER_WIFI;
        CHECK(mfr_resume_step(&m) == MFR_BRAIN);
        m.answered_mask |= MFR_ANSWER_BRAIN;
        CHECK(mfr_resume_step(&m) == MFR_PRIVACY);
        m.answered_mask |= MFR_ANSWER_PRIVACY;
        CHECK(mfr_resume_step(&m) == MFR_DONE);
    }

    mfr_init(&m, 0, 1);
    CHECK(m.mode == MFR_MODE_HOME && !(m.answered_mask & MFR_ANSWER_BRAIN));
    CHECK(mfr_choose_language(&m, -1) == 0 && m.step == MFR_LANGUAGE);
    CHECK(mfr_choose_language(&m, MFR_LANG_COUNT) == 0);
    CHECK(mfr_choose_language(&m, MFR_LANG_FR));
    CHECK(mfr_choose_name(&m, -1) == 0 && m.step == MFR_NAME);
    CHECK(mfr_choose_name(&m, MFR_NAME_COUNT) == 0 && m.step == MFR_NAME);   /* seven names: 0 to 6; 7 is not one */
    CHECK(mfr_choose_name(&m, 0));
    CHECK(m.step == MFR_WIFI);
    CHECK(mfr_choose_mode(&m, MFR_MODE_HOME) == 0 && m.step == MFR_WIFI);
    CHECK(mfr_wifi_done(&m));
#ifdef MFR_SKIP_BRAIN_WITH_HUB   /* patch UX31: a known hub answers the brain question: Home, and the flow goes on to the privacy step; Back still reaches the question */
    CHECK(m.step == MFR_PRIVACY && m.mode == MFR_MODE_HOME && (m.answered_mask & MFR_ANSWER_BRAIN));
    CHECK(mfr_choose_mode(&m, 7) == 0 && m.step == MFR_PRIVACY);
    mfr_back(&m);
    CHECK(m.step == MFR_BRAIN && mfr_choose_mode(&m, MFR_MODE_HOME));
#else
    CHECK(mfr_choose_mode(&m, 7) == 0 && m.step == MFR_BRAIN);
    CHECK(mfr_choose_mode(&m, MFR_MODE_HOME));
#endif
    CHECK(mfr_ack_privacy(&m));
    mfr_back(&m);
    CHECK(m.step == MFR_DONE);
    /* patch UX11: StackChan is the first tile and the default, saved as index 6, exactly as picked; the six older names keep their indexes */
    {
        mfr_t n;
        mfr_init(&n, 1, 0);
        CHECK(mfr_choose_language(&n, MFR_LANG_FR));
        CHECK(n.name == -1 && mfr_name_shown(&n) == MFR_NAME_STACKCHAN);       /* nothing picked: StackChan shows as the default */
        CHECK(mfr_name_at_slot(0) == MFR_NAME_STACKCHAN && mfr_name_at_slot(1) == 0 && mfr_name_at_slot(6) == 5);
        int seen[MFR_NAME_COUNT] = {0};
        for (int slot = 0; slot < MFR_NAME_COUNT; slot++) seen[mfr_name_at_slot(slot)]++;
        for (int i = 0; i < MFR_NAME_COUNT; i++) CHECK(seen[i] == 1);          /* every name is on the screen once */
        CHECK(mfr_choose_name(&n, MFR_NAME_STACKCHAN) && n.name == 6);
        CHECK(mfr_name_shown(&n) == 6 && (n.answered_mask & MFR_ANSWER_NAME));
        mfr_back(&n);
        CHECK(n.step == MFR_NAME && n.name == 6);                                /* back keeps the answer */
        CHECK(mfr_choose_name(&n, 2) && n.name == 2 && mfr_name_shown(&n) == 2);   /* another name replaces it exactly */
    }
    /* patch UX12: skip takes the shown default of the step and goes on; the brain step has a third answer, set one up for me */
    {
        mfr_t k;
        mfr_init(&k, 1, 0);
        CHECK(mfr_skip_visible(MFR_LANGUAGE) && mfr_skip_visible(MFR_NAME) && mfr_skip_visible(MFR_BRAIN) && !mfr_skip_visible(MFR_PRIVACY) && !mfr_skip_visible(MFR_DONE));
        CHECK(mfr_skip(&k) && k.step == MFR_NAME && k.language == MFR_LANG_EN);       /* skip on step 1: English */
        CHECK(mfr_skip(&k) && k.name == MFR_NAME_STACKCHAN && k.step == MFR_BRAIN);   /* skip on the name: StackChan, exactly as saved */
        CHECK(mfr_mode_shown(&k) == MFR_MODE_SETUP);                                    /* no hub known: "set one up for me" is the default shown */
        CHECK(mfr_skip(&k) && k.mode == MFR_MODE_SETUP && k.step == MFR_PRIVACY);
        CHECK(mfr_skip(&k) && k.step == MFR_DONE && mfr_done(&k));
        CHECK(mfr_skip(&k) == 0);                                                       /* nothing to skip once done */
        mfr_t h;
        mfr_init(&h, 1, 1);
        CHECK(mfr_mode_shown(&h) == MFR_MODE_HOME);                                     /* a known hub is the default shown */
        CHECK(mfr_choose_language(&h, MFR_LANG_DE) && mfr_choose_name(&h, 1));
#ifdef MFR_SKIP_BRAIN_WITH_HUB
        CHECK(h.step == MFR_PRIVACY && h.mode == MFR_MODE_HOME);                        /* patch UX31: no brain question with a hub known */
#else
        CHECK(h.step == MFR_BRAIN);
#endif
        CHECK(mfr_skip(&h) && h.mode == MFR_MODE_HOME);
        /* skip keeps an answer already given: a language picked, then skip on the same step later, keeps it */
        mfr_t a;
        mfr_init(&a, 1, 0);
        CHECK(mfr_choose_language(&a, MFR_LANG_IT) && a.language == MFR_LANG_IT);
        mfr_back(&a);
        CHECK(a.step == MFR_LANGUAGE);
        CHECK(mfr_skip(&a) && a.language == MFR_LANG_IT && a.step == MFR_NAME);   /* skip after back keeps the picked language, not English */
    }
    /* patch UX13d: the targets of every step are finger size and 8 px apart */
    {
        int b[9][4];
        mfr_back_box(&b[0][0], &b[0][1], &b[0][2], &b[0][3]);
        mfr_skip_box(&b[1][0], &b[1][1], &b[1][2], &b[1][3]);
        CHECK(b[0][1] + b[0][3] <= MFR_HEADER_BOTTOM && b[1][1] + b[1][3] <= MFR_HEADER_BOTTOM);
        for (int i = 0; i < 6; i++) mfr_lang_box(i, &b[2 + i][0], &b[2 + i][1], &b[2 + i][2], &b[2 + i][3]);
        if (check_boxes((const int (*)[4])b, 8)) return 1;              /* language: Back, Skip, six tiles */
        mfr_name_wide_box(&b[2][0], &b[2][1], &b[2][2], &b[2][3]);
        for (int i = 0; i < 6; i++) mfr_name_box(i, &b[3 + i][0], &b[3 + i][1], &b[3 + i][2], &b[3 + i][3]);
        if (check_boxes((const int (*)[4])b, 9)) return 1;              /* name: Back, Skip, StackChan, six names */
        CHECK(b[8][1] + b[8][3] + 8 <= 240);   /* the last name row ends 8 px above the glass edge */
        for (int i = 0; i < 3; i++) mfr_mode_box(i, &b[2 + i][0], &b[2 + i][1], &b[2 + i][2], &b[2 + i][3]);
        if (check_boxes((const int (*)[4])b, 5)) return 1;              /* brain: Back, Skip, three tiles */
        CHECK(b[4][1] + b[4][3] + 8 <= 240);
        mfr_got_box(&b[1][0], &b[1][1], &b[1][2], &b[1][3]);
        if (check_boxes((const int (*)[4])b, 2)) return 1;              /* privacy and the last screen: Back (or nothing) and Got it */
        CHECK(b[1][3] >= 56 && b[1][1] + b[1][3] + 8 <= 240);
    }
    {   /* patch UX19 (decision 34): two equal routes; B opens the three ways, Back returns, A is the hosted answer, Skip never picks A */
        mfr_t m;
        mfr_init(&m, 1, 0);
        CHECK(mfr_choose_language(&m, MFR_LANG_EN) && mfr_choose_name(&m, 0) && m.step == MFR_BRAIN && m.custom == 0);
        CHECK(mfr_open_custom(&m) && m.custom == 1 && m.step == MFR_BRAIN);
        mfr_back(&m);
        CHECK(m.step == MFR_BRAIN && m.custom == 0);   /* Back from the Custom page stays on the step */
        mfr_back(&m);
        CHECK(m.step == MFR_NAME);                     /* a second Back leaves the step */
        CHECK(mfr_choose_name(&m, 0) && mfr_skip(&m) && m.mode != MFR_MODE_HOSTED && m.step == MFR_PRIVACY);   /* Skip takes Home or set-one-up, never the hosted route */
        mfr_init(&m, 1, 0);
        CHECK(mfr_open_custom(&m) == 0);               /* only on the brain step */
        CHECK(mfr_choose_language(&m, MFR_LANG_EN) && mfr_choose_name(&m, 0));
        CHECK(mfr_choose_mode(&m, MFR_MODE_HOSTED) && m.mode == MFR_MODE_HOSTED && m.custom == 0 && m.step == MFR_PRIVACY);
        int r[2][4];
        for (int i = 0; i < 2; i++) mfr_route_box(i, &r[i][0], &r[i][1], &r[i][2], &r[i][3]);
        CHECK(r[0][2] == 304 && r[1][2] == 304 && r[0][3] == r[1][3]);                       /* equal tiles */
        CHECK(r[1][1] - (r[0][1] + r[0][3]) >= 8 && r[0][1] - 52 >= 8 && r[1][1] + r[1][3] <= 224);
    }
    puts("firstrun_core_test: all passed");
    return 0;
}
