// The look as the unit draws it: the style table and the emotions of hal/maipai_look_core.h.
#include "render_hooks.h"
#include "maipai_look_core.h"
using namespace stackchan::avatar;
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
    if (c == "think") { std::string n; in >> n; av->setThinking(n == "on"); return true; }
    if (c == "tint") { std::string n; in >> n; av->setEmotionTint(n == "on"); return true; }
    if (c == "colour") { int r, g, b, br = 0, bg = 0, bb = 0; in >> r >> g >> b; if (in >> br >> bg >> bb) {} av->setColors(lv_color_make(r, g, b), lv_color_make(br, bg, bb)); return true; }
    return false;
}
