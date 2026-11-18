/* The unit's host-reconnect rules (firmware patch SF49, maipai_reconnect_core.h) behind a plain C interface for ctypes: the virtual unit calls the unit's own backoff and notice rules.
 * The header is cut out of the patch by host_away.py. Placement: host-side development tool. Upstream: none. */
#include "maipai_reconnect_core.h"

uint32_t rc_cap(uint32_t away_ms) { return mrc_cap(away_ms); }
uint32_t rc_grow(uint32_t delay_ms, uint32_t cap_ms) { return mrc_grow(delay_ms, cap_ms); }
uint32_t rc_wait(uint32_t delay_ms, uint32_t cap_ms, uint32_t rnd) { return mrc_wait(delay_ms, cap_ms, rnd); }
int rc_notice_due(uint32_t away_ms, uint32_t last_ms) { return mrc_notice_due(away_ms, last_ms); }
