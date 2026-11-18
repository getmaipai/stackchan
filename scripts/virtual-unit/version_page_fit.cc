// Measures the version page of the More screen (patches U05, NX02, SF69) with the real LVGL layout: the same root (padding 8, top 58, row gap 6, wrapping flex), the same labels and fonts
// as maipai_more.cc build_version(), the detail lines of maipai_version_core.h and the notice of docs/legal/affiliation.json. Prints each label's box and whether the content fits above
// the bottom edge of the 240 px panel. Placement: host-side development tool. Upstream: none.
#include <lvgl.h>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <unistd.h>
#include <string>
extern const lv_font_t font_noto_sans_basic_16_4;
#define font_noto16 font_noto_sans_basic_16_4
static uint8_t buf[320 * 240 * 2];
static void flush(lv_display_t* d, const lv_area_t*, uint8_t*) { lv_display_flush_ready(d); }
static uint32_t tick() { return 1000; }
static lv_obj_t* label(lv_obj_t* p, const char* t, const lv_font_t* f) { lv_obj_t* l = lv_label_create(p); lv_obj_set_style_text_font(l, f, 0); lv_label_set_text(l, t); return l; }
int main(int argc, char** argv)
{
    lv_init();
    lv_tick_set_cb(tick);
    lv_display_t* d = lv_display_create(320, 240);
    lv_display_set_buffers(d, buf, nullptr, sizeof(buf), LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(d, flush);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB565);
    lv_obj_t* root = lv_obj_create(lv_layer_top());
    lv_obj_set_size(root, lv_pct(100), lv_pct(100));
    lv_obj_set_style_border_width(root, 0, 0);
    lv_obj_set_style_radius(root, 0, 0);
    lv_obj_set_style_pad_all(root, 8, 0);
    lv_obj_set_style_pad_top(root, 58, 0);
    lv_obj_set_style_pad_row(root, 6, 0);
    lv_obj_set_style_pad_column(root, 6, 0);
    lv_obj_remove_flag(root, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_flex_flow(root, LV_FLEX_FLOW_ROW_WRAP);
    lv_obj_set_flex_align(root, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_START);
    const char* rows[6] = {"Version: v1.0.0-b52+7", "Tag: v1.0.0", "Image: signed", "Slot: ota_0", "Memory free: 68 KB (lowest 32 KB)", "Large memory free: 7340 KB (lowest 7100 KB)"};
    const int nrows = argc > 2 ? atoi(argv[2]) : 6;                                   // how many detail lines to keep (the first ones)
    const lv_font_t* body = argc > 3 && strcmp(argv[3], "16") == 0 ? &font_noto16 : &lv_font_montserrat_14;   // the font of the detail lines and the notice
    const char* notice = argc > 1 && argv[1][0] ? argv[1] : "Independent project. Not affiliated with or endorsed by M5Stack or the original StackChan creators.";
    lv_obj_t* title = label(root, "MaiPai for StackChan", &lv_font_montserrat_20);
    lv_obj_set_width(title, LV_PCT(100));
    lv_obj_add_flag(title, LV_OBJ_FLAG_FLEX_IN_NEW_TRACK);
    lv_obj_t* all[8];
    all[0] = title;
    for (int i = 1; i < 8; i++) all[i] = nullptr;
    for (int i = 0; i < nrows; i++) {
        lv_obj_t* l = label(root, rows[i], body);
        lv_obj_set_width(l, LV_PCT(100));
        lv_label_set_long_mode(l, LV_LABEL_LONG_WRAP);
        lv_obj_add_flag(l, LV_OBJ_FLAG_FLEX_IN_NEW_TRACK);
        all[1 + i] = l;   // detail lines
    }
    lv_obj_t* n = label(root, notice, body);
    lv_obj_set_width(n, LV_PCT(100));
    lv_label_set_long_mode(n, LV_LABEL_LONG_WRAP);
    lv_obj_add_flag(n, LV_OBJ_FLAG_FLEX_IN_NEW_TRACK);
    all[7] = n;
    lv_obj_update_layout(root);
    int bottom = 0;
    for (int i = 0; i < 8; i++) {
        if (all[i] == nullptr) continue;
        lv_area_t a;
        lv_obj_get_coords(all[i], &a);
        printf("%s y %d..%d (h %d) font line %d\n", i == 0 ? "title" : (i == 7 ? "notice" : "detail"), (int)a.y1, (int)a.y2, (int)(a.y2 - a.y1 + 1), (int)lv_font_get_line_height(lv_obj_get_style_text_font(all[i], LV_PART_MAIN)));
        bottom = a.y2 > bottom ? a.y2 : bottom;
    }
    printf("content bottom %d of 239: %s by %d px\n", bottom, bottom <= 239 ? "fits" : "OVERFLOWS", bottom <= 239 ? 239 - bottom : bottom - 239);
    fflush(stdout);
    _exit(0);
}
