/* The unit's side of the pack and picture-face wire protocol, as a program (patch FM06 tests).
 *
 * It runs the firmware's own cores (maipai_pack_core.h for self.pack.*, maipai_picface_core.h for self.facepic.*) behind the same
 * tool names and the same rules as hal/maipai_packs.cc and hal/maipai_picface.cc, so the host's real push code can be run against it
 * with fragmented data, a dropped link and a reboot. One request per line on stdin: `tool key=value ...` with values percent-encoded;
 * one JSON answer per line on stdout. `reboot` forgets everything held (a unit with its flash cache off); `power_cycle` forgets the RAM
 * and applies the flash cache again, as the real unit's boot does (patches TB02, K13). Every pack type has its own slot, name and cache
 * state, and the language and phrase types run the firmware's own consumers (maipai_lang_core.h, maipai_phrasepack_core.h): a pack the
 * host builds is read by the code the unit runs, so a words file or a clip the unit would refuse is refused here too.
 * Build: cc -std=c99 -Wall -Wextra -Werror -I<dir with both headers> pack_wire_driver.c -o driver -lz
 */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <zlib.h>

#include "maipai_pack_core.h"
#include "maipai_picface_core.h"
#include "maipai_lang_core.h"
#include "maipai_phrasepack_core.h"

/* ---- request parsing ---- */
#define MAXKV 16
static char* kv_key[MAXKV];
static char* kv_val[MAXKV];
static int kv_n;

static void unquote(char* s)
{
    char* o = s;
    for (; *s; s++) {
        if (*s == '%' && isxdigit((unsigned char)s[1]) && isxdigit((unsigned char)s[2])) {
            char h[3] = {s[1], s[2], 0};
            *o++ = (char)strtol(h, NULL, 16);
            s += 2;
        } else {
            *o++ = *s;
        }
    }
    *o = 0;
}
static const char* arg(const char* k, const char* dflt)
{
    for (int i = 0; i < kv_n; i++) if (strcmp(kv_key[i], k) == 0) return kv_val[i];
    return dflt;
}

static int b64_val(int c)
{
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}
static long b64_decode(const char* s, uint8_t* out, size_t cap)
{
    size_t n = 0;
    uint32_t acc = 0;
    int bits = 0;
    for (; *s && *s != '='; s++) {
        int v = b64_val((unsigned char)*s);
        if (v < 0) return -1;
        acc = (acc << 6) | (uint32_t)v;
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            if (n >= cap) return -1;
            out[n++] = (uint8_t)((acc >> bits) & 0xff);
        }
    }
    return (long)n;
}

/* ---- self.pack.* ---- */
static tpk_rx_t rx;
static uint8_t* rx_buf;
static int held[TPK_TYPES], cached[TPK_TYPES], damaged[TPK_TYPES];
static char held_sha[TPK_TYPES][65];
static uint32_t held_size[TPK_TYPES];
static char held_name[TPK_TYPES][TPK_NAME_MAX + 1];
static uint8_t* held_data[TPK_TYPES]; /* the pack bytes the cache holds (what a power cycle reapplies) */
static mlw_t words;                   /* the language pack in use, or none */
static int words_ok;
static mph_table_t ptable;            /* the phrase pack in use */
static uint8_t* pblock;
static int pclips;

static long zinflate(const uint8_t* in, size_t inlen, uint8_t* out, size_t outcap)
{
    z_stream z;
    memset(&z, 0, sizeof(z));
    if (inflateInit2(&z, -15) != Z_OK) return -1;
    z.next_in = (Bytef*)in; z.avail_in = (uInt)inlen; z.next_out = out; z.avail_out = (uInt)outcap;
    const int r = inflate(&z, Z_FINISH);
    const long n = (long)z.total_out;
    inflateEnd(&z);
    return r == Z_STREAM_END ? n : -1;
}

/* The consumers, as maipai_lang.cc and maipai_phrasepack.cc run them. 1 when the pack is usable. */
static int apply_pack(int type, const uint8_t* data, uint32_t len)
{
    if (type == TPK_LANGUAGE) {
        tpz_t z;
        if (tpz_open(&z, data, len) != TPK_OK) return 0;
        const tpz_entry_t* e = tpz_find(&z, "words.txt");
        if (e == NULL || e->usize == 0 || e->usize > MLW_FILE_MAX) return 0;
        char* text = (char*)malloc(e->usize + 1);
        int ok = tpz_extract(&z, e, (uint8_t*)text, e->usize, zinflate) == TPK_OK && mlw_parse(text, e->usize, &words) == MLW_OK;
        free(text);
        words_ok = ok ? 1 : words_ok;
        return ok;
    }
    if (type == TPK_PHRASE) {
        tpz_t z;
        if (tpz_open(&z, data, len) != TPK_OK) return 0;
        const uint32_t need = mph_need(&z);
        if (need == 0) return 0;
        uint8_t* blk = (uint8_t*)malloc(need);
        mph_table_t t;
        if (mph_build(&z, zinflate, blk, need, &t) != TPK_OK) { free(blk); return 0; }
        free(pblock);
        pblock = blk; ptable = t; pclips = t.count;
        return 1;
    }
    return 1; /* look, filler and the rest: their consumers are tested by the picture and filler tests */
}

static void unapply(int type)
{
    if (type == TPK_LANGUAGE) { words_ok = 0; memset(&words, 0, sizeof(words)); }
    if (type == TPK_PHRASE) { free(pblock); pblock = NULL; pclips = 0; memset(&ptable, 0, sizeof(ptable)); }
}

static void say_pack(tpk_err_t e)
{
    if (e == TPK_OK) { printf("{\"ok\":true}\n"); return; }
    printf("{\"ok\":false,\"code\":\"%s\",\"error\":\"%s\"}\n", TPK_ERR_CODES[e], tpk_say(e, 0));
}

static int type_arg(void) { return tpk_type_by_name(arg("type", "look")); }

static void forget_ram(void)
{
    for (int t = 0; t < TPK_TYPES; t++) { held[t] = 0; unapply(t); }
}

/* ---- self.facepic.* ---- */
typedef struct { uint8_t* data; uint32_t comp, got, crc_run, crc_want; int done; } frame_t;
static pf_plan_t plan;
static frame_t fr[PF_SLOTS][PF_MAX_FRAMES_PER_SLOT];
static int pack_open, pack_held;

static void free_frames(void)
{
    for (int s = 0; s < PF_SLOTS; s++) for (int i = 0; i < PF_MAX_FRAMES_PER_SLOT; i++) { free(fr[s][i].data); memset(&fr[s][i], 0, sizeof(fr[s][i])); }
}
static void say_pf(pf_err_t e)
{
    if (e == PF_OK) { printf("{\"ok\":true}\n"); return; }
    printf("{\"ok\":false,\"code\":\"%s\",\"error\":\"%s\"}\n", PF_ERR_CODES[e], pf_say(e, 0));
}

static void handle(const char* tool)
{
    if (strcmp(tool, "reboot") == 0) {
        tpk_rx_init(&rx); free(rx_buf); rx_buf = NULL; free_frames(); pack_open = pack_held = 0;
        forget_ram();
        for (int t = 0; t < TPK_TYPES; t++) { cached[t] = 0; free(held_data[t]); held_data[t] = NULL; }
        printf("{\"ok\":true}\n");
    } else if (strcmp(tool, "power_cycle") == 0) { /* RAM gone, the flash cache applied again; a damaged cache means the built-in set */
        tpk_rx_init(&rx); free(rx_buf); rx_buf = NULL; free_frames(); pack_open = pack_held = 0;
        forget_ram();
        for (int t = 0; t < TPK_TYPES; t++) {
            if (!cached[t]) continue;
            if (damaged[t] || !apply_pack(t, held_data[t], held_size[t])) { cached[t] = 0; free(held_data[t]); held_data[t] = NULL; damaged[t] = 0; continue; }
            held[t] = 1;
        }
        printf("{\"ok\":true}\n");
    } else if (strcmp(tool, "damage_cache") == 0) { /* a flipped bit in the cache: found at the next boot */
        const int t = type_arg();
        if (t >= 0) damaged[t] = 1;
        printf("{\"ok\":true}\n");
    } else if (strcmp(tool, "self.pack.begin") == 0) {
        free(rx_buf); rx_buf = NULL;
        tpk_err_t e = tpk_rx_begin(&rx, arg("type", ""), arg("name", ""), (uint32_t)atol(arg("version", "0")), (uint32_t)atol(arg("size", "0")), arg("sha256", ""));
        if (e == TPK_OK) rx_buf = (uint8_t*)malloc(rx.size);
        say_pack(e);
    } else if (strcmp(tool, "self.pack.data") == 0) {
        uint8_t piece[8192];
        long n = b64_decode(arg("b64", ""), piece, sizeof(piece));
        if (n < 0) { say_pack(TPK_ERR_RANGE); return; }
        uint32_t at = (uint32_t)atol(arg("at", "0"));
        tpk_err_t e = tpk_rx_data(&rx, at, piece, (size_t)n);
        if (e == TPK_OK) memcpy(rx_buf + at, piece, (size_t)n);
        say_pack(e);
    } else if (strcmp(tool, "self.pack.commit") == 0) {
        const int type = rx.type;
        tpk_err_t e = tpk_rx_commit(&rx);
        if (e == TPK_OK) {
            if (!apply_pack(type, rx_buf, rx.size)) { free(rx_buf); rx_buf = NULL; say_pack(TPK_ERR_ZIP); return; } /* nothing changes */
            tpk_sha_t s; uint8_t d[32];
            tpk_sha_init(&s); tpk_sha_update(&s, rx_buf, rx.size); tpk_sha_final(&s, d); tpk_sha_hex(d, held_sha[type]);
            held[type] = 1; cached[type] = 1; damaged[type] = 0; held_size[type] = rx.size;
            strncpy(held_name[type], rx.name, TPK_NAME_MAX); held_name[type][TPK_NAME_MAX] = 0;
            free(held_data[type]); held_data[type] = rx_buf; rx_buf = NULL;
        }
        say_pack(e);
    } else if (strcmp(tool, "self.pack.status") == 0) {
        const int t = type_arg();
        if (t < 0) { say_pack(TPK_ERR_TYPE); return; }
        char extra[64] = "";
        if (t == TPK_LANGUAGE) snprintf(extra, sizeof(extra), ",\"lang\":\"%s\"", words_ok ? words.code : "");
        if (t == TPK_PHRASE) snprintf(extra, sizeof(extra), ",\"clips\":%d", pclips);
        printf("{\"ok\":true,\"type\":\"%s\",\"held\":%s,\"name\":\"%s\",\"sha256\":\"%s\",\"size\":%u,\"cached\":%s,\"cache\":\"%s\",\"fallback\":%s%s}\n",
               TPK_TYPE_NAMES[t], held[t] ? "true" : "false", held[t] ? held_name[t] : "", held[t] ? held_sha[t] : "", held[t] ? held_size[t] : 0u,
               cached[t] ? "true" : "false", cached[t] ? (damaged[t] ? "damaged" : "ok") : "empty", held[t] ? "false" : "true", extra);
    } else if (strcmp(tool, "self.lang.words") == 0) { /* test helper: the words in use for a face language code */
        const mlw_t* w = mlw_for(words_ok ? &words : NULL, arg("code", "en"));
        printf("{\"ok\":true,\"code\":\"%s\",\"dmy\":%d,\"wd0\":\"%s\",\"mon10\":\"%s\",\"alarm\":\"%s\",\"timer\":\"%s\"}\n", w->code, w->dmy, w->wd[0], w->mon[10], w->alarm, w->timer);
    } else if (strcmp(tool, "self.pack.remove") == 0) {
        const int t = type_arg();
        if (t < 0) { say_pack(TPK_ERR_TYPE); return; }
        held[t] = 0; cached[t] = 0; damaged[t] = 0; unapply(t); free(held_data[t]); held_data[t] = NULL;
        printf("{\"ok\":true}\n");
    } else if (strcmp(tool, "self.facepic.begin") == 0) {
        int mode = pf_mode_by_name(arg("mode", "picture"));
        pf_err_t e = pf_start_ok(mode, atoi(arg("fps", "6")));
        if (e != PF_OK) { say_pf(e); return; }
        free_frames(); pf_plan_init(&plan, mode, atoi(arg("fps", "6"))); pack_open = 1; pack_held = 0;
        printf("{\"ok\":true}\n");
    } else if (strcmp(tool, "self.facepic.frame") == 0) {
        if (!pack_open) { say_pf(PF_ERR_NOT_STARTED); return; }
        int slot = pf_slot_by_name(arg("slot", "")), index = atoi(arg("index", "0"));
        uint32_t bytes = (uint32_t)atol(arg("bytes", "0"));
        uint32_t replaces = (slot >= 0 && index >= 0 && index < PF_MAX_FRAMES_PER_SLOT) ? fr[slot][index].comp : 0;
        pf_err_t e = pf_admit(&plan, slot, index, bytes, replaces);
        if (e != PF_OK) { say_pf(e); return; }
        frame_t* f = &fr[slot][index];
        free(f->data); memset(f, 0, sizeof(*f));
        f->data = (uint8_t*)malloc(bytes); f->comp = bytes; f->crc_want = (uint32_t)strtoul(arg("crc", "0"), NULL, 16);
        plan.bytes = plan.bytes - replaces + bytes;
        if (index >= plan.frames[slot]) plan.frames[slot] = (uint8_t)(index + 1);
        plan.received[slot][index] = 0;
        plan.total_frames = 0;
        for (int s = 0; s < PF_SLOTS; s++) plan.total_frames += plan.frames[s];
        printf("{\"ok\":true}\n");
    } else if (strcmp(tool, "self.facepic.data") == 0) {
        uint8_t piece[8192];
        long n = b64_decode(arg("b64", ""), piece, sizeof(piece));
        if (n < 0) { say_pf(PF_ERR_ORDER); return; }
        if (!pack_open) { say_pf(PF_ERR_NOT_STARTED); return; }
        int slot = pf_slot_by_name(arg("slot", "")), index = atoi(arg("index", "0"));
        if (slot < 0) { say_pf(PF_ERR_SLOT); return; }
        if (index < 0 || index >= PF_MAX_FRAMES_PER_SLOT || fr[slot][index].data == NULL) { say_pf(PF_ERR_INDEX); return; }
        frame_t* f = &fr[slot][index];
        if ((uint32_t)atol(arg("at", "0")) != f->got || f->got + (uint32_t)n > f->comp) { say_pf(PF_ERR_ORDER); return; }
        memcpy(f->data + f->got, piece, (size_t)n);
        f->crc_run = pf_crc32(f->crc_run, f->data + f->got, (size_t)n);
        f->got += (uint32_t)n;
        if (f->got == f->comp) {
            if (f->crc_run != f->crc_want) { f->got = 0; f->crc_run = 0; say_pf(PF_ERR_CRC); return; }
            f->done = 1; plan.received[slot][index] = 1;
        }
        printf("{\"ok\":true,\"got\":%u,\"done\":%s}\n", f->got, f->done ? "true" : "false");
    } else if (strcmp(tool, "self.facepic.commit") == 0) {
        pf_err_t e = pack_open ? pf_complete(&plan) : PF_ERR_NOT_STARTED;
        if (e == PF_OK) { pack_open = 0; pack_held = 1; }
        say_pf(e);
    } else if (strcmp(tool, "self.facepic.status") == 0) {
        if (!pack_held) { printf("{\"ok\":true,\"held\":false,\"showing\":false}\n"); return; }
        printf("{\"ok\":true,\"held\":true,\"mode\":\"%s\",\"bytes\":%u,\"frames\":%d,\"showing\":true}\n", PF_MODE_NAMES[plan.mode], plan.bytes, plan.total_frames);
    } else if (strcmp(tool, "self.facepic.frame_crc") == 0) { /* test helper: the CRC of what a frame holds now */
        int slot = pf_slot_by_name(arg("slot", "")), index = atoi(arg("index", "0"));
        if (slot < 0 || fr[slot][index].data == NULL) { printf("{\"ok\":false}\n"); return; }
        printf("{\"ok\":true,\"crc\":\"%08x\",\"done\":%s}\n", pf_crc32(0, fr[slot][index].data, fr[slot][index].comp), fr[slot][index].done ? "true" : "false");
    } else {
        printf("{\"ok\":false,\"error\":\"Unknown tool: %s\"}\n", tool);
    }
}

int main(void)
{
    static char line[16384];
    tpk_rx_init(&rx);
    while (fgets(line, sizeof(line), stdin)) {
        kv_n = 0;
        char* save = NULL;
        char* tool = strtok_r(line, " \r\n", &save);
        if (tool == NULL) continue;
        for (char* tok; (tok = strtok_r(NULL, " \r\n", &save)) != NULL && kv_n < MAXKV;) {
            char* eq = strchr(tok, '=');
            if (eq == NULL) continue;
            *eq = 0;
            unquote(eq + 1);
            kv_key[kv_n] = tok;
            kv_val[kv_n++] = eq + 1;
        }
        handle(tool);
        fflush(stdout);
    }
    return 0;
}
