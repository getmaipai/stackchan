// The look as the unit draws it, plus the banner row (patch N01): the style table, the emotions, and these commands:
//   bpost PRIO ICON TAG HOLD_MS text...   (PRIO privacy|notice|caption; ICON none|remote|check|battery|wifioff|bars|ring|speech|key;
//                                          TAG none|caption|volume|say|cue|find|link|game; HOLD 0 = until cleared)
//   bstatus LEVEL CHARGING WIFI_UP HUB_UP MIC | bwifiscreen on|off (a Wi-Fi screen is up: no strip glyph, patch WF01) | bbar hidden|always (the gauges the unit polls; the strip decides what shows)
//   bclear TAG | bsession on|off [label] | bflag mic|face|camera|remote|battery|wifi on|off [HOLD_MS] | bcaps off|subtitles|banner | ssay TEXT | send | sstop | bvis
#include "render_hooks.h"
#if __has_include("maipai_firstrun.h")
#include "maipai_firstrun.h"
#define MAIPAI_HAVE_FIRSTRUN 1
#endif
#include <esp_timer.h>
#include "maipai_look_core.h"
#include "maipai_banner.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <functional>
#ifdef MAIPAI_PAGES_RENDER
#include "maipai_pages.h"
#include "maipai_more.h"
extern int64_t g_fake_us;
// A stand-in for the unit: fixed numbers and a few scripted answers, so every page and the sheet can be drawn and judged.
struct FakeHost : MaipaiPagesHost {
    int hh = 10, mm = 24, ss = 36;
    bool night_ = false, c24 = false, ring = false, es_ = false, quiet_ = false, muted_ = false, light = true;
    int vol = 70, bri = 80, bars = 3, bat = 82, tail = 2, frames = 0;
    bool charging = false;
    std::string addr = "192.0.2.10:8780";
    mpg_tiles_t tl;
    uint32_t tile_age = 0;
    MaipaiPageTimer tm[4];
    int ntm = 0;
    int polls = 0;
    std::string log;
    uint32_t now_ms() override { return (uint32_t)(g_fake_us / 1000); }
    bool local_time(struct tm* t) override {
        const int total = hh * 3600 + mm * 60 + ss + (int)(g_fake_us / 1000000) - 1;
        memset(t, 0, sizeof(*t));
        t->tm_hour = (total / 3600) % 24; t->tm_min = (total / 60) % 60; t->tm_sec = total % 60;
        t->tm_wday = 2; t->tm_mday = 17; t->tm_mon = 10;
        return true;
    }
    bool night() override { return night_; }
    bool clock24() override { return c24; }
    bool clock_ring() override { return ring; }
    bool spanish() override { return es_; }
    bool quiet() override { return quiet_; }
    bool muted() override { return muted_; }
    int timers(MaipaiPageTimer* out, int max) override {
        int n = ntm < max ? ntm : max;
        for (int i = 0; i < n; i++) { out[i] = tm[i]; out[i].left_s = tm[i].left_s - (int)(g_fake_us / 1000000) + 1; if (out[i].left_s < 0) out[i].left_s = 0; }
        return n;
    }
    void timer_cancel(uint32_t id) override { for (int i = 0; i < ntm; i++) if (tm[i].id == id) { for (int k = i; k + 1 < ntm; k++) tm[k] = tm[k + 1]; ntm--; break; } log += "cancel;"; }
    void timer_add(int s, const char* l) override { if (ntm < 4) { tm[ntm].id = 100 + ntm; tm[ntm].left_s = s + (int)(g_fake_us / 1000000) - 1; snprintf(tm[ntm].label, sizeof(tm[ntm].label), "%s", l); ntm++; } }
    int game_count() override { return 8; }  // patch UI15: eight games, the page is a grid with a More tile
    const char* game_title(int i) override { static const char* n[8] = {"Color Memory", "Whack-a-Mole", "Tic-Tac-Toe", "Do It", "Rock Paper Scissors", "Magic 8 Ball", "Dice and Coin", "Reaction Time"}; return n[i]; }
    const char* game_id(int i) override { static const char* n[8] = {"memory", "whack", "tictactoe", "bopit", "rps", "eightball", "dice", "reaction"}; return n[i]; }
    int game_best(int i) override { static const int b[8] = {14, 287, 22, 30, 0, 3, 0, 0}; return b[i]; }
    const char* game_start(int i) override { log += "game" + std::to_string(i) + ";"; return ""; }
    void action(int a) override { log += std::string("action_") + MPG_ACTION_NAMES[a] + ";"; }
    const mpg_tiles_t* tiles(uint32_t* age) override { *age = tile_age; return tl.n ? &tl : nullptr; }
    int frame_count() override { return frames; }
    uint8_t* frame_alloc() override { return (uint8_t*)malloc(320 * 240 * 2); }
    void frame_free(uint8_t* p) override { free(p); }
    bool frame_request(int i, uint8_t* dst) override {
        for (int y = 0; y < 240; y++) for (int x = 0; x < 320; x++) {
            const int r = (x * 255 / 319 + i * 60) % 256, g = (y * 255 / 239), b = 180 - (x + y) / 4 + i * 20;
            uint16_t v = (uint16_t)(((r >> 3) << 11) | ((g >> 2) << 5) | ((b & 255) >> 3));
            dst[(y * 320 + x) * 2] = v & 255; dst[(y * 320 + x) * 2 + 1] = v >> 8;
        }
        polls = 0;
        return true;
    }
    int frame_poll() override { return ++polls >= 1 ? 1 : 0; }
    int volume() override { return vol; }
    void set_volume(int v) override { vol = v; }
    int brightness() override { return bri; }
    void set_brightness(int v) override { bri = v; }
    bool light_on() override { return light; }
    void toggle_light() override { light = !light; }
    void toggle_mute() override { muted_ = !muted_; }
    void toggle_quiet() override { quiet_ = !quiet_; }
    int wifi_bars() override { return bars; }
    int battery_pct(bool* c) override { *c = charging; return bat; }
    int tailnet() override { return tail; }
    const char* address() override { return addr.c_str(); }
    void open_more() override { log += "more;"; }
    int style_ = 1; bool icons_ = false, pics_ = false;
    int face_style() override { return style_; }
    void set_face_style(int v) override { style_ = v; log += "style;"; }
    bool pictures_held() override { return pics_; }
    bool status_icons() override { return icons_; }
    void set_status_icons(bool v) override { icons_ = v; log += "icons;"; }
    void stop_all() override { log += "stop;"; }
    void volume_step(int d) override { vol += d; log += "volume;"; }
    void bump() override { log += "bump;"; }
};
static FakeHost g_pages_host;
// The renderer is not a unit: nothing is locked and no game runs (patches LK03 and GM01 call these from the pages and the subtitles).
#include "maipai_lock.h"
#include "maipai_games.h"
#if CONFIG_MAIPAI_LOCK
bool maipai_lock_locked() { return false; }
#endif
#if CONFIG_MAIPAI_GAMES
bool maipai_games_active() { return false; }
#endif
#endif
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
#ifdef MAIPAI_PAGES_RENDER
    maipai_pages_attach(&g_pages_host, fg_cb);
#endif
}
void render_hook_frame(DefaultAvatar*)
{
    maipai_banner_step();
#ifdef MAIPAI_PAGES_RENDER
    maipai_pages_step();
#endif
}
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
    static const char* const flags[] = {"mic", "face", "camera", "remote", "battery", "wifi"};
#ifdef MAIPAI_PAGES_RENDER
    // pages: pcfg TEXT | pshow NAME|face|sheet | pswipe X0 Y0 X1 Y1 MS | pset KEY VALUE | ptile ICON LABEL VALUE | ptimer SECONDS LABEL | pstate | pevent NAME
    if (c == "pcfg") { std::string t; std::getline(in, t); if (!t.empty() && t[0] == ' ') t.erase(0, 1); mpg_cfg_t cfg; const int ok = mpg_cfg_from_text(&cfg, t.c_str()); maipai_pages_set_config(cfg); printf("pcfg %d\n", ok); return true; }
    if (c == "pshow") { std::string n; in >> n; int t = n == "face" ? -1 : (n == "sheet" ? -2 : (n == "settings" ? -3 : mpg_page_by_name(n.c_str()))); printf("pshow %s %d\n", n.c_str(), maipai_pages_show(t) ? 1 : 0); return true; }
    if (c == "pswipe") {
        int x0, y0, x1, y1, ms; in >> x0 >> y0 >> x1 >> y1 >> ms;
        maipai_pages_touch_down(x0, y0, 0);
        g_fake_us += (int64_t)ms * 1000;
        const bool used = maipai_pages_touch_up(x1, y1);
        printf("pswipe consumed %d open %d pos %d sheet %d log %s\n", used ? 1 : 0, maipai_pages_open() ? 1 : 0, maipai_pages_position(), maipai_pages_sheet_open() ? 1 : 0, g_pages_host.log.c_str());
        g_pages_host.log.clear();
        return true;
    }
    if (c == "pset") {
        std::string k; in >> k; std::string v; in >> v; FakeHost& h = g_pages_host; const int n = atoi(v.c_str()); const bool b = v == "on" || v == "1";
        if (k == "night") h.night_ = b; else if (k == "c24") h.c24 = b; else if (k == "ring") h.ring = b; else if (k == "es") h.es_ = b;
        else if (k == "style") h.style_ = n; else if (k == "icons") h.icons_ = b; else if (k == "pics") h.pics_ = b; else if (k == "quiet") h.quiet_ = b; else if (k == "mute") h.muted_ = b; else if (k == "light") h.light = b;
        else if (k == "vol") h.vol = n; else if (k == "bri") h.bri = n; else if (k == "bars") h.bars = n; else if (k == "bat") h.bat = n;
        else if (k == "charging") h.charging = b; else if (k == "tail") h.tail = n; else if (k == "frames") h.frames = n; else if (k == "age") h.tile_age = (uint32_t)n;
        else if (k == "addr") h.addr = v; else if (k == "hh") h.hh = n; else if (k == "mm") h.mm = n;
        return true;
    }
    if (c == "ptile") { std::string i, l, v; in >> i >> l >> v; if (l == "_") l = ""; if (v == "_") v = ""; for (auto& ch : l) if (ch == '~') ch = ' '; for (auto& ch : v) if (ch == '~') ch = ' '; printf("ptile %d\n", mpg_tiles_add(&g_pages_host.tl, i.c_str(), l.c_str(), v.c_str())); return true; }
    if (c == "ptiles_clear") { mpg_tiles_clear(&g_pages_host.tl); return true; }
    if (c == "ptimer") { int sec; std::string l; in >> sec >> l; if (l == "_") l = ""; for (auto& ch : l) if (ch == '~') ch = ' '; g_pages_host.timer_add(sec, l.c_str()); return true; }
    if (c == "pevent") { std::string n; in >> n; maipai_pages_event(n == "wake" ? MGS_EV_WAKE : (n == "speech" ? MGS_EV_SPEECH : MGS_EV_HEAD_TAP)); return true; }
    if (c == "pclick") {  // patch UI13: a click on whatever clickable object the top layer has at X Y (a page's own buttons)
        int x, y;
        in >> x >> y;
        lv_point_t pt = {x, y};
        lv_obj_t* o = lv_indev_search_obj(lv_layer_top(), &pt);
        printf("pclick %d %d %s\n", x, y, o != nullptr ? "hit" : "nothing");
        if (o != nullptr) lv_obj_send_event(o, LV_EVENT_CLICKED, nullptr);
        return true;
    }
    if (c == "pcount") {  // objects under the top layer now (the banner and subtitles hold some), for the cost table
        std::function<int(lv_obj_t*)> count = [&](lv_obj_t* o) { int n = 0; for (uint32_t i = 0; i < lv_obj_get_child_count(o); i++) n += 1 + count(lv_obj_get_child(o, i)); return n; };
        std::string label; in >> label;
        printf("pcount %s %d\n", label.c_str(), count(lv_layer_top()));
        return true;
    }
    if (c == "pscrollby") {  // pscrollby X Y DY: scrolls the nearest scrollable object under X Y by DY pixels (content moves up for a positive DY), as a drag would (patch UX13 tests and scenarios)
        int x, y, dy;
        in >> x >> y >> dy;
        lv_point_t pt = {x, y};
        lv_obj_t* o = lv_indev_search_obj(lv_layer_top(), &pt);
        while (o != nullptr && !lv_obj_has_flag(o, LV_OBJ_FLAG_SCROLLABLE)) o = lv_obj_get_parent(o);
        if (o != nullptr) {   // never past the ends, as a drag cannot go
            const int room = dy > 0 ? (int)lv_obj_get_scroll_bottom(o) : -(int)lv_obj_get_scroll_top(o);
            if ((dy > 0 && dy > room) || (dy < 0 && dy < room)) dy = room;
            lv_obj_scroll_by(o, 0, -dy, LV_ANIM_OFF);
        }
        printf("pscrollby %s %d\n", o != nullptr ? "done" : "nothing", o != nullptr ? (int)lv_obj_get_scroll_y(o) : 0);
        return true;
    }
    if (c == "more") {  // more open | more lang en|es | more games N: the More screen (menu, time zone, network test, version, games), opened on the top layer; pages are reached by pclick
        std::string k; in >> k;
        extern int g_more_lang, g_more_games;
        if (k == "lang") { std::string l; in >> l; g_more_lang = l == "es" ? 1 : 0; }
        else if (k == "games") { in >> g_more_games; }
        else if (k == "open") { maipai_more_open(); }
        return true;
    }
    if (c == "ptargets") {  // every visible clickable object and every visible label of the top layer and the screen: x1 y1 x2 y2 (a click area includes the extended one) and the text, for the screen audit
        std::function<void(lv_obj_t*, bool, bool)> walk = [&](lv_obj_t* o, bool hidden, bool scr) {
            const bool h = hidden || lv_obj_has_flag(o, LV_OBJ_FLAG_HIDDEN);
            const bool sc = scr || lv_obj_get_scroll_bottom(o) > 0 || lv_obj_get_scroll_top(o) > 0 || lv_obj_get_scroll_right(o) > 0 || lv_obj_get_scroll_left(o) > 0;   // an ancestor (or this) scrolls
            if (!h) {
                lv_area_t a;
                if (lv_obj_has_flag(o, LV_OBJ_FLAG_CLICKABLE)) {
                    lv_obj_get_click_area(o, &a);
                    lv_area_t own;
                    lv_obj_get_coords(o, &own);
                    printf("ptarget %d %d %d %d own %d %d %d %d scroll %d\n", (int)a.x1, (int)a.y1, (int)a.x2, (int)a.y2, (int)own.x1, (int)own.y1, (int)own.x2, (int)own.y2, sc ? 1 : 0);
                }
                if (lv_obj_check_type(o, &lv_label_class)) {
                    lv_obj_get_coords(o, &a);
                    const lv_font_t* f = lv_obj_get_style_text_font(o, LV_PART_MAIN);
                    const char* t = lv_label_get_text(o);
                    std::string txt = t != nullptr ? t : "";
                    for (auto& ch : txt) if (ch == '\n' || ch == ' ') ch = '~';
                    printf("ptext %d %d %d %d %d scroll %d %s\n", (int)a.x1, (int)a.y1, (int)a.x2, (int)a.y2, f != nullptr ? (int)f->line_height : 0, sc ? 1 : 0, txt.c_str());
                }
            }
            for (uint32_t i = 0; i < lv_obj_get_child_count(o); i++) walk(lv_obj_get_child(o, i), h, sc);
        };
        walk(lv_layer_top(), false, false);
        walk(lv_screen_active(), false, false);
        printf("ptargets done\n");
        return true;
    }
    if (c == "pstate") { printf("pstate open %d pos %d sheet %d log %s\n", maipai_pages_open() ? 1 : 0, maipai_pages_position(), maipai_pages_sheet_open() ? 1 : 0, g_pages_host.log.c_str()); return true; }
#endif
    if (c == "style") {
        std::string n; in >> n;
        for (int i = 0; i < ML_STYLE_COUNT; i++) if (n == ML_STYLES[i].name) av->setLook(i);
        return true;
    }
    if (c == "face") {  // face NAME: the dance faces as the display's SetEmotion makes them (patch MD02): an emotion plus accents
        std::string n; in >> n;
        g_ml_wink_until_ms = 0; g_ml_shut_eyes = false; g_ml_tongue = false;
        const uint32_t now = static_cast<uint32_t>(esp_timer_get_time() / 1000);
        int grin = 0;
        Emotion e = Emotion::Happy;
        if (n == "laughing" || n == "joy") grin = 85;
        else if (n == "winking" || n == "wink") g_ml_wink_until_ms = now + 900;
        else if (n == "silly") { g_ml_wink_until_ms = now + 900; g_ml_tongue = true; }
        else if (n == "serene") g_ml_shut_eyes = true;
        else if (n == "excited") { e = Emotion::Surprised; grin = 60; }
        else if (n == "surprised") e = Emotion::Surprised;
        else if (n == "love") e = Emotion::Love;
        else if (n == "content") e = Emotion::Content;
        else if (n == "neutral") e = Emotion::Neutral;
        av->setEmotion(e);
        av->mouth().setWeight(grin);
        return true;
    }
    if (c == "gaze") { int x, y; in >> x >> y; av->leftEye().setPosition(uitk::Vector2i(x, y)); av->rightEye().setPosition(uitk::Vector2i(x, y)); return true; }  // gaze X Y: both eyes look (patch MD02)
    if (c == "think") { std::string n; in >> n; av->setThinking(n == "on"); return true; }
#ifdef MAIPAI_HAVE_FIRSTRUN
    if (c == "frun") {  // frun start | frun step N LANG MODE | frun wifi: the first-run flow (patches UX05a, UX05b), on the unit's own drawing code
        std::string a; in >> a;
        static const maipai_firstrun_host_t host = {[]() { return false; }, []() { return false; }, [](int) {}, []() {}, [](int l, int n, int m) { printf("firstrun finished %d %d %d\n", l, n, m); fflush(stdout); }};
        if (a == "start") { maipai_firstrun_init(&host); maipai_firstrun_start(); }
        else if (a == "step") { int st = 0, l = 0, m = -1; in >> st >> l >> m; maipai_firstrun_show_step(st, l, m); }
        else if (a == "wifi") { maipai_firstrun_wifi_done(); }
        else if (a == "close") { maipai_firstrun_close(); }
        return true;
    }
#endif
    if (c == "seal") {  // seal on|off: mute, as ApplyPrivacyFace does it (patch 105): the mouth becomes a flat closed line
        std::string n; in >> n;
        if (auto* m = dynamic_cast<DefaultMouth*>(&av->mouth())) m->setSealed(n == "on");
        return true;
    }
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
    if (c == "bwifiscreen") { std::string o; in >> o; maipai_banner_wifi_screen(o == "on"); return true; }  // patch WF01: a Wi-Fi screen is up
    if (c == "bflag") { std::string f, o; unsigned hold = 0; in >> f >> o >> hold; maipai_banner_flag(pick(f, flags, 6), o == "on", hold); return true; }
    if (c == "bsicons") { std::string o; in >> o; maipai_banner_set_status_icons(o == "on"); return true; }  // patch UI04: the status icons setting
    if (c == "bst") { int k; in >> k; maipai_banner_status(k, false); return true; }                          // a state: 0 heard, 1 listening, 2 thinking
    if (c == "bstc") { maipai_banner_status_clear(); return true; }
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
