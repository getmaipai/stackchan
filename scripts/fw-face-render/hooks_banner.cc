// The look as the unit draws it, plus the banner row (patch N01): the style table, the emotions, and these commands:
//   bpost PRIO ICON TAG HOLD_MS text...   (PRIO privacy|notice|caption; ICON none|remote|check|battery|wifioff|bars|ring|speech|key;
//                                          TAG none|caption|volume|say|cue|find|link|game; HOLD 0 = until cleared)
//   bstatus LEVEL CHARGING WIFI_UP HUB_UP MIC | bbar hidden|always (the gauges the unit polls; the strip decides what shows)
//   bclear TAG | bsession on|off [label] | bflag mic|camera|remote|battery|wifi on|off [HOLD_MS] | bcaps off|subtitles|banner | ssay TEXT | send | sstop | bvis
#include "render_hooks.h"
#include "maipai_look_core.h"
#include "maipai_banner.h"
#include <cstdio>
using namespace stackchan::avatar;
extern "C" { volatile int g_md_legacy = 0; }  // the dirty-rectangle switch of patch V20 (bench only on the unit)
static DefaultAvatar* g_face = nullptr;
static maipai_banner_status_t g_status;
static int g_bar = MB_BAR_HIDDEN;
static void poll_cb(maipai_banner_status_t* st) { *st = g_status; }
static lv_color_t fg_cb() { return g_face != nullptr ? g_face->shownColor() : lv_color_white(); }
void render_hook_init(DefaultAvatar* av, lv_obj_t*)
{
    g_face = av;
    maipai_banner_attach(fg_cb, poll_cb);
    maipai_banner_set_captions(MB_CAP_SUBTITLES);
}
void render_hook_frame(DefaultAvatar*) { maipai_banner_step(); }
Emotion render_hook_emotion(const std::string& n)
{
    static const char* names[] = {"neutral", "happy", "angry", "sad", "doubt", "sleepy", "surprised", "tired", "closing", "sleeping", "love", "content"};
    for (int i = 0; i < 12; i++) if (n == names[i]) return static_cast<Emotion>(i);
    return Emotion::Neutral;
}
static int pick(const std::string& n, const char* const* names, int count)
{
    for (int i = 0; i < count; i++) if (n == names[i]) return i;
    return 0;
}
bool render_hook_cmd(DefaultAvatar* av, const std::string& c, std::istringstream& in)
{
    static const char* const prios[] = {"privacy", "notice", "caption"};
    static const char* const icons[] = {"none", "remote", "check", "battery", "wifioff", "bars", "ring", "speech", "key"};
    static const char* const tags[] = {"none", "caption", "volume", "say", "cue", "find", "link", "game"};
    static const char* const flags[] = {"mic", "camera", "remote", "battery", "wifi"};
    if (c == "style") {
        std::string n; in >> n;
        for (int i = 0; i < ML_STYLE_COUNT; i++) if (n == ML_STYLES[i].name) av->setLook(i);
        return true;
    }
    if (c == "think") { std::string n; in >> n; av->setThinking(n == "on"); return true; }
    if (c == "tint") { std::string n; in >> n; av->setEmotionTint(n == "on"); return true; }
    if (c == "colour") { int r, g, b, br = 0, bg = 0, bb = 0; in >> r >> g >> b; if (in >> br >> bg >> bb) {} av->setColors(lv_color_make(r, g, b), lv_color_make(br, bg, bb)); return true; }
    if (c == "bpost") {
        std::string p, i, t, rest; unsigned hold = 0;
        in >> p >> i >> t >> hold;
        std::getline(in, rest);
        if (!rest.empty() && rest[0] == ' ') rest.erase(0, 1);
        maipai_banner_post(rest.c_str(), pick(i, icons, 9), pick(p, prios, 3), pick(t, tags, 8), hold);
        return true;
    }
    if (c == "bclear") { std::string t; in >> t; maipai_banner_clear_tag(pick(t, tags, 8)); return true; }
    if (c == "bsession") { std::string o, l; in >> o; std::getline(in, l); if (!l.empty() && l[0] == ' ') l.erase(0, 1); maipai_banner_session(o == "on", l.c_str()); return true; }
    if (c == "bflag") { std::string f, o; unsigned hold = 0; in >> f >> o >> hold; maipai_banner_flag(pick(f, flags, 5), o == "on", hold); return true; }
    if (c == "bcaps") { std::string m; in >> m; maipai_banner_set_captions(m == "off" ? MB_CAP_OFF : (m == "banner" ? MB_CAP_BANNER : MB_CAP_SUBTITLES)); return true; }
    if (c == "ssay") { std::string rest; std::getline(in, rest); if (!rest.empty() && rest[0] == ' ') rest.erase(0, 1); maipai_subtitles_say(rest.c_str(), false); return true; }
    if (c == "send") { maipai_subtitles_end(); return true; }
    if (c == "sstop") { maipai_subtitles_stop(); return true; }
    if (c == "bstatus") {
        int lvl, ch, w, h, m; in >> lvl >> ch >> w >> h >> m;
        g_status.battery_level = lvl; g_status.charging = ch; g_status.on_cable = ch; g_status.wifi_up = w; g_status.wifi_bars = w ? 3 : 0; g_status.hub_up = h; g_status.mic_live = m;
        maipai_banner_set_bar_mode(g_bar);  // forces a fresh read at the next step
        return true;
    }
    if (c == "bbar") { std::string m; in >> m; g_bar = m == "always" ? MB_BAR_ALWAYS : MB_BAR_HIDDEN; maipai_banner_set_bar_mode(g_bar); return true; }
    if (c == "zonecheck") {  // zonecheck is answered by the renderer itself (it reads the picture): nothing here
        return false;
    }
    if (c == "bvis") { printf("banner %d subtitles %d\n", maipai_banner_visible() ? 1 : 0, maipai_subtitles_visible() ? 1 : 0); return true; }
    return false;
}
