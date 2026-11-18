/* Prints the geometry and the pure functions of maipai_banner_core.h as JSON (patch N01), for the settings page preview.
 *   banner_dump table      host/maipai_body/banner_table.json is this output
 *   banner_dump scenarios  inputs and the answers of the core: the parity test feeds the same inputs to the page's JavaScript
 * cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> banner_dump.c */
#include <stdio.h>

#include "maipai_banner_core.h"
#include "maipai_subs_core.h"

static const char* ICONS[MB_ICON_COUNT] = {"none", "remote", "check", "battery", "wifi_off", "bars", "ring", "speech", "key"};
static const char* FLAGS[MB_FLAG_COUNT] = {"mic", "face", "camera", "remote", "battery", "wifi"};

static void table(void)
{
    printf("{\n \"screen_w\": %d,\n \"screen_h\": %d,\n", MB_SCREEN_W, MB_SCREEN_H);
    printf(" \"zones\": {\"banner\": [%d, %d], \"face\": [%d, %d], \"subtitles\": [%d, %d]},\n", MB_ZONE_BANNER_Y0, MB_ZONE_BANNER_Y1, MB_ZONE_FACE_Y0, MB_ZONE_FACE_Y1,
           MB_ZONE_SUB_Y0, MB_ZONE_SUB_Y1);
    printf(" \"row\": {\"x\": %d, \"y\": %d, \"w\": %d, \"h\": %d, \"r\": %d},\n", MB_ROW_X, MB_ROW_Y, MB_ROW_W, MB_ROW_H, MB_ROW_R);
    printf(" \"pad_x\": %d,\n \"icon_w\": %d,\n \"strip\": {\"glyph_w\": %d, \"gap\": %d},\n", MB_PAD_X, MB_ICON_W, MB_STRIP_GLYPH_W, MB_STRIP_GAP);
    printf(" \"fade_ms\": %d,\n \"font_px\": %d,\n \"min_ms\": %u,\n \"max_hold_ms\": %u,\n", MB_FADE_MS, MB_FONT_PX, MB_MIN_MS, MB_MAX_HOLD_MS);
    printf(" \"subtitles\": {\"font_px\": %d, \"lines\": %d, \"pad_y\": %d, \"fade_ms\": %u, \"end_hold_ms\": %u, \"page_per_char_ms\": %u, \"page_min_ms\": %u, \"page_max_ms\": %u},\n",
           MS_FONT_PX, MS_LINES, MS_PAD_Y, MS_FADE_MS, MS_END_HOLD_MS, MS_PAGE_PER_CHAR_MS, MS_PAGE_MIN_MS, MS_PAGE_MAX_MS);
    printf(" \"scroll_px_s\": %d,\n \"scroll_pause_ms\": %u,\n \"text_max\": %d,\n \"icons\": [", MB_SCROLL_PX_S, MB_SCROLL_PAUSE_MS, MB_TEXT_MAX);
    for (int i = 0; i < MB_ICON_COUNT; i++) printf("%s\"%s\"", i ? ", " : "", ICONS[i]);
    printf("],\n \"flags\": [");
    for (int i = 0; i < MB_FLAG_COUNT; i++) printf("%s\"%s\"", i ? ", " : "", FLAGS[i]);
    printf("]\n}\n");
}

static void scenarios(void)
{
    int first = 1;
#define SEP() printf("%s\n", first ? "" : ","), first = 0
    printf("[");
    const int widths[] = {40, 150, 200, 266, 267, 300, 480};
    const int rooms[] = {200, 266};
    for (unsigned a = 0; a < sizeof widths / sizeof widths[0]; a++)
        for (unsigned b = 0; b < 2; b++) {
            SEP();
            printf(" {\"k\": \"fit\", \"w\": %d, \"room\": %d, \"v\": %d}", widths[a], rooms[b], mb_fit(widths[a], rooms[b]));
        }
    for (int overflow = 0; overflow <= 240; overflow += 40)
        for (unsigned t = 0; t <= 9000; t += 250) {
            SEP();
            printf(" {\"k\": \"marquee\", \"overflow\": %d, \"t\": %u, \"v\": %d, \"pass\": %u}", overflow, t, mb_marquee_x(t, overflow), mb_marquee_pass_ms(overflow));
        }
    for (int visible = 0; visible < 2; visible++) {  /* the fade of the row, frame by frame at 33 ms */
        int cur = visible ? 0 : 255;
        SEP();
        printf(" {\"k\": \"fade\", \"visible\": %d, \"opa\": [", visible);
        for (int f = 0; f < 12; f++) {
            cur = mb_fade_step(cur, visible, 33);
            printf("%s%d", f ? ", " : "", cur);
        }
        printf("]}");
    }
    for (int chars = 0; chars <= 120; chars += 15) {
        SEP();
        printf(" {\"k\": \"page_ms\", \"chars\": %d, \"v\": %u}", chars, (unsigned)ms_page_ms(chars));
    }
    for (int lines = 1; lines <= 2; lines++) {
        SEP();
        printf(" {\"k\": \"text_top\", \"lines\": %d, \"line_h\": 23, \"v\": %d}", lines, ms_text_top(lines, 23));
    }
    for (unsigned bits = 0; bits < (1u << MB_FLAG_COUNT); bits++)
        for (int icon = 0; icon < MB_ICON_COUNT; icon += 4) {
            SEP();
            printf(" {\"k\": \"room\", \"bits\": %u, \"icon\": %d, \"strip_w\": %d, \"v\": %d}", bits, icon, mb_strip_w(bits), mb_text_room(bits, icon));
        }
    for (int chars = 0; chars <= 300; chars += 25) {
        SEP();
        printf(" {\"k\": \"caption_hold\", \"chars\": %d, \"v\": %u}", chars, mb_caption_hold(chars));
    }
    for (int level = -1; level <= 100; level += 9)
        for (int ch = 0; ch < 2; ch++)
            for (int mode = 0; mode < 2; mode++)
                for (int blip = 0; blip < 2; blip++) {
                    SEP();
                    printf(" {\"k\": \"battery\", \"level\": %d, \"charging\": %d, \"mode\": %d, \"blip\": %d, \"v\": %d}", level, ch, mode, blip,
                           mb_battery_shown(level, ch, ch, mode, blip));
                }
    for (int w = 0; w < 2; w++)
        for (int h = 0; h < 2; h++)
            for (int mode = 0; mode < 2; mode++) {
                SEP();
                printf(" {\"k\": \"wifi\", \"wifi\": %d, \"hub\": %d, \"mode\": %d, \"v\": %d}", w, h, mode, mb_wifi_shown(w, h, mode));
            }
    printf("\n]\n");
}

int main(int argc, char** argv)
{
    if (argc > 1 && argv[1][0] == 's') scenarios();
    else table();
    return 0;
}
