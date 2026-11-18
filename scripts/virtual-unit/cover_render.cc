// Host renderer for the full-screen link covers: Wi-Fi connecting, Wi-Fi setup needed, connecting to Home, waiting for Home to approve.
// The drawing code is the unit's own: cover_gen.py cuts it out of stackchan_display.cc into the three .inc files included below.
// Commands on stdin: show RING GLYPH TEXT... | hide | advance MS | ring | snap FILE.png
//   (ring 1 blue blink, 2 cyan blink; glyph 0 bars cycling, 1 slashed bars, 2 slash and key; the unit calls ShowBootCover with these pairs)
// Not shared with the unit: the display base class, the banner (maipai_banner_wifi_screen is a no-op here) and ApplyLink (empty here).
// Placement: host-side development tool. Upstream: none.
#include <lvgl.h>
#include <zlib.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

extern const lv_font_t font_noto_sans_basic_20_4;
#define BUILTIN_TEXT_FONT font_noto_sans_basic_20_4

static uint8_t s_buf[320 * 240 * 2];
static uint32_t g_ms = 1000;
static uint32_t tick_cb() { return g_ms; }
static void flush_cb(lv_display_t* d, const lv_area_t*, uint8_t*) { lv_display_flush_ready(d); }

struct FakeHal {
    int ring[12][3] = {};
    uint32_t millis() { return g_ms; }
    void setRgbColor(int i, int r, int g, int b) { ring[i][0] = r; ring[i][1] = g; ring[i][2] = b; }
    void refreshRgb() {}
};
static FakeHal g_hal;
static FakeHal& GetHAL() { return g_hal; }
static void maipai_banner_wifi_screen(bool) {}
namespace hal_bridge { static void leds_offline(bool) {} }

#include "cover_helpers.inc"

class StackChanAvatarDisplay {
public:
    lv_obj_t* boot_cover_ = nullptr;
    lv_obj_t* boot_label_ = nullptr;
    lv_timer_t* boot_ring_timer_ = nullptr;
    bool boot_done_ = false;
    uint32_t boot_ring_start_ms_ = 0;
    int boot_ring_kind_ = 0;
    bool boot_ring_last_on_ = false;
    int cover_glyph_kind_ = 0;
    LinkGlyph* cover_glyph_ = nullptr;
    LinkGlyph* strip_glyph_ = nullptr;
    lv_timer_t* link_timer_ = nullptr;
    int link_look_ = 0;
    int link_step_ = 0;
    void build()
    {
#include "cover_ctor.inc"
    }
    void ShowBootCover(const char* text, int ring_kind, int glyph_kind = 0);
    void HideBootCover();
    void SetCoverGlyph(int kind);
    void UpdateLinkTimer();
    void ApplyLink() {}
    static void BootRingTick(lv_timer_t* timer);
    static void LinkTick(lv_timer_t* timer);
};
#include "cover_funcs.inc"

static void write_png(const char* path, const std::vector<uint8_t>& rgb)
{
    const int w = 320, h = 240;
    std::vector<uint8_t> raw;
    for (int y = 0; y < h; y++) { raw.push_back(0); raw.insert(raw.end(), rgb.begin() + (size_t)y * w * 3, rgb.begin() + (size_t)(y + 1) * w * 3); }
    uLongf cl = compressBound(raw.size());
    std::vector<uint8_t> comp(cl);
    compress(comp.data(), &cl, raw.data(), raw.size());
    FILE* f = fopen(path, "wb");
    if (!f) { printf("cannot write %s\n", path); return; }
    auto be32 = [&](uint32_t v) { uint8_t b[4] = {(uint8_t)(v >> 24), (uint8_t)(v >> 16), (uint8_t)(v >> 8), (uint8_t)v}; fwrite(b, 1, 4, f); };
    auto chunk = [&](const char* t, const uint8_t* d, uint32_t n) { be32(n); fwrite(t, 1, 4, f); if (n) fwrite(d, 1, n, f); uint32_t c = crc32(0, (const Bytef*)t, 4); if (n) c = crc32(c, d, n); be32(c); };
    const uint8_t sig[8] = {137, 80, 78, 71, 13, 10, 26, 10};
    fwrite(sig, 1, 8, f);
    uint8_t ihdr[13] = {0, 0, 1, 64, 0, 0, 0, 240, 8, 2, 0, 0, 0};
    chunk("IHDR", ihdr, 13); chunk("IDAT", comp.data(), (uint32_t)cl); chunk("IEND", nullptr, 0);
    fclose(f);
}

int main()
{
    lv_init();
    lv_tick_set_cb(tick_cb);
    lv_display_t* d = lv_display_create(320, 240);
    lv_display_set_buffers(d, s_buf, nullptr, sizeof(s_buf), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(d, flush_cb);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB565);
    lv_obj_set_style_bg_color(lv_screen_active(), lv_color_black(), 0);
    static StackChanAvatarDisplay disp;
    disp.build();
    disp.HideBootCover();  // the unit's first face before any cover
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream in(line);
        std::string c;
        in >> c;
        if (c == "show") {
            int ring, glyph; in >> ring >> glyph;
            std::string text; std::getline(in, text);
            if (!text.empty() && text[0] == ' ') text.erase(0, 1);
            std::string t;
            for (size_t i = 0; i < text.size(); i++) t += (text[i] == '\\' && i + 1 < text.size() && text[i + 1] == 'n') ? (i++, '\n') : text[i];
            disp.ShowBootCover(t.c_str(), ring, glyph);
        } else if (c == "hide") {
            disp.HideBootCover();
        } else if (c == "advance") {
            int ms; in >> ms;
            for (int t = 0; t < ms; t += 50) { g_ms += 50; lv_timer_handler(); }
        } else if (c == "ring") {
            printf("ring %d %d %d\n", g_hal.ring[0][0], g_hal.ring[0][1], g_hal.ring[0][2]);
        } else if (c == "snap") {
            std::string f; in >> f;
            lv_refr_now(nullptr);
            std::vector<uint8_t> rgb;
            for (int i = 0; i < 320 * 240; i++) {
                const uint16_t v = (uint16_t)(s_buf[i * 2] | (s_buf[i * 2 + 1] << 8));
                rgb.push_back((uint8_t)(((v >> 11) & 31) * 255 / 31)); rgb.push_back((uint8_t)(((v >> 5) & 63) * 255 / 63)); rgb.push_back((uint8_t)((v & 31) * 255 / 31));
            }
            write_png(f.c_str(), rgb);
        }
    }
    fflush(stdout);
    _exit(0);
}
