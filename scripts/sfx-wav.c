/* Writes every game clip of the unit's sound core (maipai_games_sfx_core.h) as a 16-bit mono 16 kHz WAV, rendered by the unit's own code, so the real sounds can be auditioned
 * on a computer. Usage: sfx-wav OUTDIR   (compile with -I<firmware main/hal dir>; scripts/sfx-wav.sh does it).
 * Placement: host-side development tool; no firmware change. Upstream: none. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "maipai_games_sfx_core.h"

static void put32(uint8_t* p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }
static void put16(uint8_t* p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }

int main(int argc, char** argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: sfx-wav OUTDIR. Give the folder the WAV files are written to.\n");
        return 2;
    }
    static int16_t pcm[MGS_SFX_MAX_SAMPLES];
    for (int c = 0; c < MGS_CLIPS; c++) {
        const size_t n = mgs_render(c, pcm, MGS_SFX_MAX_SAMPLES);
        if (n == 0) {
            fprintf(stderr, "clip %s did not render. The sound core and this tool must come from the same firmware tree.\n", MGS_CLIP[c].name);
            return 1;
        }
        char path[512];
        snprintf(path, sizeof(path), "%s/%02d_%s.wav", argv[1], c, MGS_CLIP[c].name);
        FILE* f = fopen(path, "wb");
        if (f == NULL) {
            fprintf(stderr, "Could not write %s. Check that the folder exists.\n", path);
            return 1;
        }
        uint8_t h[44];
        memcpy(h, "RIFF\0\0\0\0WAVEfmt \x10\0\0\0\x01\0\x01\0\0\0\0\0\0\0\0\0\x02\0\x10\0data\0\0\0\0", 44);
        put32(h + 4, (uint32_t)(36 + n * 2));
        put32(h + 24, MGS_SFX_RATE);
        put32(h + 28, MGS_SFX_RATE * 2);
        put16(h + 32, 2);
        put32(h + 40, (uint32_t)(n * 2));
        fwrite(h, 1, 44, f);
        for (size_t i = 0; i < n; i++) {
            uint8_t b[2];
            put16(b, (uint16_t)pcm[i]);
            fwrite(b, 1, 2, f);
        }
        fclose(f);
        printf("%s  %zu samples  %zu ms\n", path, n, n * 1000 / MGS_SFX_RATE);
    }
    return 0;
}
