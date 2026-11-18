// Spike A: the unit's real face (LVGL plus the default avatar classes) behind a small C API for WebAssembly.
// Intent: draw the face in a browser with no server. The page calls vu_init, then vu_tick(ms) each frame, vu_touch(x, y, type) for the pointer,
// and reads the frame from vu_rgba() (RGBA8888, 320 x 240).
// Placement: host-side development tool. Upstream: none.
#include <lvgl.h>
#include <cstdint>
#include <cstring>
#include <string>
#include <emscripten.h>
#include <stackchan/avatar/skins/default/default.h>
#include "render_hooks.h"
#include "maipai_facefx.h"

using namespace stackchan::avatar;

static const int W = 320, H = 240;
static uint8_t s_buf[W * H * 2];
static uint8_t s_rgba[W * H * 4];
int64_t g_fake_us = 1000000;  // the unit's clock for esp_timer_get_time (the render stub reads it)
#define s_now_us g_fake_us
static DefaultAvatar* s_av = nullptr;
static lv_display_t* s_disp = nullptr;
static int s_tx = 0, s_ty = 0, s_down = 0, s_down_x = 0, s_down_y = 0;
static int s_taps = 0, s_frames = 0, s_emo = 0, s_speak = 0;

static void flush_cb(lv_display_t* d, const lv_area_t*, uint8_t*) { lv_display_flush_ready(d); }
static uint32_t tick_cb() { return (uint32_t)(s_now_us / 1000); }
static void read_cb(lv_indev_t*, lv_indev_data_t* data)
{
    data->point.x = s_tx;
    data->point.y = s_ty;
    data->state = s_down ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
}

static const Emotion kEmotions[] = {Emotion::Neutral, Emotion::Happy, Emotion::Angry, Emotion::Sad, Emotion::Doubt, Emotion::Sleepy, Emotion::Surprised};
static const char* kEmotionNames[] = {"neutral", "happy", "angry", "sad", "doubt", "sleepy", "surprised"};

extern "C" {

EMSCRIPTEN_KEEPALIVE int vu_init()
{
    lv_init();
    lv_tick_set_cb(tick_cb);
    s_disp = lv_display_create(W, H);
    lv_display_set_buffers(s_disp, s_buf, nullptr, sizeof(s_buf), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(s_disp, flush_cb);
    lv_display_set_color_format(s_disp, LV_COLOR_FORMAT_RGB565);
    lv_indev_t* in = lv_indev_create();
    lv_indev_set_type(in, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(in, read_cb);
    lv_obj_t* scr = lv_screen_active();
    lv_obj_set_style_bg_color(scr, lv_color_black(), 0);
    static DefaultAvatar av;
    s_av = &av;
    av.init(scr);
    render_hook_init(s_av, scr);
    maipai_speech_set_active(false);
    return 0;
}

// Advance the fake clock by ms and draw one or more frames (33 ms apart, as the unit's face task runs).
EMSCRIPTEN_KEEPALIVE int vu_tick(int ms)
{
    int n = 0;
    for (int t = 0; t < ms || n == 0; t += 33) {
        s_now_us += 33333;
        if (s_speak > 0) maipai_speech_feed_bench(s_speak);
        s_av->update();
        render_hook_frame(s_av);
        lv_timer_handler();
        n++;
        s_frames++;
    }
    return n;
}

// type: 0 down, 1 move, 2 up. A short press that stays within 12 px is a tap: the face looks at it and the next emotion plays.
EMSCRIPTEN_KEEPALIVE void vu_touch(int x, int y, int type)
{
    s_tx = x; s_ty = y;
    if (type == 0) { s_down = 1; s_down_x = x; s_down_y = y; }
    else if (type == 2) {
        s_down = 0;
        int dx = x - s_down_x, dy = y - s_down_y;
        if (dx * dx + dy * dy < 144) {
            s_taps++;
            s_emo = (s_emo + 1) % (int)(sizeof(kEmotions) / sizeof(kEmotions[0]));
            s_av->setEmotion(kEmotions[s_emo]);
            s_av->leftEye().setPosition(uitk::Vector2i((x - W / 2) / 8, (y - H / 2) / 8));
            s_av->rightEye().setPosition(uitk::Vector2i((x - W / 2) / 8, (y - H / 2) / 8));
        }
    }
    lv_indev_read(lv_indev_get_next(nullptr));
}

EMSCRIPTEN_KEEPALIVE void vu_set_emotion(int i)
{
    if (i < 0 || i >= (int)(sizeof(kEmotions) / sizeof(kEmotions[0]))) return;
    s_emo = i;
    s_av->setEmotion(kEmotions[i]);
}
EMSCRIPTEN_KEEPALIVE const char* vu_emotion_name() { return kEmotionNames[s_emo]; }
EMSCRIPTEN_KEEPALIVE void vu_speak(int level) { s_speak = level; maipai_speech_set_active(level > 0); }
EMSCRIPTEN_KEEPALIVE int vu_taps() { return s_taps; }
EMSCRIPTEN_KEEPALIVE int vu_frames() { return s_frames; }
EMSCRIPTEN_KEEPALIVE int vu_width() { return W; }
EMSCRIPTEN_KEEPALIVE int vu_height() { return H; }
EMSCRIPTEN_KEEPALIVE int vu_fb_size() { return W * H * 2; }
EMSCRIPTEN_KEEPALIVE const uint8_t* vu_fb() { return s_buf; }

// The frame as RGBA8888 for a canvas ImageData.
EMSCRIPTEN_KEEPALIVE const uint8_t* vu_rgba()
{
    for (int i = 0; i < W * H; i++) {
        const uint16_t v = s_buf[i * 2] | (s_buf[i * 2 + 1] << 8);
        s_rgba[i * 4] = ((v >> 11) & 31) * 255 / 31;
        s_rgba[i * 4 + 1] = ((v >> 5) & 63) * 255 / 63;
        s_rgba[i * 4 + 2] = (v & 31) * 255 / 31;
        s_rgba[i * 4 + 3] = 255;
    }
    return s_rgba;
}

}  // extern "C"
