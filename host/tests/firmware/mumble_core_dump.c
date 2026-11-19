/* Prints the blips of the text in argv[1] over argv[2] ms, one line each: t dur f0 f1 level mouth (patch UX16). The Python reference must print the same. */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_mumble_core.h"

int main(int argc, char** argv)
{
    if (argc < 3) { printf("usage: dump TEXT MS\n"); return 2; }
    mm_t m;
    mm_blip_t b;
    mm_init(&m, argv[1], 100, 100u + (uint32_t)atoi(argv[2]));
    while (mm_next(&m, &b)) printf("%u %u %u %u %u %u\n", (unsigned)b.t_ms, (unsigned)b.dur_ms, (unsigned)b.f0, (unsigned)b.f1, (unsigned)b.level, (unsigned)b.mouth);
    return 0;
}
