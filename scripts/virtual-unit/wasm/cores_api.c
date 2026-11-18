/* Spike B: three of the unit's pure C cores behind one small C API for WebAssembly: the lock core (maipai_lock_core.h), the movement limiter core
 * (maipai_motion_limit_core.h) and the dance ladder core (maipai_dance_ladder_core.h, through the same wrapper the Python virtual unit uses).
 * The headers are the firmware's own, from the replayed tree; nothing is copied. Time is passed in by the caller (a fake clock).
 * Placement: host-side development tool. Upstream: none. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "maipai_lock_core.h"
#include "maipai_motion_limit_core.h"
#include "../dance/ladder_sim.c"

/* ---- lock ---- */
static mlk_t g_lock;
static const uint8_t g_salt[LK_SALT_LEN] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
void lock_reset(void) { mlk_init(&g_lock); }
int lock_set(const char* code, const char* current) { return mlk_set(&g_lock, code, current, g_salt); }
int lock_lock_now(uint32_t now) { return mlk_lock_now(&g_lock, now); }
void lock_touch(uint32_t now) { mlk_screen_touch(&g_lock, now); }
int lock_key(int key, uint32_t now) { return mlk_key(&g_lock, (char)key, now); }
int lock_keypad_tick(uint32_t now) { return mlk_keypad_tick(&g_lock, now); }
int lock_is_locked(void) { return g_lock.locked; }
int lock_entered(void) { return g_lock.n; }
int lock_wrong_shown(void) { return g_lock.wrong_shown; }
static char g_json[160];
const char* lock_status(void) { mlk_status_json(&g_lock, g_json, sizeof(g_json)); return g_json; }
const char* lock_reply(int reason) { mlk_reply_json(reason, g_json, sizeof(g_json)); return g_json; }

/* ---- movement limiter ---- */
static mml_t g_ml;
void limit_reset(void) { mml_init(&g_ml); }
void limit_step(uint32_t now, int carried, int usb, int level) { mml_step(&g_ml, now, carried, usb, level); }
void limit_orient(uint32_t now, float ax, float ay, float az, float pitch) { mml_orient_feed(&g_ml, now, ax, ay, az, pitch); }
const char* limit_state(void) { return mml_state_name(&g_ml); }
int limit_scale(void) { return mml_scale(&g_ml); }
int limit_speed_cap(void) { return mml_speed_cap(&g_ml); }
int limit_dance_max(void) { return mml_dance_max(&g_ml); }
int limit_angle(int angle, int current) { return mml_angle(&g_ml, angle, current); }
