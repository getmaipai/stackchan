#pragma once
#include <stackchan/avatar/skins/default/default.h>
#include <sstream>
#include <string>
// Hooks the face under test fills in (the new look code), so render.cc stays the same across edits.
void render_hook_init(stackchan::avatar::DefaultAvatar* av, lv_obj_t* scr);
void render_hook_frame(stackchan::avatar::DefaultAvatar* av);
stackchan::avatar::Emotion render_hook_emotion(const std::string& name);
bool render_hook_cmd(stackchan::avatar::DefaultAvatar* av, const std::string& c, std::istringstream& in);
