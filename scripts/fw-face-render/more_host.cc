// Host stand-ins for what the More screen (maipai_more.cc) asks of the rest of the unit: the language, the lock, the games list, the time zone, the network test and the version
// numbers. The values are plain examples (a release build, a quiet network); `more set KEY VALUE` changes them for a scenario. Placement: host-side development tool. Upstream: none.
#include <sdkconfig.h>
#include "maipai_more.h"
#include "maipai_face.h"
#include "maipai_face_core.h"
#include "maipai_lock.h"
#include "maipai_games.h"
#include "maipai_tz.h"
#include "maipai_nettest.h"
#include "maipai_version.h"
#include <cstdio>
#include <cstring>

int g_more_lang = 0;          // 0 English, 1 Spanish
int g_more_games = 2;         // how many games the unit lists
bool g_more_locked_code = true;

mf_config_t maipai_face_config()
{
    mf_config_t c;
    mf_default(&c);
    c.lang = g_more_lang == 1 ? MF_LANG_ES : MF_LANG_EN;
    return c;
}
bool maipai_lock_has_code() { return g_more_locked_code; }
bool maipai_lock_now(const char*) { return true; }
int maipai_games_count() { return g_more_games; }
const char* maipai_games_id(int i) { static const char* ids[] = {"tictactoe", "memory", "whack", "rps"}; return ids[i & 3]; }
const char* maipai_games_title(int i, bool es) { static const char* en[] = {"Tic-Tac-Toe", "Color Memory", "Whack", "Rock Paper Scissors"}; static const char* sp[] = {"Tres en raya", "Memoria", "Golpea", "Piedra papel tijera"}; return (es ? sp : en)[i & 3]; }
int maipai_games_best(int) { return 0; }
const char* maipai_games_start_locked(const char*, const char*) { return nullptr; }
extern "C" void maipai_quick_settings_close(void) {}
extern "C" void maipai_display_open_quick(void) {}
int maipai_tz_current() { return 0; }
bool maipai_tz_set(int) { return true; }
void maipai_tz_local_hhmm(char* out, int cap) { snprintf(out, cap, "%s", "10:24"); }
bool maipai_tz_picker_allowed() { return true; }
void maipai_nettest_run(mn_result_t* out, int* lang)
{
    memset(out, 0, sizeof(*out));
    *lang = g_more_lang;
    out->state[0] = MN_OK; snprintf(out->line[0], MN_LINE, "%s", g_more_lang ? "Wi-Fi: bien, senal buena" : "Wi-Fi: connected, good signal");
    out->state[1] = MN_OK; snprintf(out->line[1], MN_LINE, "%s", g_more_lang ? "Home: responde" : "Home: answers");
    out->state[2] = MN_SKIP; snprintf(out->line[2], MN_LINE, "%s", g_more_lang ? "Red privada: no se usa" : "Private network: not used");
}
void maipai_version_read(mv_info_t* o)
{
    memset(o, 0, sizeof(*o));
    snprintf(o->version, sizeof(o->version), "%s", "v1.0.0-b52+7");
    snprintf(o->project, sizeof(o->project), "%s", "MaiPai");
    snprintf(o->slot, sizeof(o->slot), "%s", "ota_0");
    o->slot_known = 1;
    o->update_key = 1;
    o->image_state = MV_IMG_VALID;
    o->internal_free = 68500; o->internal_min = 32024; o->internal_big = 25600;
    o->psram_free = 7340000; o->psram_min = 7100000;
    o->uptime_s = 3700;
}
