/* Prints the overlay core's shared table as JSON (what the settings page preview draws from): the names, the layers, the particle
 * caps, the named combinations, the sizes of every element and the palette. host/maipai_body/overlay_table.json must be exactly this
 * output, and the preview's JavaScript (overlay_shapes.py) draws from it, so the preview and the unit show the same sizes and colors.
 * cc -std=c99 -Wall -Wextra -Werror -I<headers> overlay_dump.c -o dump -lm && ./dump > host/maipai_body/overlay_table.json */
#include <stdio.h>
#include <string.h>

#include "maipai_overlay_core.h"

static void hex(uint8_t r, uint8_t g, uint8_t b) { printf("\"#%02x%02x%02x\"", r, g, b); }

int main(void)
{
    printf("{\n  \"screen\": [%d, %d],\n  \"zones\": {\"banner\": %d, \"subtitles\": %d},\n  \"layers\": %d,\n  \"tick_ms\": %u,\n", MO_W, MO_H, MO_ZONE_TOP, MO_ZONE_BOTTOM, MO_LAYERS, MO_TICK_MS);
    /* the names the settings page offers: the 16 single overlays, then the named combinations (moon and sparkles are parts only) */
    printf("  \"names\": [");
    int first = 1;
    for (int i = 1; i < MO_COUNT; i++) {
        if (i == MO_MOON || i == MO_SPARKLES) continue;
        printf("%s\"%s\"", first ? "" : ", ", MO_NAMES[i]);
        first = 0;
    }
    for (int i = 0; i < MOP_COUNT; i++) printf(", \"%s\"", MOP_NAMES[i]);
    printf("],\n  \"parts_only\": [\"%s\", \"%s\"],\n", MO_NAMES[MO_MOON], MO_NAMES[MO_SPARKLES]);
    printf("  \"layer\": {");
    for (int i = 1; i < MO_COUNT; i++) printf("%s\"%s\": %d", i > 1 ? ", " : "", MO_NAMES[i], mo_layer_of(i));
    printf("},\n  \"caps\": {");
    for (int i = 1; i < MO_COUNT; i++) printf("%s\"%s\": [%d, %d, %d]", i > 1 ? ", " : "", MO_NAMES[i], mo_cap(i, 1), mo_cap(i, 2), mo_cap(i, 3));
    printf("},\n  \"presets\": {\n");
    for (int pi = 0; pi < MOP_COUNT; pi++) {
        printf("    \"%s\": [", MOP_NAMES[pi]);
        int n = 0;
        for (int l = 0; l < MO_LAYERS; l++) {
            if (MOP_PARTS[pi][l][0] == 0) continue;
            printf("%s[\"%s\", %d]", n++ ? ", " : "", MO_NAMES[MOP_PARTS[pi][l][0]], MOP_PARTS[pi][l][1]);
        }
        printf("]%s\n", pi + 1 < MOP_COUNT ? "," : "");
    }
    printf("  },\n  \"sizes\": {\n");
    { /* what each element draws, by calling the core's own size functions */
        mo_p_t p;
        int v[8];
        memset(&p, 0, sizeof p);
        v[0] = 3; v[1] = 14; v[2] = 24;
        printf("    \"rain\": {\"width\": %d, \"len\": [%d, %d]},\n", v[0], v[1], v[2]);
        for (int a = 0; a < 4; a++) { p.a = (uint8_t)a; v[a] = mo_snow_d(&p); }
        printf("    \"snow\": [%d, %d, %d, %d],\n", v[0], v[1], v[2], v[3]);
        for (int a = 0; a < 3; a++) { p.a = (uint8_t)a; v[a] = mo_heart_s(&p); }
        printf("    \"hearts\": [%d, %d, %d],\n", v[0], v[1], v[2]);
        memset(&p, 0, sizeof p);
        p.life = 120;
        const int ages[3] = {0, 60, 100};
        for (int k = 0; k < 3; k++) { p.age = (uint16_t)ages[k]; v[k] = mo_zzz_s(&p); }
        printf("    \"zzz\": {\"sizes\": [%d, %d, %d], \"x\": [%d, %d], \"y\": [160, 164], \"rise\": 106},\n", v[0], v[1], v[2], MO_ZZZ_XL, MO_ZZZ_XR);
        printf("    \"confetti\": [");
        for (int ph = 0; ph < 4; ph++) { memset(&p, 0, sizeof p); p.age = (uint16_t)(ph * 4); int w, h; mo_confetti_dims(&p, &w, &h); printf("%s[%d, %d]", ph ? ", " : "", w, h); }
        printf("],\n    \"leaf\": 14,\n    \"stars\": [");
        for (int a = 0; a < 4; a++) { memset(&p, 0, sizeof p); p.a = (uint8_t)a; printf("%s%d", a ? ", " : "", mo_star_r(&p)); }
        printf("],\n    \"sparkles\": [8, 13],\n    \"clouds\": [");
        for (int a = 0; a < 3; a++) { memset(&p, 0, sizeof p); p.a = (uint8_t)a; printf("%s%d", a ? ", " : "", mo_cloud_w(&p)); }
        printf("],\n    \"wind\": [%d, %d],\n", 40, 88);
        printf("    \"sun\": {\"x\": %d, \"y\": %d, \"r\": %d, \"rays\": 16},\n", MO_SUN_CX, MO_SUN_CY, MO_SUN_R);
        printf("    \"moon\": {\"x\": %d, \"y\": %d, \"r\": %d},\n", MO_MOON_CX, MO_MOON_CY, MO_MOON_R);
        printf("    \"fireworks\": {\"radius\": [60, 100], \"sparks\": [16, 20]},\n");
        printf("    \"disco\": {\"ball_r\": 20, \"dots\": [12, 18]}\n");
    }
    printf("  },\n  \"colors\": {\n");
    {
        static const char* const single[MOC_COUNT] = {"rain", "snow", "snow_rim", "wind", "wind2", "leaf_vein", "heart", "heart_edge", "heart_shine", "steam_in", "steam_mid",
                                                      "steam_out", "zzz", "zzz_edge", "rocket", "rocket_head", "burst_flash", "star", "white", "sun", "sun_rim", "sun_ray",
                                                      "sun_glow", "moon", "moon_glow", "fog", "string", "bolt", "bolt_glow", "wash"};
        for (int i = 0; i < MOC_COUNT; i++) {
            printf("    \"%s\": ", single[i]);
            hex(MO_PAL[i][0], MO_PAL[i][1], MO_PAL[i][2]);
            printf(",\n");
        }
#define LIST(name, macro)                          \
    printf("    \"%s\": [", name);                \
    {                                              \
        int n_ = 0;                                \
        const uint8_t tab_[][3] = {macro};         \
        for (size_t k_ = 0; k_ < sizeof tab_ / sizeof tab_[0]; k_++) { printf("%s", n_++ ? ", " : ""); hex(tab_[k_][0], tab_[k_][1], tab_[k_][2]); } \
    }                                              \
    printf("],\n");
#undef X
#define X(r, g, b) {r, g, b},
        LIST("party", MO_X_PARTY)
        LIST("leaf", MO_X_LEAF)
        LIST("sparkle", MO_X_SPARKLE)
        LIST("balloon", MO_X_BALLOON)
        LIST("firework", MO_X_FIREWORK)
        LIST("disco", MO_X_DISCO)
        LIST("cloud_light_back", MO_X_CLOUD_LIGHT_BACK)
        LIST("cloud_light_front", MO_X_CLOUD_LIGHT_FRONT)
        LIST("cloud_dark_back", MO_X_CLOUD_DARK_BACK)
        printf("    \"cloud_dark_front\": [");
        {
            const uint8_t tab_[][3] = {MO_X_CLOUD_DARK_FRONT};
            for (size_t k_ = 0; k_ < sizeof tab_ / sizeof tab_[0]; k_++) { printf("%s", k_ ? ", " : ""); hex(tab_[k_][0], tab_[k_][1], tab_[k_][2]); }
        }
        printf("]\n");
    }
    printf("  }\n}\n");
    return 0;
}
