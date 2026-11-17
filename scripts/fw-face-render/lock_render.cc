// Host renderer for the passcode lock (patch LK02): the real LVGL and the unit's own drawing code (maipai_lock_draw.h) draw the lock screen and the
// keypad into memory, so they can be looked at without flashing the unit. Commands, one per line on stdin:
//   lang en|es          the language of the words
//   lock FILE.png       the lock screen: a black glass with the padlock (the sleeping face is drawn by the unit's face code, not here)
//   pad N W FILE.png    the keypad with N digits typed; W 1 shows the wrong-code line
//   banner on|off       draw a gray strip where the banner row (y 0 to 28) stays on the unit
// Build: bash scripts/fw-face-render/lock_render.sh <firmware tree root> <out dir>
#include <lvgl.h>
#include <zlib.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "maipai_lock_draw.h"

static uint8_t s_buf[320 * 240 * 2];
static uint32_t tick_cb() { return 1000; }
static void flush_cb(lv_display_t* d, const lv_area_t*, uint8_t*) { lv_display_flush_ready(d); }

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
    if (f == nullptr) {
        printf("cannot write %s\n", path);
        return;
    }
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
    }
    write_png(path, rgb, 320, 240);
    printf("wrote %s\n", path);
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
    bool es = false, banner = false;
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream in(line);
        std::string cmd;
        in >> cmd;
        lv_obj_t* root = lv_obj_create(lv_layer_top());
        lv_obj_remove_style_all(root);
        lv_obj_set_size(root, 320, 240);
        lv_obj_set_pos(root, 0, 0);
        if (cmd == "lang") {
            std::string l;
            in >> l;
            es = l == "es";
        } else if (cmd == "banner") {
            std::string l;
            in >> l;
            banner = l == "on";
        } else if (cmd == "lock") {
            std::string f;
            in >> f;
            mlkd::build_padlock(root);
            snap(f.c_str(), banner);
        } else if (cmd == "pad") {
            int n, w;
            std::string f;
            in >> n >> w >> f;
            mlkd::Pad pad;
            mlkd::build_pad(root, &pad, es, nullptr);
            mlkd::refresh_pad(&pad, n, w != 0, es);
            snap(f.c_str(), banner);
        }
        lv_obj_delete(root);
    }
    return 0;
}
