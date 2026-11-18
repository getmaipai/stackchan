/* Renders the unit's own game clips (maipai_games_sfx_core.h, the tone-segment table and mgs_render) to WAV files: the sounds the robot really plays, not a sketch.
 * Usage: sfx_render OUTDIR name... Placement: host-side development tool. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>
#include "maipai_games_sfx_core.h"

static void le32(FILE* f, uint32_t v) { fputc(v & 255, f); fputc((v >> 8) & 255, f); fputc((v >> 16) & 255, f); fputc((v >> 24) & 255, f); }
static void le16(FILE* f, uint16_t v) { fputc(v & 255, f); fputc((v >> 8) & 255, f); }

int main(int argc, char** argv)
{
    static int16_t buf[MGS_SFX_MAX_SAMPLES + 16];
    for (int a = 2; a < argc; a++) {
        int idx = -1;
        for (int i = 0; i < MGS_CLIPS; i++) if (strcmp(MGS_CLIP[i].name, argv[a]) == 0) idx = i;
        if (idx < 0) { fprintf(stderr, "no clip %s in this tree\n", argv[a]); printf("%s 0\n", argv[a]); continue; }
        const size_t n = mgs_render(idx, buf, sizeof(buf) / sizeof(buf[0]));
        char path[512];
        snprintf(path, sizeof(path), "%s/%s.wav", argv[1], argv[a]);
        FILE* f = fopen(path, "wb");
        fwrite("RIFF", 1, 4, f); le32(f, 36 + (uint32_t)n * 2); fwrite("WAVEfmt ", 1, 8, f); le32(f, 16); le16(f, 1); le16(f, 1); le32(f, MGS_SFX_RATE); le32(f, MGS_SFX_RATE * 2); le16(f, 2); le16(f, 16);
        fwrite("data", 1, 4, f); le32(f, (uint32_t)n * 2);
        for (size_t i = 0; i < n; i++) le16(f, (uint16_t)buf[i]);
        fclose(f);
        printf("%s %zu\n", argv[a], n);
    }
    return 0;
}
