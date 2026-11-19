#pragma once
#include <stdint.h>
// The host renderers' stand-in for the chip's random source: the same fixed sequence in every build. It was libc rand(), whose sequence differs between the macOS libc the native renderer
// links and the musl the WebAssembly build links, so a screen that draws random confetti or notes came out differently in the browser. Not random at all, on purpose: frames stay reproducible.
static inline uint32_t esp_random(void)
{
    static uint32_t s = 2463534242u;   // xorshift32
    s ^= s << 13;
    s ^= s >> 17;
    s ^= s << 5;
    return s;
}
