// Host renderer stub: the pictures of the face (patch V23) live in PSRAM on the unit; here they are plain memory.
#pragma once
#include <stdlib.h>
#define MALLOC_CAP_SPIRAM 0
#define MALLOC_CAP_8BIT 0
#define MALLOC_CAP_INTERNAL 0
static inline void* heap_caps_malloc(size_t n, unsigned caps) { (void)caps; return malloc(n); }
