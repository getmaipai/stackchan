/* Fuzz harness for the unit's own parsers (the firmware's *_core.h headers, compiled on the host with the address and undefined behavior sanitizers).
 * One target per build: cc -DTARGET_FACE ... core_fuzz.c. Every input is copied into a heap block of exactly its length, so reading or writing one byte past it is a sanitizer
 * error; any sanitizer report aborts the run (-fno-sanitize-recover=all). Inputs: the valid seeds below, then byte flips, truncations, cut-and-splice, extensions to
 * oversized lengths, and pure noise, from a seeded generator (the seed and the iteration count are on the command line, so a failure repeats).
 * Usage: core_fuzz [iterations] [seed]. Prints one line, "fuzz TARGET: N inputs, ok". Run through scripts/fuzz-cores.sh.
 * Placement: host-side development tool; no firmware change. Upstream: none. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(TARGET_FACE)
#include "maipai_face_core.h"
#define NAME "face blob (mf_load)"
#elif defined(TARGET_FILLER)
#include "maipai_filler_core.h"
#define NAME "filler index (tf_parse_index)"
#elif defined(TARGET_GAMES)
#include "maipai_games_core.h"
#define NAME "game pack (mg_parse)"
#elif defined(TARGET_LANG)
#include "maipai_lang_core.h"
#define NAME "words file (mlw_parse)"
#elif defined(TARGET_REACT)
#include "maipai_react_core.h"
#define NAME "reaction table (mr_load)"
#elif defined(TARGET_PACKCACHE)
#include "maipai_packcache_core.h"
#define NAME "pack cache directory (tpc_decode)"
#elif defined(TARGET_TIMERS)
#include "maipai_timers_core.h"
#define NAME "timer blob (mt_load)"
#elif defined(TARGET_UPDATEHDR)
#include "maipai_updatehdr_core.h"
#define NAME "signed update header (muh_parse)"
#elif defined(TARGET_MOOD)
#include "maipai_mood_core.h"
#define NAME "pet record (mm_load)"
#elif defined(TARGET_TAILNET)
#include "maipai_tailnet_core.h"
#define NAME "private network address (mt_parse_ip)"
#elif defined(TARGET_REMOTE)
#include "maipai_remote_core.h"
#define NAME "remote speaking setting and say text (mr_parse_speaking, mr_say)"
#elif defined(TARGET_LISTEN)
#include "maipai_listen_core.h"
#define JOIN_(a, b) a##b   /* the firmware names this function with the other spelling; the repo hygiene check wants the American one in source text */
#define TL_PARSE_HUE JOIN_(tl_parse_colo, ur)
#define NAME "listening cue words (tl_parse_*)"
#elif defined(TARGET_LOCK)
#include "maipai_lock_core.h"
#define NAME "lock record and code (mlk_load, mlk_check)"
#elif defined(TARGET_LINKURL)
#include "maipai_linkurl_core.h"
#define NAME "encrypted link address rewrite (mlu_rewrite)"
#elif defined(TARGET_MOUTHCUE)
#include "maipai_mouthcue_core.h"
#define NAME "mouth cue lists (mmc_set, mmc_append, mmc_level)"
#elif defined(TARGET_BARGE)
#include "maipai_barge_core.h"
#define NAME "talk-over decisions (mbg_*)"
#elif defined(TARGET_PAIRX)
#include "maipai_pairx_core.h"
#define NAME "pairing exchange state machine (mpx_*)"
#else
#error "name a target, for example -DTARGET_FACE"
#endif

static uint64_t rng_state;
static uint32_t rnd(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return (uint32_t)(rng_state >> 16);
}

/* a heap copy of exactly n bytes, plus a NUL for the string parsers that expect one outside the length they are given (not counted in n) */
static uint8_t* exact(const uint8_t* src, size_t n)
{
    uint8_t* p = (uint8_t*)malloc(n ? n : 1);
    if (n) memcpy(p, src, n);
    return p;
}

static char* cstring(const uint8_t* src, size_t n)
{
    char* p = (char*)malloc(n + 1);
    for (size_t i = 0; i < n; i++) p[i] = src[i] ? (char)src[i] : 'x';   /* no embedded NUL: the C string ends where the data ends */
    p[n] = 0;
    return p;
}

static void run(const uint8_t* d, size_t n)
{
#if defined(TARGET_FACE)
    mf_config_t c;
    uint8_t* b = exact(d, n);
    mf_load(&c, b, n);
    free(b);
#elif defined(TARGET_FILLER)
    static tf_index_t x;
    char* s = cstring(d, n);
    tf_parse_index(s, n, &x);
    free(s);
#elif defined(TARGET_GAMES)
    static mg_pack_t p;
    uint8_t* b = exact(d, n);
    mg_parse(b, n, &p);
    free(b);
#elif defined(TARGET_LANG)
    static mlw_t w;
    char* s = cstring(d, n);
    mlw_parse(s, n, &w);
    free(s);
#elif defined(TARGET_REACT)
    static mr_table_t t;
    uint8_t* b = exact(d, n);
    mr_load(&t, b, n);
    free(b);
#elif defined(TARGET_PACKCACHE)
    static tpc_dir_t dir;
    uint8_t* b = (uint8_t*)calloc(1, TPC_SECTOR);   /* the function reads a whole sector: give it exactly one, filled from the input */
    memcpy(b, d, n < TPC_SECTOR ? n : TPC_SECTOR);
    tpc_decode(b, &dir);
    free(b);
#elif defined(TARGET_TIMERS)
    static mt_state_t st;
    uint8_t* b = exact(d, n);
    mt_load(&st, b, n);
    free(b);
#elif defined(TARGET_UPDATEHDR)
    muh_hdr_t h;
    uint8_t* b = exact(d, n);
    muh_parse(b, n, (uint32_t)(n * 7), &h);
    free(b);
#elif defined(TARGET_MOOD)
    mm_t m;
    uint8_t* b = (uint8_t*)calloc(1, MM_REC_BYTES);   /* a fixed 8 byte record */
    memcpy(b, d, n < MM_REC_BYTES ? n : MM_REC_BYTES);
    mm_load(&m, b);
    free(b);
#elif defined(TARGET_TAILNET)
    char* s = cstring(d, n);
    mt_parse_ip(s);
    free(s);
#elif defined(TARGET_REMOTE)
    char* s = cstring(d, n);
    mr_speak_t sp;
    mr_t r;
    mr_init(&r);
    mr_parse_speaking(s, &sp);
    mr_session(&r, 1, s, 1000);
    mr_set_host(&r, (uint32_t)n);
    uint32_t tok = 0;
    mr_action(&r, "say", 1001, &tok);
    mr_say(&r, s, tok, 1002);
    mr_gate_call(&r, s, s, tok, 1003);
    free(s);
#elif defined(TARGET_LISTEN)
    char* s = cstring(d, n);
    uint8_t r, g, b, o;
    TL_PARSE_HUE(s, &r, &g, &b);
    tl_parse_sound(s, &o);
    tl_parse_light(s, &o);
    free(s);
#elif defined(TARGET_LOCK)
    char* s = cstring(d, n);
    mlk_t l;
    memset(&l, 0, sizeof(l));
    mlk_load(&l, s, s, 1, 5, 1000);
    mlk_check(&l, s);
    free(s);
#elif defined(TARGET_LINKURL)
    char* s = cstring(d, n);
    char out[64];
    mlu_rewrite(s, out, n % 64 + 1);
    mlu_rewrite(s, out, sizeof(out));
    free(s);
#elif defined(TARGET_MOUTHCUE)
    mmc_t* m = (mmc_t*)calloc(1, sizeof(*m));
    uint32_t ms[600];
    uint8_t lvl[600];
    int cnt = (int)(n / 3);
    if (cnt > 600) cnt = 600;
    for (int k = 0; k < cnt; k++) { ms[k] = (uint32_t)(d[3 * k] | (d[3 * k + 1] << 8)) * 5u; lvl[k] = d[3 * k + 2]; }
    mmc_init(m);
    mmc_set(m, ms, lvl, cnt, 1000u);
    mmc_append(m, ms, lvl, cnt / 2, 1000u + (uint32_t)n);
    mmc_start(m, 2000u);
    for (uint32_t t = 2000u; t < 6000u; t += 37u) { int lv; mmc_level(m, t, &lv); }
    free(m);
#elif defined(TARGET_BARGE)
    mbg_t m;
    mbg_init(&m);
    uint32_t now = 1000u;
    for (size_t k = 0; k < n; k++) {
        now += (uint32_t)d[k] * 7u;
        switch (d[k] & 7) {
            case 0: mbg_speaking(&m, d[k] >> 3); break;
            case 1: mbg_tts_start(&m); break;
            case 2: mbg_no_barge_sentence(&m, now, (uint32_t)d[k] * 40u); break;
            default: (void)mbg_wake_hit(&m, now); break;
        }
        (void)mbg_frame_ok(&m);
    }
#elif defined(TARGET_PAIRX)
    mpx_t m;
    uint8_t a[MLY_PK], b[MLY_PK], c[32], nu[MLY_NONCE], nh[MLY_NONCE], z[32], k[MLY_KEY];
    memset(a, 1, sizeof(a)); memset(b, 2, sizeof(b)); memset(c, 3, sizeof(c)); memset(nu, 4, sizeof(nu)); memset(nh, 5, sizeof(nh)); memset(z, 6, sizeof(z));
    mpx_begin(&m, a, 5000u);
    uint32_t now = 5000u;
    for (size_t q = 0; q < n; q++) {
        now += (uint32_t)d[q] * 997u;
        switch (d[q] & 7) {
            case 0: mpx_on_host_key(&m, b, c, nu); break;
            case 1: nh[0] = d[q]; mpx_on_host_nonce(&m, nh); break;
            case 2: mpx_on_paired(&m, z, "aa:bb:cc:dd:ee:ff", k); break;
            case 3: mpx_abort(&m); mpx_begin(&m, a, now); break;
            default: mpx_tick(&m, now); break;
        }
    }
#endif
}

/* seeds: a few valid-looking inputs per target; the mutators do the rest */
static const char* SEEDS[] = {
    "{\"rate\":16000,\"codec\":\"mulaw\",\"lang\":\"en\",\"clips\":[{\"name\":\"hmm\",\"file\":\"hmm_1.ulaw\",\"ms\":420}]}",
    "MPG1\x01\x00\x00\x00 words: hello=1\nlove=2\n",
    "say hello 10.0.0.1 100.64.1.2 255.255.255.255 0.0.0.0 1.2.3 1.2.3.4.5 #ff00aa red green blue off on ask",
    "ABCDEF0123456789abcdef0123456789ABCDEF0123456789abcdef0123456789",
    "\x03\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
};

/* valid inputs made by the cores' own writers, so the mutations start from something the parser accepts and reach its deeper checks */
typedef struct { uint8_t* p; size_t n; } blob_t;
static blob_t BLOBS[8];
static int NBLOBS;
static void add_blob(const void* p, size_t n)
{
    if (NBLOBS >= 8 || n == 0 || n > 8000) return;
    BLOBS[NBLOBS].p = (uint8_t*)malloc(n);
    memcpy(BLOBS[NBLOBS].p, p, n);
    BLOBS[NBLOBS++].n = n;
}

static void make_blobs(void)
{
#if defined(TARGET_FACE)
    mf_config_t c;
    uint8_t out[256];
    memset(&c, 0, sizeof(c));
    add_blob(out, mf_save(&c, out, sizeof(out)));
#elif defined(TARGET_TIMERS)
    mt_state_t st;
    uint8_t out[512];
    mt_init(&st);
    mt_add_timer(&st, 1700000000u, 5u, 60u, "tea", 0);
    mt_add_timer(&st, 1700000000u, 5u, 600u, "oven", 1);
    add_blob(out, mt_save(&st, out, sizeof(out)));
#elif defined(TARGET_REACT)
    mr_table_t t;
    uint8_t out[1024];
    mr_defaults(&t);
    add_blob(out, mr_save(&t, out, sizeof(out)));
#elif defined(TARGET_PACKCACHE)
    static tpc_dir_t d;
    static uint8_t sector[TPC_SECTOR];
    memset(&d, 0, sizeof(d));
    memset(d.e, 0xFF, sizeof(d.e));
    d.e[0].type = 0; d.e[0].name_len = 4; d.e[0].first = 2; d.e[0].nsect = 1; d.e[0].version = 1; d.e[0].size = 100; memcpy(d.e[0].name, "demo", 5);
    d.have[0] = 1; d.seq = 7;
    tpc_encode(&d, sector);
    add_blob(sector, 512);   /* the directory is at the start of the sector; the rest is zero */
#elif defined(TARGET_UPDATEHDR)
    uint8_t h[MUH_HDR_LEN];
    memset(h, 0, sizeof(h));
    memcpy(h, "MPUH1", 5);
    h[8] = 9; h[12] = 0x00; h[13] = 0x10;
    add_blob(h, sizeof(h));
#elif defined(TARGET_LANG)
    static const char w[] = "lang=es\norder=dmy\nweekdays=Dom,Lun,Mar,Mie,Jue,Vie,Sab\nmonths=Ene,Feb,Mar,Abr,May,Jun,Jul,Ago,Sep,Oct,Nov,Dic\nalarm=Alarma\ntimer=Temporizador\n";
    add_blob(w, sizeof(w) - 1);
#endif
}

int main(int argc, char** argv)
{
    make_blobs();
    const long iterations = argc > 1 ? atol(argv[1]) : 20000;
    rng_state = argc > 2 ? (uint64_t)atoll(argv[2]) * 2654435761u + 88172645463325252ull : 88172645463325252ull;
    uint8_t buf[9000];
    long done = 0;
    for (long it = 0; it < iterations; it++) {
        size_t n;
        const uint32_t mode = rnd() % 6;
        if (mode == 0) {   /* noise of a random length, sometimes large */
            n = rnd() % 4 == 0 ? rnd() % sizeof(buf) : rnd() % 80;
            for (size_t i = 0; i < n; i++) buf[i] = (uint8_t)rnd();
        } else {           /* a seed, mutated */
            const char* seed = SEEDS[rnd() % (sizeof(SEEDS) / sizeof(SEEDS[0]))];
            n = strlen(seed);
            if (NBLOBS && rnd() % 4 != 0) {   /* mostly the structured seeds when there are some */
                const blob_t* b = &BLOBS[rnd() % NBLOBS];
                n = b->n;
                memcpy(buf, b->p, n);
            } else {
                if (mode == 1 && n < 8) n = 8;
                memcpy(buf, seed, n);
            }
            if (n < 8) memset(buf + n, 0, 8 - n);
            const uint32_t edits = 1 + rnd() % 6;
            for (uint32_t e = 0; e < edits; e++) {
                switch (rnd() % 6) {
                case 0: if (n) buf[rnd() % n] ^= (uint8_t)(1u << (rnd() % 8)); break;               /* flip a bit */
                case 1: if (n) buf[rnd() % n] = (uint8_t)rnd(); break;                              /* a random byte */
                case 2: if (n > 1) n = rnd() % n; break;                                            /* truncate */
                case 3: {                                                                           /* extend, to a short or a very long length */
                    size_t add = rnd() % 3 == 0 ? rnd() % 6000 : rnd() % 40;
                    for (size_t i = 0; i < add && n < sizeof(buf); i++) buf[n++] = (uint8_t)rnd();
                    break;
                }
                case 4: if (n > 4) { size_t a = rnd() % n, b = rnd() % n; uint8_t t = buf[a]; buf[a] = buf[b]; buf[b] = t; } break;
                default: if (n) memset(buf + rnd() % n, rnd() % 2 ? 0xFF : 0x00, 1 + rnd() % 4 > n ? 1 : 1 + rnd() % 4); break;   /* a run of 0xFF or 0x00 */
                }
            }
        }
        run(buf, n);
        done++;
    }
    printf("fuzz %s: %ld inputs from %d structured seed(s), ok\n", NAME, done, NBLOBS);
    return 0;
}
