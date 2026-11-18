// The look as the unit draws it: the style table and the emotions of hal/maipai_look_core.h.
#include "render_hooks.h"
#include <esp_timer.h>
#include "maipai_look_core.h"
using namespace stackchan::avatar;
extern "C" volatile int g_msp_off;  // patch V23: 1 draws shape lists, 0 the pictures
void render_hook_init(DefaultAvatar*, lv_obj_t*) {}
void render_hook_frame(DefaultAvatar*) {}
Emotion render_hook_emotion(const std::string& n)
{
    static const char* names[] = {"neutral", "happy", "angry", "sad", "doubt", "sleepy", "surprised", "tired", "closing", "sleeping", "love", "content"};
    for (int i = 0; i < 12; i++) if (n == names[i]) return static_cast<Emotion>(i);
    return Emotion::Neutral;
}
bool render_hook_cmd(DefaultAvatar* av, const std::string& c, std::istringstream& in)
{
    if (c == "style") {
        std::string n; in >> n;
        for (int i = 0; i < ML_STYLE_COUNT; i++) if (n == ML_STYLES[i].name) av->setLook(i);
        return true;
    }
    if (c == "eyepose") {  // eyepose DEG LID: both eyes at a tilt (the right eye mirrors the left) and a lid percent, as the emotions ask
        int deg, lid; in >> deg >> lid;
        av->leftEye().setRotation(deg * 10); av->rightEye().setRotation(-deg * 10);
        av->leftEye().setWeight(lid); av->rightEye().setWeight(lid);
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
        av->setEmotion(e);
        av->mouth().setWeight(grin);
        return true;
    }
    if (c == "gaze") { int x, y; in >> x >> y; av->leftEye().setPosition(uitk::Vector2i(x, y)); av->rightEye().setPosition(uitk::Vector2i(x, y)); return true; }  // gaze X Y: eyes look (patch MD02)
    if (c == "sprite") { std::string n; in >> n; g_msp_off = (n == "off") ? 1 : 0; return true; }  // sprite on|off: pictures or shape lists (patch V23)
    if (c == "think") { std::string n; in >> n; av->setThinking(n == "on"); return true; }
    if (c == "tint") { std::string n; in >> n; av->setEmotionTint(n == "on"); return true; }
    if (c == "colour") { int r, g, b, br = 0, bg = 0, bb = 0; in >> r >> g >> b; if (in >> br >> bg >> bb) {} av->setColors(lv_color_make(r, g, b), lv_color_make(br, bg, bb)); return true; }
    return false;
}
