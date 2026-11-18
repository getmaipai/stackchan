/* Harness for the listening guard (patch SF03): runs the guard loop of Application::Run once a second through the real mlg_should_end.
 * Usage: listen_guard follow_up_s cap_s voice_from_s voice_until_s   (voice heard on every tick from..until; 0 0 means none) -> "ends at <s>" */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_listen_guard_core.h"

int main(int argc, char** argv)
{
    if (argc != 5) { printf("usage: listen_guard follow_up_s cap_s voice_from_s voice_until_s\n"); return 2; }
    const uint32_t follow = (uint32_t)atoi(argv[1]), cap = (uint32_t)atoi(argv[2]);
    const int from = atoi(argv[3]), until = atoi(argv[4]);
    uint32_t clock = 0, since = 0, voice_tick = 0;  /* the wake word enters Listening at clock 0 */
    for (int s = 1; s <= 300; s++) {
        clock++;
        if (until > 0 && s >= from && s <= until) voice_tick = clock;  /* IsVoiceDetected() this tick */
        const uint32_t held = clock - since;
        const uint32_t last_voice = (voice_tick - since < 0x80000000u) ? voice_tick : since;
        if (mlg_should_end(held, clock - last_voice, follow, cap)) { printf("ends at %d\n", s); return 0; }
    }
    printf("never ends\n");
    return 0;
}
