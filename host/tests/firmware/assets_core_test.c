/* Host test of the asset store core (patch SF89): header checks, install, replace, swap, remove, wear rotation, references, and a power cut at every flash step. */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_assets_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

#define DATA 40u                                     /* data sectors in the test region */
#define REGION ((MAS_RING + DATA) * MAS_SECTOR)
static uint8_t flash[REGION];
static long steps, cut_at = -1;                      /* a cut makes this step half done and every later one fail */
static int dead;

static int f_read(void* c, uint32_t off, uint8_t* b, size_t n) { (void)c; if (off + n > REGION) return -1; memcpy(b, flash + off, n); return 0; }
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
    for (size_t i = 0; i < n; i++) flash[off + i] &= b[i];   /* flash can only clear bits */
    return 0;
}
static const tpc_ops_t OPS = {f_read, f_erase, f_write, NULL};

static void put32(uint8_t* p, uint32_t v) { tpc_put32(p, v); }
static void sha_of(const uint8_t* body, uint32_t n, uint8_t out[32]) { muh_sha_t s; muh_sha_begin(&s); muh_sha_update(&s, body, n); muh_sha_end(&s, out); }

/* a header for a body */
static void mkhdr(uint8_t h[MAS_ASSET_HDR], int kind, const char* name, uint32_t version, const uint8_t* body, uint32_t n)
{
    memset(h, 0, MAS_ASSET_HDR);
    memcpy(h, "MPAH1", 5);
    put32(h + 8, version);
    put32(h + 12, n);
    sha_of(body, n, h + 16);
    memcpy(h + 48, "STKCHN01", 8);
    h[56] = (uint8_t)kind;
    h[57] = 1;
    memcpy(h + 64, name, strlen(name));
    memcpy(h + 104, "en", 2);
    h[120] = 1;   /* license id 1 */
}

static uint8_t body_a[9000], body_b[5000], body_c[200], sector[MAS_SECTOR];
static void fill(uint8_t* b, size_t n, uint8_t seed) { for (size_t i = 0; i < n; i++) b[i] = (uint8_t)(seed + i * 7 + (i >> 8)); }

static int install(mas_dir_t* d, int kind, const char* name, uint32_t ver, const uint8_t* body, uint32_t n, int slot)
{
    uint8_t h[MAS_ASSET_HDR];
    mah_t m;
    mkhdr(h, kind, name, ver, body, n);
    int r = mah_parse(h, sizeof(h), "STKCHN01", 100, &m);
    if (r != MAS_OK) return r;
    return mas_store(&OPS, NULL, sector, d, &m, slot, body, NULL);
}

static void fresh(mas_dir_t* d, mas_report_t* r)
{
    memset(flash, 0xFF, sizeof(flash));
    steps = 0; cut_at = -1; dead = 0;
    mas_scan(&OPS, NULL, sector, DATA, d, r);
}

int main(void)
{
    fill(body_a, sizeof(body_a), 1); fill(body_b, sizeof(body_b), 50); fill(body_c, sizeof(body_c), 99);
    mas_dir_t d; mas_report_t rep;
    uint8_t h[MAS_ASSET_HDR]; mah_t m;

    /* ---- the header ---- */
    mkhdr(h, 4, "Trivia pack", 3, body_c, sizeof(body_c));
    CHECK(mah_parse(h, sizeof(h), "STKCHN01", 100, &m) == MAS_OK && m.kind == 4 && m.version == 3 && strcmp(m.name, "Trivia pack") == 0 && m.license == 1);
    CHECK(mah_parse(h, 100, "STKCHN01", 100, &m) == MAS_E_SHORT);
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); x[0] = 'X'; CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_MAGIC); }
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); memset(x + 48, 0, 8); CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_BOARD_ZERO); }
    CHECK(mah_parse(h, sizeof(h), "OTHER001", 100, &m) == MAS_E_BOARD_OTHER);
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); x[56] = 9; CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_KIND); }
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); x[64] = '!'; CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_NAME); }
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); put32(x + 12, 0); CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_LENGTH); }
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); put32(x + 12, 16385); CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_LENGTH); }   /* a game pack is at most 16,384 bytes */
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); x[120] = 0; x[121] = 0; CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_LICENSE); }
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); put32(x + 60, 101); CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_NEWER_FIRMWARE); }
    { uint8_t x[MAS_ASSET_HDR]; memcpy(x, h, sizeof(x)); x[127] = 1; CHECK(mah_parse(x, sizeof(x), "STKCHN01", 100, &m) == MAS_E_RESERVED); }
    for (int e = 0; e < MAS_E_COUNT; e++) CHECK(MAS_ERR_EN[e] != NULL && MAS_ERR_ES[e] != NULL && strlen(MAS_ERR_EN[e]) > 1);

    /* ---- empty region, first install ---- */
    fresh(&d, &rep);
    CHECK(!rep.dir_found && mas_free_sectors(&d) == DATA);
    CHECK(install(&d, 4, "Quiz", 1, body_a, sizeof(body_a), -1) == MAS_OK);          /* 9,000 bytes: 3 sectors */
    CHECK(mas_free_sectors(&d) == DATA - 3);
    CHECK(mas_active(&d, 4) >= 0 && d.e[mas_active(&d, 4)].slot == 0);               /* the first item of a kind is active */
    CHECK(install(&d, 4, "Maze", 1, body_b, sizeof(body_b), -1) == MAS_OK);          /* 5,000 bytes: 2 sectors, slot 1 */
    CHECK(d.e[mas_find(&d, 4, 1)].first == 3);                                       /* the rotating start: right after the last run */
    mas_dir_t back; mas_scan(&OPS, NULL, sector, DATA, &back, &rep);                 /* a reboot sees the same directory */
    CHECK(rep.dir_found && !rep.dir_corrupt && back.seq == d.seq && mas_find(&back, 4, 0) >= 0 && mas_find(&back, 4, 1) >= 0);
    for (unsigned i = 0; i < MAS_MAX_ENTRIES; i++) CHECK(!rep.damaged[i]);

    /* ---- swap, remove, replace, version rule, limits ---- */
    CHECK(mas_swap(&OPS, NULL, sector, &d, 4, 1) == MAS_OK && d.e[mas_active(&d, 4)].slot == 1);
    CHECK(mas_swap(&OPS, NULL, sector, &d, 4, 5) == MAS_E_NO_ITEM);
    CHECK(install(&d, 4, "Quiz", 2, body_c, sizeof(body_c), 0) == MAS_OK);            /* replace slot 0: a new run, the old one stays until the flip */
    CHECK(d.e[mas_find(&d, 4, 0)].size == sizeof(body_c) && d.e[mas_active(&d, 4)].slot == 1);
    CHECK(install(&d, 4, "Quiz", 1, body_c, sizeof(body_c), 0) == MAS_E_VERSION);     /* a lower version of the same name is refused */
    CHECK(install(&d, 4, "Third", 1, body_c, sizeof(body_c), 8) == MAS_E_SLOT);
    for (int i = 2; i < 8; i++) { char nm[20]; snprintf(nm, sizeof(nm), "Game %d", i); CHECK(install(&d, 4, nm, 1, body_c, sizeof(body_c), -1) == MAS_OK); }
    CHECK(install(&d, 4, "Ninth", 1, body_c, sizeof(body_c), -1) == MAS_E_FULL);     /* a kind holds 8 */
    CHECK(mas_remove(&OPS, NULL, sector, &d, 4, 1) == MAS_OK && mas_find(&d, 4, 1) < 0);
    CHECK(mas_active(&d, 4) >= 0 && d.e[mas_active(&d, 4)].slot == 0);               /* the active item moved to the lowest slot left */
    CHECK(mas_remove(&OPS, NULL, sector, &d, 4, 1) == MAS_E_NO_ITEM);

    /* ---- room: a font that does not fit is refused, and nothing changes ---- */
    fresh(&d, &rep);
    static uint8_t big[DATA * MAS_SECTOR];
    fill(big, sizeof(big), 3);
    const uint32_t before = d.seq;
    uint8_t hb[MAS_ASSET_HDR]; mah_t mb;
    mkhdr(hb, 1, "Big font", 1, big, 800000u > sizeof(big) ? (uint32_t)sizeof(big) : 0);
    CHECK(mah_parse(hb, sizeof(hb), "STKCHN01", 100, &mb) == MAS_OK);
    CHECK(mas_store(&OPS, NULL, sector, &d, &mb, -1, big, NULL) == MAS_OK);          /* exactly the whole data area */
    CHECK(mas_free_sectors(&d) == 0 && d.seq == before + 1);
    CHECK(install(&d, 4, "Quiz", 1, body_c, sizeof(body_c), -1) == MAS_E_FULL && d.seq == before + 1);

    /* ---- references come from the directory ---- */
    fresh(&d, &rep);
    CHECK(install(&d, 4, "Quiz", 1, body_a, sizeof(body_a), -1) == MAS_OK);
    uint8_t id_a[8]; memcpy(id_a, d.e[0].sha, 8);
    CHECK(mas_refs(&d, id_a) == 1);                                                  /* the active consumer */
    mkhdr(h, 5, "Chimes", 1, body_c, sizeof(body_c)); mah_parse(h, sizeof(h), "STKCHN01", 100, &m);
    uint8_t deps[MAS_DEPS][8]; memset(deps, 0, sizeof(deps)); memcpy(deps[0], id_a, 8);
    CHECK(mas_store(&OPS, NULL, sector, &d, &m, -1, body_c, deps) == MAS_OK);
    CHECK(mas_refs(&d, id_a) == 2);
    mas_scan(&OPS, NULL, sector, DATA, &back, &rep);
    CHECK(mas_refs(&back, id_a) == 2);                                               /* the same after a reboot: nothing stored */

    /* ---- wear: free space is handed out from a rotating start, so a swapped item moves along the region ---- */
    fresh(&d, &rep);
    int firsts[6];
    for (int i = 0; i < 6; i++) { CHECK(install(&d, 4, "Rot", (uint32_t)i + 1, body_a, sizeof(body_a), 0) == MAS_OK); firsts[i] = d.e[mas_find(&d, 4, 0)].first; }
    CHECK(firsts[0] == 0 && firsts[1] == 3 && firsts[2] == 6 && firsts[5] == 15);
    CHECK(d.pos == ((6u - 1u) % MAS_RING));                                                 /* each change wrote the next ring sector */

    /* ---- a damaged item is reported, and the others stay ---- */
    flash[(MAS_RING + (uint32_t)d.e[mas_find(&d, 4, 0)].first) * MAS_SECTOR + 5] ^= 0x40;
    mas_scan(&OPS, NULL, sector, DATA, &back, &rep);
    CHECK(rep.damaged[mas_find(&back, 4, 0)] == 1);

    /* ---- the power cut at every step of an install, a replace, a swap and a remove ---- */
    long total_steps = 0;
    for (int scenario = 0; scenario < 4; scenario++) {
        for (long cut = 0; cut < 40; cut++) {
            fresh(&d, &rep);
            CHECK(install(&d, 4, "Quiz", 1, body_a, sizeof(body_a), -1) == MAS_OK);
            CHECK(install(&d, 4, "Maze", 1, body_b, sizeof(body_b), -1) == MAS_OK);
            const uint32_t seq0 = d.seq;
            steps = 0; cut_at = cut; dead = 0;
            int r = MAS_OK;
            if (scenario == 0) r = install(&d, 4, "Extra", 1, body_c, sizeof(body_c), -1);
            if (scenario == 1) r = install(&d, 4, "Quiz", 2, body_b, sizeof(body_b), 0);
            if (scenario == 2) r = mas_swap(&OPS, NULL, sector, &d, 4, 1);
            if (scenario == 3) r = mas_remove(&OPS, NULL, sector, &d, 4, 0);
            const long used = steps;
            if (used > total_steps) total_steps = used;
            cut_at = -1; dead = 0;                                                  /* power back */
            mas_dir_t after; mas_report_t ar;
            mas_scan(&OPS, NULL, sector, DATA, &after, &ar);
            CHECK(ar.dir_found);
            for (unsigned i = 0; i < MAS_MAX_ENTRIES; i++) CHECK(!ar.damaged[i]);     /* every listed item is whole */
            CHECK(after.seq == seq0 || after.seq == seq0 + 1);
            if (after.seq == seq0) {                                                  /* the old set, untouched */
                CHECK(mas_find(&after, 4, 0) >= 0 && mas_find(&after, 4, 1) >= 0);
                CHECK(after.e[mas_find(&after, 4, 0)].version == 1 && after.e[mas_find(&after, 4, 0)].size == sizeof(body_a));
                CHECK(after.e[mas_active(&after, 4)].slot == 0);
            }
            if (r == MAS_OK) CHECK(after.seq == seq0 + 1);                            /* a change that reported success is there after the cut */
            if (cut >= used && r != MAS_OK) CHECK(0);                                 /* nothing was cut: it must have succeeded */
        }
    }
    CHECK(total_steps >= 4);
    printf(fails ? "assets_core_test FAILED\n" : "assets_core_test ok\n");
    return fails ? 1 : 0;
}
