#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "maipai_sounds_core.h"

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)

static int decisions(void) {
    ms_policy_t p; ms_policy_default(&p);
    CHECK(ms_sound_from_name(NULL) == -1);
    for (int i = 0; i < MS_SND_COUNT; ++i) CHECK(ms_sound_from_name(MS_SOUND_NAMES[i]) == i);
    CHECK(ms_sound_from_name("bogus") == -1);
    CHECK(ms_sound_is_asset(0) && ms_sound_is_asset(6) && !ms_sound_is_asset(7) && !ms_sound_is_asset(-1));
    CHECK(ms_in_window(1320, 420, 1380) && ms_in_window(1320, 420, 0));
    CHECK(!ms_in_window(1320, 420, 420) && !ms_in_window(10, 10, 10) && !ms_in_window(-1, 10, 0));
    p.quiet_from=1320; p.quiet_to=420; p.dark=1;
    CHECK(ms_is_night(&p, 30, 0) && ms_is_night(&p, -1, 1) && !ms_is_night(&p, 600, 0));
    CHECK(ms_night_ok(MS_SND_SHUTTER,0) && ms_night_ok(MS_SND_GOODBYE,0) && ms_night_ok(MS_SND_LOW_BATTERY,0));
    CHECK(ms_night_ok(MS_SND_EXCLAMATION,0) && ms_night_ok(MS_SND_POPUP,0) && ms_night_ok(MS_SND_VIBRATION,0));
    CHECK(ms_night_ok(MS_SND_NEEDS_YOU,1) && !ms_night_ok(MS_SND_NEEDS_YOU,0) && !ms_night_ok(MS_SND_PLUG_IN,1));
    CHECK(ms_safety(MS_SND_SHUTTER,0) && ms_safety(MS_SND_NEEDS_YOU,1) && !ms_safety(MS_SND_NEEDS_YOU,0));
    CHECK(ms_decide(&p,-1,0,0,0)==MS_NO_SUCH_SOUND);
    p.muted=1; CHECK(ms_decide(&p,MS_SND_POPUP,0,1,0)==MS_MUTED);
    CHECK(ms_decide(&p,MS_SND_POPUP,0,1,MS_BYPASS_FIND)==MS_OK);
    CHECK(ms_decide(&p,MS_SND_POPUP,0,1,1)==MS_MUTED);
    p.muted=0; p.enabled=0;
    CHECK(ms_decide(&p,MS_SND_PLUG_IN,0,0,0)==MS_DISABLED);
    CHECK(ms_decide(&p,MS_SND_SHUTTER,0,0,0)==MS_OK && ms_decide(&p,MS_SND_NEEDS_YOU,1,0,0)==MS_OK);
    CHECK(ms_decide(&p,MS_SND_NEEDS_YOU,0,0,0)==MS_DISABLED);
    p.enabled=1;
    CHECK(ms_decide(&p,MS_SND_PLUG_IN,0,1,0)==MS_NIGHT);
    CHECK(ms_decide(&p,MS_SND_SHUTTER,0,1,0)==MS_OK);
    CHECK(ms_decide(&p,MS_SND_PLUG_IN,0,1,1)==MS_OK);
    p.night_ok=1; CHECK(ms_decide(&p,MS_SND_PLUG_IN,0,1,0)==MS_OK);
    CHECK(strcmp(ms_reason_word(MS_MUTED),"muted")==0 && strcmp(ms_reason_word((ms_reason_t)99),"unknown")==0);
    return 0;
}
static int power(void) {
    ms_power_t p; ms_power_init(&p);
    CHECK(ms_power_update(&p,1,1)==MS_PWR_NONE);
    CHECK(ms_power_update(&p,0,0)==MS_PWR_NONE); CHECK(ms_power_update(&p,1,1)==MS_PWR_NONE);
    CHECK(ms_power_update(&p,0,0)==MS_PWR_NONE); CHECK(ms_power_update(&p,1,1)==MS_PWR_NONE);
    CHECK(ms_power_update(&p,1,1)==MS_PWR_NONE);
    CHECK(ms_power_update(&p,0,0)==MS_PWR_NONE); CHECK(ms_power_update(&p,0,0)==MS_PWR_NONE);
    CHECK(ms_power_update(&p,0,0)==MS_PWR_UNPLUG);
    CHECK(ms_power_update(&p,1,1)==MS_PWR_NONE); CHECK(ms_power_update(&p,1,1)==MS_PWR_NONE);
    CHECK(ms_power_update(&p,1,1)==MS_PWR_PLUG);
    CHECK(ms_power_update(&p,1,0)==MS_PWR_NONE); CHECK(ms_power_update(&p,1,0)==MS_PWR_NONE);
    CHECK(ms_power_update(&p,1,0)==MS_PWR_FULL);
    return 0;
}
static int link_and_phrases(uint32_t base) {
    ms_link_t l; ms_link_init(&l);
    CHECK(ms_link_state(&l,base,1,0)==MS_LINK_CONNECTING);
    CHECK(ms_link_state(&l,base,0,0)==MS_LINK_NO_WIFI && ms_link_state(&l,base,1,1)==MS_LINK_UP);
    ms_link_down(&l,base); CHECK(ms_link_state(&l,base+MS_OFFLINE_AFTER_MS-1,1,0)==MS_LINK_CONNECTING);
    CHECK(ms_link_state(&l,base+MS_OFFLINE_AFTER_MS,1,0)==MS_LINK_NO_HOST);
    ms_link_hello_failed(&l); CHECK(ms_link_state(&l,base,1,0)==MS_LINK_CONNECTING);
    ms_link_hello_failed(&l); CHECK(ms_link_state(&l,base,1,0)==MS_LINK_REFUSED);
    ms_link_mark_offline(&l); ms_link_return_t r=ms_link_up(&l,base+MS_BACK_CLIP_AFTER_MS);
    CHECK(r.back_online && r.back_clip && r.outage_ms==MS_BACK_CLIP_AFTER_MS && !l.down && l.hello_fails==0);
    ms_link_down(&l,base); r=ms_link_up(&l,base+1000); CHECK(!r.back_online && !r.back_clip && r.outage_ms==1000);
    CHECK(ms_group_for_link(MS_LINK_NO_WIFI)==MS_GRP_NO_WIFI && ms_group_for_link(MS_LINK_NO_HOST)==MS_GRP_NO_HOST);
    CHECK(ms_group_for_link(MS_LINK_REFUSED)==MS_GRP_REFUSED && ms_group_for_link(MS_LINK_CONNECTING)==MS_GRP_CONNECTING);
    CHECK(ms_group_for_link(MS_LINK_UP)==-1);
    char buf[64]; CHECK(ms_phrase_file(buf,sizeof(buf),MS_GRP_BACK,1) && strcmp(buf,"ph_back_2.ogg")==0);
    CHECK(!ms_phrase_file(buf,sizeof(buf),MS_GRP_BACK,2) && !ms_phrase_file(buf,sizeof(buf),-1,0));
    ms_phrases_t ph; ms_phrases_init(&ph);
    ms_phrase_t q=ms_phrase_pick(&ph,MS_LINK_NO_WIFI,base,0,0,-1);
    CHECK(q.kind==MS_PH_CLIP && q.group==MS_GRP_NO_WIFI && q.variant==0);
    q=ms_phrase_pick(&ph,MS_LINK_NO_WIFI,base+9999u,0,0,-1); CHECK(q.kind==MS_PH_TONE);
    q=ms_phrase_pick(&ph,MS_LINK_NO_WIFI,base+10000u,1,0,-1); CHECK(q.kind==MS_PH_TONE);
    q=ms_phrase_pick(&ph,MS_LINK_NO_WIFI,base+10000u,0,1,-1); CHECK(q.kind==MS_PH_NONE);
    q=ms_phrase_pick(&ph,MS_LINK_NO_WIFI,base+10000u,0,0,-1); CHECK(q.kind==MS_PH_CLIP && q.variant==1);
    q=ms_phrase_pick(&ph,MS_LINK_NO_HOST,base+20000,0,0,-1); CHECK(q.kind==MS_PH_CLIP && q.variant==0);
    q=ms_phrase_pick(&ph,MS_LINK_NO_HOST,base+30000,0,0,-1); CHECK(q.kind==MS_PH_TONE);
    q=ms_phrase_pick(&ph,MS_LINK_UP,base+40000,0,0,MS_GRP_BACK); CHECK(q.kind==MS_PH_TONE);
    q=ms_phrase_pick(&ph,MS_LINK_UP,base+60000,0,0,MS_GRP_BACK); CHECK(q.kind==MS_PH_CLIP && q.group==MS_GRP_BACK);
    CHECK(ms_phrases_limited(&ph,base+60000));
    return 0;
}
int main(void) {
    CHECK(decisions()==0); CHECK(power()==0); CHECK(link_and_phrases(0)==0); CHECK(link_and_phrases(0x90000000u)==0);
    puts("sounds core ok"); return 0;
}
