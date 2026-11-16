/* Host test for the listening cues (patch TB01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header> ... -lm. */
#include <stdio.h>
#include <string.h>
#include "maipai_listen_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static int maxc(tl_rgb_t c) { return c.r > c.g ? (c.r > c.b ? c.r : c.b) : (c.g > c.b ? c.g : c.b); }

int main(void)
{
    tl_prefs_t p;
    tl_prefs_default(&p);

    /* The defaults are the host's (unit_prefs.py): chime, normal, face on, cyan 40c0ff. */
    CHECK(p.sound == TL_SOUND_CHIME && p.light == TL_LIGHT_NORMAL && p.face == 1);
    CHECK(p.r == 0x40 && p.g == 0xc0 && p.b == 0xff);

    /* Parsing: only the allowed words and "#rrggbb" count; anything else leaves the value alone. */
    uint8_t v = 9, r = 1, g = 2, b = 3;
    CHECK(tl_parse_sound("mm", &v) && v == TL_SOUND_MM);
    CHECK(tl_parse_sound("off", &v) && v == TL_SOUND_OFF);
    CHECK(!tl_parse_sound("loud", &v) && v == TL_SOUND_OFF);
    CHECK(!tl_parse_sound(NULL, &v));
    CHECK(tl_parse_light("dim", &v) && v == TL_LIGHT_DIM);
    CHECK(!tl_parse_light("bright", &v) && v == TL_LIGHT_DIM);
    CHECK(tl_parse_colour("#40C0ff", &r, &g, &b) && r == 0x40 && g == 0xc0 && b == 0xff);
    CHECK(!tl_parse_colour("40c0ff", &r, &g, &b) && !tl_parse_colour("#40c0f", &r, &g, &b) && !tl_parse_colour("#40c0fg", &r, &g, &b));
    CHECK(!tl_parse_colour("#40c0ff00", &r, &g, &b) && !tl_parse_colour(NULL, &r, &g, &b) && r == 0x40);

    /* Rules. Mute: sound off, light and face kept. */
    tl_env_t e = {0, 0, 0, 1};
    tl_effective_t x = tl_effective(&p, &e);
    CHECK(x.sound == TL_SOUND_CHIME && x.light == TL_LIGHT_NORMAL && x.face == 1);
    e.muted = 1;
    x = tl_effective(&p, &e);
    CHECK(x.sound == TL_SOUND_OFF && x.light == TL_LIGHT_NORMAL && x.face == 1);
    /* The sound policy says no (sounds off in the page): sound off, the rest stays. */
    e.muted = 0;
    e.sound_ok = 0;
    x = tl_effective(&p, &e);
    CHECK(x.sound == TL_SOUND_OFF && x.light == TL_LIGHT_NORMAL);
    /* Quiet hours: the light is at most dim; a light that was off stays off. */
    e.sound_ok = 1;
    e.quiet_hrs = 1;
    x = tl_effective(&p, &e);
    CHECK(x.light == TL_LIGHT_DIM && x.sound == TL_SOUND_CHIME);
    p.light = TL_LIGHT_OFF;
    CHECK(tl_effective(&p, &e).light == TL_LIGHT_OFF);
    p.light = TL_LIGHT_NORMAL;
    /* Full quiet: no sound, no light, no face cue. */
    e.full_quiet = 1;
    x = tl_effective(&p, &e);
    CHECK(x.sound == TL_SOUND_OFF && x.light == TL_LIGHT_OFF && x.face == 0);
    /* All three off is a plain notice on the page, nothing else. */
    p.sound = TL_SOUND_OFF; p.light = TL_LIGHT_OFF; p.face = 0;
    CHECK(tl_all_off(&p));
    p.face = 1;
    CHECK(!tl_all_off(&p));
    tl_prefs_default(&p);

    /* The state-to-colour table. Idle and light off: dark. */
    CHECK(!tl_frame(TL_ST_OFF, 0, 0, &p, TL_LIGHT_NORMAL).lit);
    CHECK(!tl_frame(TL_ST_LISTEN, 500, 0, &p, TL_LIGHT_OFF).lit);

    /* Listening breathes: darkest at the start of a breath, brightest half way, same colour family as the setting. */
    const tl_rgb_t l0 = tl_frame(TL_ST_LISTEN, 0, 0, &p, TL_LIGHT_NORMAL);
    const tl_rgb_t l1 = tl_frame(TL_ST_LISTEN, TL_BREATH_MS / 2, 0, &p, TL_LIGHT_NORMAL);
    CHECK(l0.lit && l1.lit && maxc(l1) > maxc(l0));
    CHECK(maxc(l1) <= TL_PEAK_NORMAL && maxc(l1) >= TL_PEAK_NORMAL - 3);
    CHECK(maxc(l0) >= 15 && maxc(l0) <= 25); /* the floor of a breath is visible, not off */
    CHECK(l1.b > l1.g && l1.g > l1.r); /* cyan stays cyan: blue over green over red */
    int monotone_up = 1, last = -1;
    for (uint32_t t = 0; t <= TL_BREATH_MS / 2; t += 80) {
        const int m = maxc(tl_frame(TL_ST_LISTEN, t, 0, &p, TL_LIGHT_NORMAL));
        if (m < last) monotone_up = 0;
        last = m;
    }
    CHECK(monotone_up);
    /* The breath repeats. */
    CHECK(maxc(tl_frame(TL_ST_LISTEN, 700, 0, &p, TL_LIGHT_NORMAL)) == maxc(tl_frame(TL_ST_LISTEN, 700 + TL_BREATH_MS, 0, &p, TL_LIGHT_NORMAL)));
    /* Dim is a third of normal at the same moment. */
    const int dim = maxc(tl_frame(TL_ST_LISTEN, TL_BREATH_MS / 2, 0, &p, TL_LIGHT_DIM));
    CHECK(dim <= TL_PEAK_DIM && dim >= TL_PEAK_DIM - 2 && dim * 2 < maxc(l1));
    /* Brighter while it hears speech, never past the cap, never past the dim cap in dim. */
    const tl_rgb_t hear = tl_frame(TL_ST_LISTEN, 400, 1, &p, TL_LIGHT_NORMAL);
    const tl_rgb_t quiet = tl_frame(TL_ST_LISTEN, 400, 0, &p, TL_LIGHT_NORMAL);
    CHECK(maxc(hear) > maxc(quiet) && maxc(hear) <= TL_PEAK_MAX_NORMAL);
    CHECK(maxc(tl_frame(TL_ST_LISTEN, TL_BREATH_MS / 2, 1, &p, TL_LIGHT_NORMAL)) == TL_PEAK_MAX_NORMAL || maxc(tl_frame(TL_ST_LISTEN, TL_BREATH_MS / 2, 1, &p, TL_LIGHT_NORMAL)) == TL_PEAK_MAX_NORMAL - 1);
    CHECK(maxc(tl_frame(TL_ST_LISTEN, TL_BREATH_MS / 2, 1, &p, TL_LIGHT_DIM)) <= TL_PEAK_DIM);

    /* Heard: a quick double blink (on, off, on, off), then the thinking pulse. */
    CHECK(tl_frame(TL_ST_HEARD, 0, 0, &p, TL_LIGHT_NORMAL).lit);
    CHECK(!tl_frame(TL_ST_HEARD, TL_BLINK_MS, 0, &p, TL_LIGHT_NORMAL).lit);
    CHECK(tl_frame(TL_ST_HEARD, 2 * TL_BLINK_MS, 0, &p, TL_LIGHT_NORMAL).lit);
    CHECK(!tl_frame(TL_ST_HEARD, 3 * TL_BLINK_MS, 0, &p, TL_LIGHT_NORMAL).lit);
    CHECK(tl_frame(TL_ST_HEARD, TL_HEARD_MS + 10, 0, &p, TL_LIGHT_NORMAL).lit); /* now thinking */
    CHECK(tl_frame(TL_ST_HEARD, TL_HEARD_MS + 10, 0, &p, TL_LIGHT_NORMAL).r == tl_frame(TL_ST_THINK, 10, 0, &p, TL_LIGHT_NORMAL).r);

    /* Thinking: a different colour from listening, and a different rhythm. */
    const tl_rgb_t th = tl_frame(TL_ST_THINK, TL_THINK_MS / 2, 0, &p, TL_LIGHT_NORMAL);
    CHECK(th.lit && (th.r != l1.r || th.g != l1.g || th.b != l1.b));
    CHECK(th.g > th.r && th.g > th.b); /* cyan 40c0ff rotates to c0ff40: green leads */
    CHECK(TL_THINK_MS != TL_BREATH_MS);
    CHECK(maxc(th) < maxc(l1)); /* quieter than a breath's peak */
    uint8_t tr, tg, tb;
    tl_think_colour(0x40, 0xc0, 0xff, &tr, &tg, &tb);
    CHECK(tr == 0xc0 && tg == 0xff && tb == 0x40);

    /* Speaking: steady and dim, the same at every moment. */
    const tl_rgb_t s0 = tl_frame(TL_ST_SPEAK, 0, 0, &p, TL_LIGHT_NORMAL);
    const tl_rgb_t s1 = tl_frame(TL_ST_SPEAK, 1234, 0, &p, TL_LIGHT_NORMAL);
    CHECK(s0.lit && s0.r == s1.r && s0.g == s1.g && s0.b == s1.b);
    CHECK(maxc(s0) < maxc(l1) / 3 && maxc(s0) >= 8);

    /* Every state at every 30 ms for 20 s stays inside the peak and never wraps a channel. */
    for (int st = TL_ST_OFF; st < TL_ST_COUNT; st++) {
        for (uint32_t t = 0; t < 20000; t += 30) {
            for (int hearing = 0; hearing < 2; hearing++) {
                const tl_rgb_t c = tl_frame((tl_state_t)st, t, hearing, &p, TL_LIGHT_NORMAL);
                CHECK(maxc(c) <= TL_PEAK_MAX_NORMAL);
                CHECK(c.lit == ((c.r | c.g | c.b) != 0));
            }
        }
    }
    /* A white or black setting never gets brighter than the peak. A black light is dark, not an error. */
    tl_prefs_t w = p;
    w.r = w.g = w.b = 255;
    CHECK(maxc(tl_frame(TL_ST_LISTEN, TL_BREATH_MS / 2, 1, &w, TL_LIGHT_NORMAL)) <= TL_PEAK_MAX_NORMAL);
    w.r = w.g = w.b = 0;
    CHECK(!tl_frame(TL_ST_LISTEN, TL_BREATH_MS / 2, 0, &w, TL_LIGHT_NORMAL).lit);

    /* The "mm": the right length, a real signal, soft ends, never clipping, deterministic. */
    static int16_t a[TL_MM_SAMPLES], c[TL_MM_SAMPLES];
    CHECK(tl_render_mm(a, TL_MM_SAMPLES) == TL_MM_SAMPLES);
    CHECK(tl_render_mm(c, TL_MM_SAMPLES) == TL_MM_SAMPLES && memcmp(a, c, sizeof(a)) == 0);
    CHECK(tl_render_mm(a, 100) == 100); /* a small buffer is filled, not overrun */
    tl_render_mm(a, TL_MM_SAMPLES);
    int peak = 0;
    double sum = 0;
    for (int i = 0; i < TL_MM_SAMPLES; i++) {
        const int m = a[i] < 0 ? -a[i] : a[i];
        if (m > peak) peak = m;
        sum += (double)a[i] * a[i];
    }
    const double rms = sqrt(sum / TL_MM_SAMPLES);
    CHECK(peak > 1500 && peak < 24000); /* audible, and no bark */
    CHECK(rms > 400 && rms < 9000);
    CHECK(abs(a[0]) < 40 && abs(a[TL_MM_SAMPLES - 1]) < 40); /* starts and ends at silence: no click */
    int step = 0;
    for (int i = 1; i < TL_MM_SAMPLES; i++) {
        const int d = a[i] - a[i - 1];
        if ((d < 0 ? -d : d) > step) step = d < 0 ? -d : d;
    }
    CHECK(step < 6000); /* no jump from one sample to the next */
    CHECK(TL_MM_SAMPLES * 2 <= 16384); /* the preloaded buffer is at most 16 KB */

    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
