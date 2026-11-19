#include <stdio.h>
#include <string.h>
#include "maipai_lines_core.h"

static void put16(unsigned char* p, unsigned v) { p[0] = (unsigned char)v; p[1] = (unsigned char)(v >> 8); }
static void put24(unsigned char* p, unsigned v) { p[0] = (unsigned char)v; p[1] = (unsigned char)(v >> 8); p[2] = (unsigned char)(v >> 16); }
static void put32(unsigned char* p, unsigned v) { p[0] = (unsigned char)v; p[1] = (unsigned char)(v >> 8); p[2] = (unsigned char)(v >> 16); p[3] = (unsigned char)(v >> 24); }

int main(void)
{
    unsigned char b[256] = {0};
    const char* texts[] = {"Hello there", "Good to see you"};
    const char* tag = "greeting_day";
    memcpy(b, "MPSH", 4); b[4] = 1; b[5] = 'e'; b[6] = 'n'; put16(b + 8, 2); put32(b + 10, 16);
    unsigned pos = 48;
    for (unsigned i = 0; i < 2; ++i) {
        unsigned char* e = b + 16 + i * 16;
        e[8] = MPY_LINE; e[9] = MPY_KID; put24(e + 11, pos);
        const unsigned tl = (unsigned)strlen(texts[i]) + 1 + 1 + (unsigned)strlen(tag);
        put16(e + 14, tl);
        memcpy(b + pos, texts[i], strlen(texts[i]) + 1);
        memcpy(b + pos + strlen(texts[i]) + 1 + 1, tag, strlen(tag));
        pos += tl;
    }
    mpy_shelf_t sh;
    if (mpy_parse(b, pos, &sh) != MPY_OK) return 1;
    if (ML_SITUATION_COUNT != 20) return 2;
    for (int i = 0; i < ML_SITUATION_COUNT; ++i) {
        if (ml_situation_index(ML_SITUATIONS[i]) != i) return 3;
        for (int j = i + 1; j < ML_SITUATION_COUNT; ++j) if (strcmp(ML_SITUATIONS[i], ML_SITUATIONS[j]) == 0) return 4;
    }
    if (ml_situation_index("not_a_situation") != -1) return 5;
    ml_state_t state = {0};
    int a = ml_pick(&sh, tag, 1000, 7, &state);
    if (a < 0) return 6;
    if (ml_pick(&sh, tag, 1001, 7, &state) != -1) return 7;
    int next = ml_pick(&sh, tag, 31000, 7, &state);
    if (next < 0 || next == a) return 8;
    int after = ml_pick(&sh, tag, 61000, 8, &state);
    if (after < 0 || after == next) return 9;
    puts("lines core ok");
    return 0;
}
