/* The hand-written wrappers of the virtual unit's cores in one translation unit: the spike's lock, limiter and dance ladder wrappers (cores_api.c, which includes the Python
 * virtual unit's own dance/ladder_sim.c) and the host reconnect wrapper the Python virtual unit loads with ctypes (dance/reconnect_sim.c). Included, not copied.
 * Placement: host-side development tool. Upstream: none. */
#include "cores_api.c"
#include "../dance/reconnect_sim.c"

/* The signed update header check (maipai_updatehdr_core.h, patch FM02 family), on a header given as hex text: muh_parse needs a byte buffer, which a caller cannot hand over. */
#include "maipai_updatehdr_core.h"
static muh_hdr_t g_hdr;
static int hexv(char c) { return c >= '0' && c <= '9' ? c - '0' : (c >= 'a' && c <= 'f' ? c - 'a' + 10 : (c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1)); }
int hdr_parse_hex(const char* hex, uint32_t floor_build, const char* board)
{
    uint8_t b[128]; size_t n = 0;
    for (; hex[0] && hex[1] && n < sizeof(b); hex += 2) { int h = hexv(hex[0]), l = hexv(hex[1]); if (h < 0 || l < 0) return -1; b[n++] = (uint8_t)(h * 16 + l); }
    return muh_parse(b, n, floor_build, board, &g_hdr);
}
uint32_t hdr_build(void) { return g_hdr.build; }
uint32_t hdr_image_len(void) { return g_hdr.image_len; }
const char* hdr_reason(int code) { return code >= 0 && code < MUH_COUNT ? MUH_REASONS[code] : "unknown"; }
