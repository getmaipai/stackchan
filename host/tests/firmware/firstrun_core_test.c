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
    CHECK(mfr_choose_mode(&m, 7) == 0 && m.step == MFR_BRAIN);
    CHECK(mfr_choose_mode(&m, MFR_MODE_HOME));
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
    puts("firstrun_core_test: all passed");
    return 0;
}
