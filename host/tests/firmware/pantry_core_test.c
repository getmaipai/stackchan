/* Host test of the pantry core (patch SF92): shelf checks, record parts, the heard list, choosing a record, and the heard list in the asset store with a power cut at every step. */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_assets_core.h"
#include "maipai_pantry_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

/* ---- a shelf builder ---- */
typedef struct { uint8_t kind, rating; const char* text; const char* answer; const char* extra; } rec_t;
static uint32_t build(uint8_t* out, const rec_t* r, int n, int rating_max)
{
    memset(out, 0, 16);
    memcpy(out, "MPSH", 4); out[4] = 1; out[5] = 'e'; out[6] = 'n'; out[7] = (uint8_t)rating_max;
    out[8] = (uint8_t)n; out[9] = (uint8_t)(n >> 8);
    out[10] = 16; /* index offset */
    uint32_t text_at = 16u + (uint32_t)n * 16u;
    for (int i = 0; i < n; i++) {
        uint8_t* e = out + 16 + i * 16;
        memset(e, 0, 16);
        e[0] = (uint8_t)(0xA0 + i); e[1] = (uint8_t)(i * 7); e[7] = 0x55;   /* the id: its first 4 bytes differ per record */
        e[8] = r[i].kind; e[9] = r[i].rating;
        uint8_t* t = out + text_at;
        size_t len = 0;
        const size_t lt = strlen(r[i].text), la = strlen(r[i].answer), le = strlen(r[i].extra);
        memcpy(t, r[i].text, lt); t[lt] = 0; memcpy(t + lt + 1, r[i].answer, la); t[lt + 1 + la] = 0; memcpy(t + lt + 2 + la, r[i].extra, le);
        len = lt + 2 + la + le;
        e[11] = (uint8_t)text_at; e[12] = (uint8_t)(text_at >> 8); e[13] = (uint8_t)(text_at >> 16);
        e[14] = (uint8_t)len; e[15] = (uint8_t)(len >> 8);
        text_at += (uint32_t)len;
    }
    return text_at;
}

/* ---- a RAM flash with a power cut ---- */
#define DATA 24u
#define REGION ((MAS_RING + DATA) * MAS_SECTOR)
static uint8_t flash[REGION];
static long steps, cut_at = -1;
static int dead;
static int f_read(void* c, uint32_t off, uint8_t* b, size_t n) { (void)c; memcpy(b, flash + off, n); return 0; }
static int f_erase(void* c, uint32_t off, size_t n)
{
    (void)c;
    if (dead) return -1;
    if (cut_at >= 0 && steps++ == cut_at) { memset(flash + off, 0xFF, n / 2); dead = 1; return -1; }
    if (cut_at < 0) steps++;
    memset(flash + off, 0xFF, n);
    return 0;
}
static int f_write(void* c, uint32_t off, const uint8_t* b, size_t n)
{
    (void)c;
    if (dead) return -1;
    if (cut_at >= 0 && steps++ == cut_at) { memcpy(flash + off, b, n / 2); dead = 1; return -1; }
    if (cut_at < 0) steps++;
    for (size_t i = 0; i < n; i++) flash[off + i] &= b[i];
    return 0;
}
static const tpc_ops_t OPS = {f_read, f_erase, f_write, NULL};

int main(void)
{
    static uint8_t shelf[4096];
    const rec_t recs[] = {
        {MPY_JOKE, 0, "Why did the cat sit on the computer? | To keep an eye on the mouse.", "", ""},
        {MPY_RIDDLE, 0, "What has hands but cannot clap?", "A clock", ""},
        {MPY_TRIVIA, 0, "Which planet is red?", "Mars", "Venus|Jupiter"},
        {MPY_TRIVIA, 0, "How many legs does a spider have?", "Eight", "Six|Ten"},
        {MPY_STORY, 0, "Once a small robot found a seed.|It planted it by the window.|A flower grew.", "", ""},
        {MPY_JOKE, 1, "An adult joke", "", ""},
    };
    uint32_t len = build(shelf, recs, 5, MPY_KID);
    mpy_shelf_t sh;
    CHECK(mpy_parse(shelf, len, &sh) == MPY_OK && sh.count == 5 && strcmp(sh.lang, "en") == 0 && sh.rating_max == MPY_KID);
    mpy_rec_t r;
    mpy_get(&sh, 2, &r);
    CHECK(r.kind == MPY_TRIVIA && r.text_len == 20 && strncmp(r.text, "Which planet is red?", 20) == 0);
    CHECK(r.answer_len == 4 && strncmp(r.answer, "Mars", 4) == 0 && r.extra_len == 13 && strncmp(r.extra, "Venus|Jupiter", 13) == 0);
    mpy_get(&sh, 0, &r);
    CHECK(r.answer_len == 0 && r.extra_len == 0 && r.text_len > 40);                  /* a joke has no answer */
    /* the checks */
    CHECK(mpy_parse(shelf, 8, &sh) == MPY_E_SHORT);
    { uint8_t x[4096]; memcpy(x, shelf, len); x[0] = 'X'; CHECK(mpy_parse(x, len, &sh) == MPY_E_MAGIC); }
    { uint8_t x[4096]; memcpy(x, shelf, len); x[4] = 2; CHECK(mpy_parse(x, len, &sh) == MPY_E_FORMAT); }
    { uint8_t x[4096]; memcpy(x, shelf, len); x[8] = 0; CHECK(mpy_parse(x, len, &sh) == MPY_E_COUNT); }
    { uint8_t x[4096]; memcpy(x, shelf, len); x[15] = 1; CHECK(mpy_parse(x, len, &sh) == MPY_E_RESERVED); }
    { uint8_t x[4096]; memcpy(x, shelf, len); x[10] = 0xFF; x[11] = 0xFF; CHECK(mpy_parse(x, len, &sh) == MPY_E_INDEX); }   /* the index would run past the file */
    { uint8_t x[4096]; memcpy(x, shelf, len); x[16 + 8] = 9; CHECK(mpy_parse(x, len, &sh) == MPY_E_RECORD); }  /* unknown kind */
    { uint8_t x[4096]; memcpy(x, shelf, len); x[16 + 9] = 1; CHECK(mpy_parse(x, len, &sh) == MPY_E_RECORD); }  /* a rating above the shelf's ceiling */
    { uint8_t x[4096]; memcpy(x, shelf, len); x[16 + 15] = 0xFF; CHECK(mpy_parse(x, len, &sh) == MPY_E_RECORD); } /* a text that runs past the file */
    CHECK(mpy_parse(shelf, len - 1, &sh) == MPY_E_RECORD);                                                       /* a last text cut short */
    for (int e = 0; e < MPY_E_COUNT_CODES; e++) CHECK(MPY_REASONS[e] != NULL && strlen(MPY_REASONS[e]) > 1);

    /* ---- choosing ---- */
    static mph_t h;
    memset(&h, 0, sizeof(h));
    mpy_parse(shelf, len, &sh);
    CHECK(mpy_unheard(&sh, 0, &h) == 5 && mpy_unheard(&sh, MPY_TRIVIA, &h) == 2);
    int seen[5] = {0};
    for (uint32_t seed = 1; seed < 200; seed++) {                                        /* with nothing heard, any record can come, never a wrong kind */
        const int i = mpy_pick(&sh, MPY_TRIVIA, MPY_KID, &h, seed);
        CHECK(i == 2 || i == 3);
        if (i >= 0) seen[i]++;
    }
    CHECK(seen[2] > 20 && seen[3] > 20);
    mpy_get(&sh, 2, &r);
    CHECK(mph_mark_heard(&h, r.id) == 1);
    for (uint32_t seed = 1; seed < 50; seed++) CHECK(mpy_pick(&sh, MPY_TRIVIA, MPY_KID, &h, seed) == 3);   /* the unheard one comes first */
    mpy_get(&sh, 3, &r);
    CHECK(mph_mark_heard(&h, r.id) == 2);
    CHECK(mpy_pick(&sh, MPY_TRIVIA, MPY_KID, &h, 5) == 2);                               /* all heard: the least recently heard */
    mpy_get(&sh, 2, &r);
    CHECK(mph_mark_heard(&h, r.id) == 3);
    CHECK(mpy_pick(&sh, MPY_TRIVIA, MPY_KID, &h, 5) == 3);
    mpy_get(&sh, 3, &r);
    CHECK(mph_deny(&h, r.id) == 2);                                                      /* never again: a new deny */
    {   /* review fix: the same id told again is "already denied" (1), changes nothing and so costs no flash write */
        mph_t before = h;
        int writes = 0;
        for (int again = 0; again < 3; again++) { const int got = mph_deny(&h, r.id); CHECK(got == 1); writes += got == 2; }
        CHECK(writes == 0 && memcmp(&before, &h, sizeof(h)) == 0);
    }
    CHECK(mpy_pick(&sh, MPY_TRIVIA, MPY_KID, &h, 5) == 2 && mpy_pick(&sh, MPY_TRIVIA, MPY_KID, &h, 9) == 2);
    mpy_get(&sh, 2, &r);
    CHECK(mph_deny(&h, r.id) == 2);
    CHECK(mpy_pick(&sh, MPY_TRIVIA, MPY_KID, &h, 5) == -1);                              /* nothing left of that kind */
    CHECK(mpy_pick(&sh, MPY_JOKE, MPY_KID, &h, 5) == 0);

    /* ---- the trivia tiles ---- */
    {
        char tiles[3][MPY_TILE_BYTES];
        int right = -1, seen_pos[3] = {0, 0, 0};
        for (uint32_t seed = 1; seed < 300; seed++) {
            const int n = mpy_tiles("Mars", "Venus|Jupiter", seed, tiles, &right);
            CHECK(n == 3 && right >= 0 && right < 3 && strcmp(tiles[right], "Mars") == 0);
            int found = 0;
            for (int i = 0; i < 3; i++) found += strcmp(tiles[i], "Venus") == 0 || strcmp(tiles[i], "Jupiter") == 0 || strcmp(tiles[i], "Mars") == 0;
            CHECK(found == 3);
            seen_pos[right]++;
        }
        CHECK(seen_pos[0] > 40 && seen_pos[1] > 40 && seen_pos[2] > 40);                /* the right answer is not always in the same place */
        CHECK(mpy_tiles("Eight", "Six", 5, tiles, &right) == 2 && strcmp(tiles[right], "Eight") == 0);
        CHECK(mpy_tiles("Eight", "", 5, tiles, &right) == 0);                          /* no wrong answers: no tiles */
        CHECK(mpy_tiles("Eight", "||", 5, tiles, &right) == 0);
        CHECK(mpy_tiles("Eight", "A|B|C|D", 5, tiles, &right) == 3);                    /* at most three tiles */
        char big[200];
        memset(big, 'x', sizeof(big)); big[150] = '\0';
        mpy_tiles(big, "y", 5, tiles, &right);
        CHECK(strlen(tiles[right]) == MPY_TILE_CHARS);                                  /* a long answer is cut to 40 characters */
        mpy_tiles("\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9\xC3\xA9", "z", 5, tiles, &right);   /* 30 accented letters, 60 bytes: whole characters only */
        CHECK(strlen(tiles[right]) % 2 == 0 && strlen(tiles[right]) <= MPY_TILE_BYTES - 4);
    }

    /* ---- the heard list: encode, decode, sync, room ---- */
    static uint8_t sector[4096];
    mph_encode(&h, sector);
    static mph_t back;
    CHECK(mph_decode(sector, 4096, &back) && back.n == h.n && back.counter == h.counter);
    for (uint16_t i = 0; i < h.n; i++) CHECK(back.e[i].id32 == h.e[i].id32 && back.e[i].flags == h.e[i].flags && back.e[i].counter == h.e[i].counter);
    sector[20] ^= 1;
    CHECK(!mph_decode(sector, 4096, &back));                                             /* a flipped bit is refused */
    const mph_entry_t* un[8];
    CHECK(mph_unsynced(&h, un, 8) == h.n);
    mph_ack(&h, 2);
    CHECK(mph_unsynced(&h, un, 8) < h.n);
    memset(&h, 0, sizeof(h));
    for (uint32_t i = 0; i < MPH_MAX; i++) { uint8_t id[8] = {0}; id[0] = (uint8_t)i; id[1] = (uint8_t)(i >> 8); id[2] = 1; CHECK(mph_mark_heard(&h, id) != 0); }
    CHECK(h.n == MPH_MAX);
    { uint8_t id[8] = {0xEE, 0xEE, 0xEE, 0xEE}; CHECK(mph_mark_heard(&h, id) == 0); }    /* full and nothing synced: refused, never drops what the host has not seen */
    mph_ack(&h, 10);
    { uint8_t id[8] = {0xEE, 0xEE, 0xEE, 0xEE}; CHECK(mph_mark_heard(&h, id) != 0 && h.n == MPH_MAX && mph_find(&h, mph_id32(id)) >= 0); }   /* the oldest synced entry made room */
    mph_encode(&h, sector);
    CHECK(mph_decode(sector, 4096, &back) && back.n == MPH_MAX);                         /* the fullest list still fits in one sector */

    /* ---- the heard list in the asset store: one unit-written item, a power cut at every step ---- */
    memset(flash, 0xFF, sizeof(flash));
    mas_dir_t d; mas_report_t rep; static uint8_t scratch[MAS_SECTOR];
    mas_scan(&OPS, NULL, scratch, DATA, &d, &rep);
    memset(&h, 0, sizeof(h));
    { uint8_t id[8] = {1, 2, 3, 4}; mph_mark_heard(&h, id); }
    mph_encode(&h, sector);
    CHECK(mas_store_unit(&OPS, NULL, scratch, &d, 8, "heard", sector, 4096) == MAS_OK);
    CHECK(mas_find(&d, 8, 0) >= 0 && d.e[mas_find(&d, 8, 0)].version == 1);
    CHECK(mas_store_unit(&OPS, NULL, scratch, &d, 6, "x", sector, 4096) == MAS_E_KIND);  /* only a unit kind is written by the unit */
    CHECK(mas_store_unit(&OPS, NULL, scratch, &d, 8, "heard", sector, 5000) == MAS_E_KIND);
    long total = 0;
    for (long cut = 0; cut < 12; cut++) {
        memset(flash, 0xFF, sizeof(flash));
        steps = 0; cut_at = -1; dead = 0;
        mas_scan(&OPS, NULL, scratch, DATA, &d, &rep);
        memset(&h, 0, sizeof(h));
        { uint8_t id[8] = {1, 2, 3, 4}; mph_mark_heard(&h, id); }
        mph_encode(&h, sector);
        CHECK(mas_store_unit(&OPS, NULL, scratch, &d, 8, "heard", sector, 4096) == MAS_OK);
        { uint8_t id[8] = {5, 6, 7, 8}; mph_mark_heard(&h, id); }                          /* the next telling: a second write, cut at step `cut` */
        mph_encode(&h, sector);
        steps = 0; cut_at = cut; dead = 0;
        const int rc = mas_store_unit(&OPS, NULL, scratch, &d, 8, "heard", sector, 4096);
        if (steps > total) total = steps;
        cut_at = -1; dead = 0;
        mas_dir_t after; mas_report_t ar;
        mas_scan(&OPS, NULL, scratch, DATA, &after, &ar);
        CHECK(ar.dir_found && !ar.damaged[mas_find(&after, 8, 0)]);
        const int i = mas_find(&after, 8, 0);
        CHECK(i >= 0);
        uint8_t body[4096];
        CHECK(f_read(NULL, (MAS_RING + after.e[i].first) * MAS_SECTOR, body, 4096) == 0);
        mph_t got;
        CHECK(mph_decode(body, after.e[i].size, &got) == 1);                               /* the heard list that survives is a whole one */
        CHECK(got.n == 1 || got.n == 2);
        if (rc == MAS_OK) CHECK(got.n == 2);                                               /* a write that reported success is there */
        if (cut >= steps && rc != MAS_OK) CHECK(0);
    }
    CHECK(total >= 4);
    printf(fails ? "pantry_core_test FAILED\n" : "pantry_core_test ok\n");
    return fails ? 1 : 0;
}
