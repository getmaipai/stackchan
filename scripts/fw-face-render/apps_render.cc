// Host renderer for the Apps wall, the Timers and Alarms apps and the tabbed Settings screen (patch UI16): the real LVGL and the unit's own
// drawing and touch code (maipai_apps.cc) run on this Mac with a scripted stand-in for the unit, and a fake finger drives the real input path.
// Commands, one per line on stdin:
//   lang en|es   clock 12|24   night on|off   banner on|off
//   games N      how many games the unit holds (the first N of the eight in firmware/games)
//   pictures on|off   lockcode on|off   ssid NAME|none   bars N   tail N (-1 off the build, 0 off, 1 joining, 2 up)
//   timer SECONDS LABEL|_    alarm HOUR MINUTE LABEL|_    clearall
//   show apps|games|timers|alarms|settings      snap FILE.png      state
//   tap X Y   swipe X0 Y0 X1 Y1 MS   pump MS    (a finger on the glass; the same events the unit's touch screen makes)
//   tab N (the Settings tab, by a tap on the tab column)   scroll Y (drag the Settings list so it is Y px down)
// Build: bash scripts/fw-face-render/apps_render.sh <firmware tree root> <out dir>
#include <lvgl.h>
#include <zlib.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "maipai_apps.h"
#include "maipai_apps_core.h"

static uint8_t s_buf[320 * 240 * 2];
static uint32_t g_now = 1000;
static uint32_t tick_cb() { return g_now; }
static void flush_cb(lv_display_t* d, const lv_area_t*, uint8_t*) { lv_display_flush_ready(d); }

// the renderer is not a unit: nothing is locked and no game runs
bool maipai_lock_locked() { return false; }

// ---- a scripted finger ----
static lv_indev_state_t g_ptr_state = LV_INDEV_STATE_RELEASED;
static int g_px = 0, g_py = 0;
static void indev_read(lv_indev_t*, lv_indev_data_t* d)
{
    d->state   = g_ptr_state;
    d->point.x = (int32_t)g_px;
    d->point.y = (int32_t)g_py;
}
static void pump(int ms)
{
    for (int i = 0; i < ms; i += 10) {
        g_now += 10;
        lv_timer_handler();
    }
}

static const char* kGameTitles[8] = {"Color Memory", "Reaction Time", "Whack-a-Mole", "Tic-Tac-Toe", "Do It", "Rock Paper Scissors", "Magic 8-Ball", "Dice and Coin"};
static const int kGameBest[8] = {14, 287, 22, 30, 0, 3, 0, 0};

struct Fake : MaipaiPagesHost {
    bool es_ = false, c24 = false, night_ = false, pics = false, code = false, nd = false, icons = false;
    int games = 8, vol = 70, bri = 80, bars = 3, tail = 2, autolock = 5, style = 1;
    std::string ssid = "example-wifi", log;
    std::vector<MaipaiPageTimer> items;
    uint32_t next_id = 1;
    uint32_t now_ms() override { return g_now; }
    bool local_time(struct tm* t) override { memset(t, 0, sizeof(*t)); t->tm_hour = 10; t->tm_min = 24; return true; }
    bool night() override { return night_; }
    bool clock24() override { return c24; }
    bool spanish() override { return es_; }
    int game_count() override { return games; }
    const char* game_title(int i) override { return kGameTitles[i]; }
    int game_best(int i) override { return kGameBest[i]; }
    const char* game_start(int i) override { log += "game" + std::to_string(i) + ";"; return ""; }
    void action(int a) override { log += std::string("action_") + MPG_ACTION_NAMES[a] + ";"; }
    int app_items(int kind, MaipaiPageTimer* out, int max) override
    {
        int n = 0;
        for (auto& t : items) {
            if (t.kind != kind || n >= max) continue;
            out[n] = t;
            if (kind == 1) { out[n].left_s = t.left_s - (int)((g_now - 1000) / 1000); if (out[n].left_s < 0) out[n].left_s = 0; }
            n++;
        }
        return n;
    }
    int active_count() override { return (int)items.size(); }
    void timer_cancel(uint32_t id) override { for (size_t i = 0; i < items.size(); i++) if (items[i].id == id) { items.erase(items.begin() + i); break; } log += "cancel;"; }
    const char* app_timer_add(int s) override
    {
        if (items.size() >= 8) return mac_str(MAC_S_FULL, es_);
        MaipaiPageTimer t = {}; t.id = next_id++; t.kind = 1; t.left_s = s + (int)((g_now - 1000) / 1000); items.push_back(t);
        log += "timer" + std::to_string(s) + ";";
        return "";
    }
    const char* app_alarm_add(int h, int m) override
    {
        if (items.size() >= 8) return mac_str(MAC_S_FULL, es_);
        MaipaiPageTimer t = {}; t.id = next_id++; t.kind = 2; t.hour = (int8_t)h; t.minute = (int8_t)m; items.push_back(t);
        log += "alarm" + std::to_string(h) + ":" + std::to_string(m) + ";";
        return "";
    }
    void open_strip_page(int t) override { log += "strip" + std::to_string(t) + ";"; }
    bool pictures_held() override { return pics; }
    bool lock_available() override { return true; }
    bool lock_has_code() override { return code; }
    bool lock_now() override { log += "lock;"; return code; }
    int auto_lock_minutes() override { return autolock; }
    void set_auto_lock(int m) override { autolock = m; }
    bool night_dim() override { return nd; }
    void set_night_dim(bool v) override { nd = v; }
    bool status_icons() override { return icons; }
    void set_status_icons(bool v) override { icons = v; }
    int volume() override { return vol; }
    void set_volume(int v) override { vol = v; }
    int brightness() override { return bri; }
    void set_brightness(int v) override { bri = v; }
    int wifi_bars() override { return ssid.empty() ? -1 : bars; }
    int tailnet() override { return tail; }
    const char* address() override { return "Settings: 192.0.2.10:8780"; }
    const char* wifi_ssid() override { return ssid.c_str(); }
    void open_wifi() override { log += "wifi;"; }
    int face_style() override { return style; }
    void set_face_style(int s) override { style = s; log += "style" + std::to_string(s) + ";"; }
    const char* host_name() override { return "marlow-unit"; }
    bool version_info(mv_info_t* i) override
    {
        memset(i, 0, sizeof(*i));
        snprintf(i->version, sizeof(i->version), "1.6.2-maipai");
        snprintf(i->slot, sizeof(i->slot), "ota_0");
        i->slot_known = 1; i->update_key = 1; i->image_state = MV_IMG_VALID;
        i->internal_free = 62 * 1024; i->internal_min = 41 * 1024; i->internal_big = 31 * 1024; i->psram_free = 6200 * 1024; i->psram_min = 6100 * 1024;
        return true;
    }
    bool ringing() override { return false; }
    bool game_running() override { return false; }
};
static Fake g_fake;

static lv_color_t fg_cb() { return lv_color_white(); }

static void write_png(const char* path, const std::vector<uint8_t>& rgb, int w, int h)
{
    std::vector<uint8_t> raw;
    for (int y = 0; y < h; y++) {
        raw.push_back(0);
        raw.insert(raw.end(), rgb.begin() + (size_t)y * w * 3, rgb.begin() + (size_t)(y + 1) * w * 3);
    }
    uLongf cl = compressBound(raw.size());
    std::vector<uint8_t> comp(cl);
    compress(comp.data(), &cl, raw.data(), raw.size());
    FILE* f = fopen(path, "wb");
    if (f == nullptr) { printf("cannot write %s\n", path); return; }
    auto be32 = [&](uint32_t v) { uint8_t b[4] = {(uint8_t)(v >> 24), (uint8_t)(v >> 16), (uint8_t)(v >> 8), (uint8_t)v}; fwrite(b, 1, 4, f); };
    auto chunk = [&](const char* t, const uint8_t* d, uint32_t n) {
        be32(n); fwrite(t, 1, 4, f); if (n) fwrite(d, 1, n, f);
        uint32_t c = crc32(0, (const Bytef*)t, 4); if (n) c = crc32(c, d, n); be32(c);
    };
    const uint8_t sig[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    fwrite(sig, 1, 8, f);
    uint8_t ihdr[13] = {(uint8_t)(w >> 24), (uint8_t)(w >> 16), (uint8_t)(w >> 8), (uint8_t)w, (uint8_t)(h >> 24), (uint8_t)(h >> 16), (uint8_t)(h >> 8), (uint8_t)h, 8, 2, 0, 0, 0};
    chunk("IHDR", ihdr, 13);
    chunk("IDAT", comp.data(), (uint32_t)cl);
    chunk("IEND", nullptr, 0);
    fclose(f);
}

static void snap(const char* path, bool banner)
{
    pump(20);
    lv_refr_now(nullptr);
    std::vector<uint8_t> rgb;
    for (int i = 0; i < 320 * 240; i++) {
        const uint16_t v = (uint16_t)(s_buf[i * 2] | (s_buf[i * 2 + 1] << 8));
        rgb.push_back((uint8_t)(((v >> 11) & 31) * 255 / 31));
        rgb.push_back((uint8_t)(((v >> 5) & 63) * 255 / 63));
        rgb.push_back((uint8_t)((v & 31) * 255 / 31));
    }
    if (banner) {
        for (int y = 0; y < 28; y++) for (int x = 0; x < 320; x++) { rgb[((size_t)y * 320 + x) * 3] = 40; rgb[((size_t)y * 320 + x) * 3 + 1] = 40; rgb[((size_t)y * 320 + x) * 3 + 2] = 50; }
        for (int x = 0; x < 320; x++) { rgb[((size_t)224 * 320 + x) * 3] = rgb[((size_t)224 * 320 + x) * 3] / 2 + 60; }  // a faint line at y 224: the end of the zone
    }
    write_png(path, rgb, 320, 240);
    printf("wrote %s\n", path);
}

static void tap(int x, int y)
{
    g_px = x; g_py = y; g_ptr_state = LV_INDEV_STATE_PRESSED; pump(60);
    g_ptr_state = LV_INDEV_STATE_RELEASED; pump(60);
}
static void swipe(int x0, int y0, int x1, int y1, int ms)
{
    g_px = x0; g_py = y0; g_ptr_state = LV_INDEV_STATE_PRESSED; pump(40);
    const int steps = 8;
    for (int i = 1; i <= steps; i++) {
        g_px = x0 + (x1 - x0) * i / steps; g_py = y0 + (y1 - y0) * i / steps;
        pump(ms / steps < 10 ? 10 : ms / steps);
    }
    g_ptr_state = LV_INDEV_STATE_RELEASED; pump(60);
}

int main()
{
    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t* d = lv_display_create(320, 240);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB565);
    lv_display_set_buffers(d, s_buf, nullptr, sizeof(s_buf), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(d, flush_cb);
    lv_obj_set_style_bg_color(lv_screen_active(), lv_color_black(), 0);
    lv_indev_t* in = lv_indev_create();
    lv_indev_set_type(in, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(in, indev_read);
    lv_indev_set_display(in, d);
    maipai_apps_attach(&g_fake, fg_cb);
    bool banner = false;
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream is(line);
        std::string cmd;
        is >> cmd;
        if (cmd == "lang") { std::string l; is >> l; g_fake.es_ = l == "es"; }
        else if (cmd == "clock") { int c; is >> c; g_fake.c24 = c == 24; }
        else if (cmd == "night") { std::string l; is >> l; g_fake.night_ = l == "on"; }
        else if (cmd == "banner") { std::string l; is >> l; banner = l == "on"; }
        else if (cmd == "games") { is >> g_fake.games; }
        else if (cmd == "pictures") { std::string l; is >> l; g_fake.pics = l == "on"; }
        else if (cmd == "lockcode") { std::string l; is >> l; g_fake.code = l == "on"; }
        else if (cmd == "ssid") { std::string l; is >> l; g_fake.ssid = l == "none" ? "" : l; }
        else if (cmd == "bars") { is >> g_fake.bars; }
        else if (cmd == "tail") { is >> g_fake.tail; }
        else if (cmd == "clearall") { g_fake.items.clear(); }
        else if (cmd == "timer") {
            int s; std::string l; is >> s >> l;
            MaipaiPageTimer t = {}; t.id = g_fake.next_id++; t.kind = 1; t.left_s = s + (int)((g_now - 1000) / 1000);
            snprintf(t.label, sizeof(t.label), "%s", l == "_" ? "" : l.c_str());
            g_fake.items.push_back(t);
        } else if (cmd == "alarm") {
            int h, m; std::string l; is >> h >> m >> l;
            MaipaiPageTimer t = {}; t.id = g_fake.next_id++; t.kind = 2; t.hour = (int8_t)h; t.minute = (int8_t)m;
            snprintf(t.label, sizeof(t.label), "%s", l == "_" ? "" : l.c_str());
            g_fake.items.push_back(t);
        } else if (cmd == "show") {
            std::string v; is >> v;
            const int view = v == "apps" ? MAV_APPS : (v == "games" ? MAV_GAMES : (v == "timers" ? MAV_TIMERS : (v == "alarms" ? MAV_ALARMS : MAV_SETTINGS)));
            printf("show %s %d\n", v.c_str(), maipai_apps_show(view) ? 1 : 0);
            pump(30);
        } else if (cmd == "snap") { std::string f; is >> f; snap(f.c_str(), banner); }
        else if (cmd == "tap") { int x, y; is >> x >> y; tap(x, y); }
        else if (cmd == "swipe") { int a, b, c, e, ms; is >> a >> b >> c >> e >> ms; swipe(a, b, c, e, ms); }
        else if (cmd == "pump") { int ms; is >> ms; pump(ms); }
        else if (cmd == "tab") { int t; is >> t; int x, y, w, h; mac_tab_box(t, &x, &y, &w, &h); tap(x + w / 2, y + h / 2); }
        else if (cmd == "scroll") { int y; is >> y; for (int rem = y; rem > 0; rem -= 100) { swipe(200, 214, 200, 214 - (rem > 100 ? 100 : rem), 300); pump(900); } }  // the list keeps gliding after the finger lifts
        else if (cmd == "state") {
            printf("state open %d settings %d log %s\n", maipai_apps_open() ? 1 : 0, maipai_apps_settings_open() ? 1 : 0, g_fake.log.c_str());
            g_fake.log.clear();
        } else if (cmd == "close") { maipai_apps_close(); pump(30); }
    }
    return 0;
}
