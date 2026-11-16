// Host renderer stub: a clock the harness sets, so a frame at "t = 1.2 s" is the same every run.
#pragma once
#include <stdint.h>
extern int64_t g_fake_us;
static inline int64_t esp_timer_get_time(void) { return g_fake_us; }
