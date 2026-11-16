/* Host test for the flash cache of the active pack (patch TB02): layout, checksum at boot, fallback, wear, and a power cut
 * at every step of a write. cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> packcache_core_test.c -lm. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_packcache_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

/* A NOR flash in RAM: erase sets a sector to 0xFF; a write can only clear bits (writing a 1 over a 0 is a violation,
 * counted); a power cut at operation N leaves that operation half done and every later one failing. */
static uint8_t flash[TPC_REGION_BYTES];
static long op_count, cut_at;
static int dead;
static int violations;
static int erase_count[TPC_REGION_BYTES / TPC_SECTOR];
static uint32_t rs = 4242;
static uint32_t rnd(void)
{
    rs = rs * 1664525u + 1013904223u;
    return rs >> 8;
}

static void flash_reset(void)
{
    memset(flash, 0xFF, sizeof(flash));
    op_count = 0;
    cut_at   = -1;
    dead     = 0;
    violations = 0;
    memset(erase_count, 0, sizeof(erase_count));
}

static int f_read(void* ctx, uint32_t off, uint8_t* buf, size_t len)
{
    (void)ctx;
    if (off + len > sizeof(flash)) return -1;
    memcpy(buf, flash + off, len);
    return 0;
}
static int f_erase(void* ctx, uint32_t off, size_t len)
{
    (void)ctx;
    if (dead || off % TPC_SECTOR != 0 || len % TPC_SECTOR != 0 || off + len > sizeof(flash)) return -1;
    if (op_count++ == cut_at) {
        dead = 1;
        for (size_t i = 0; i < len / 2; i++) flash[off + i] = 0xFF;        /* half erased */
        for (size_t i = len / 2; i < len; i++) flash[off + i] = (uint8_t)rnd(); /* and the rest undefined */
        return -1;
    }
    memset(flash + off, 0xFF, len);
    for (size_t s = 0; s < len / TPC_SECTOR; s++) erase_count[off / TPC_SECTOR + s]++;
    return 0;
}
static int f_write(void* ctx, uint32_t off, const uint8_t* buf, size_t len)
{
    (void)ctx;
    if (dead || off + len > sizeof(flash)) return -1;
    size_t n = len;
    int cutting = 0;
    if (op_count++ == cut_at) {
        dead    = 1;
        cutting = 1;
        n       = len / 3; /* a third made it */
    }
    for (size_t i = 0; i < n; i++) {
        const uint8_t r = (uint8_t)(flash[off + i] & buf[i]);
        if (r != buf[i]) violations++; /* tried to set a bit that is already cleared */
        flash[off + i] = r;
    }
    return cutting ? -1 : 0;
}
static void f_pause(void* ctx) { (void)ctx; }

static const tpc_ops_t OPS = {f_read, f_erase, f_write, f_pause};

static uint8_t scratch[TPC_SECTOR];
static uint8_t pack_a[1000000], pack_b[1000000], pack_c[400000];
static uint8_t sha_a[32], sha_b[32], sha_c[32];

static void fill(uint8_t* p, size_t n, uint8_t seed)
{
    for (size_t i = 0; i < n; i++) p[i] = (uint8_t)(seed * 37 + i * 13 + (i >> 5));
}
static void sha_of(const uint8_t* p, size_t n, uint8_t out[32])
{
    tpk_sha_t s;
    tpk_sha_init(&s);
    tpk_sha_update(&s, p, n);
    tpk_sha_final(&s, out);
}

/* what the cache says about `type` after a scan: 0 empty, else 1 + which of the three packs it is */
static int which(const tpc_dir_t* d, int type)
{
    if (!d->have[type]) return 0;
    if (memcmp(d->e[type].sha, sha_a, 32) == 0) return 1;
    if (memcmp(d->e[type].sha, sha_b, 32) == 0) return 2;
    if (memcmp(d->e[type].sha, sha_c, 32) == 0) return 3;
    return 99; /* a hybrid: never allowed */
}

int main(void)
{
    /* The region sits inside the partition and above the asset image (4,463,226 bytes in the built image). */
    CHECK(TPC_REGION_START + TPC_REGION_BYTES == TPC_ASSETS_PARTITION_BYTES);
    CHECK(TPC_REGION_START == 4653056u && TPC_REGION_START >= 4463226u + 100000u);
    CHECK(TPC_DATA_SECTORS == 382 && TPC_ENTRY_BYTES * TPK_TYPES + TPC_HDR_BYTES <= TPC_SECTOR);
    CHECK(sizeof(tpc_dir_t) < 800);

    fill(pack_a, sizeof(pack_a), 1);
    fill(pack_b, sizeof(pack_b), 2);
    fill(pack_c, sizeof(pack_c), 3);
    sha_of(pack_a, 100000, sha_a);
    sha_of(pack_b, 120000, sha_b);
    sha_of(pack_c, 50000, sha_c);

    /* An erased flash is an empty cache: every type is the built-in one, and the scan writes nothing. */
    flash_reset();
    tpc_dir_t d;
    tpc_report_t rep;
    tpc_scan(&OPS, NULL, scratch, &d, &rep);
    CHECK(!rep.dir_found && !rep.dir_corrupt && d.slot == 2);
    for (int t = 0; t < TPK_TYPES; t++) CHECK(!d.have[t] && rep.status[t] == TPC_ST_EMPTY);
    CHECK(op_count == 0);

    /* Store one, scan from cold: it is there, whole, with its name and version. */
    CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 3, pack_a, 100000, sha_a) == TPK_OK);
    tpc_dir_t d2;
    tpc_scan(&OPS, NULL, scratch, &d2, &rep);
    CHECK(rep.dir_found && rep.status[TPK_LOOK] == TPC_ST_OK && d2.have[TPK_LOOK] && which(&d2, TPK_LOOK) == 1);
    CHECK(strcmp(d2.e[TPK_LOOK].name, "Pixel") == 0 && d2.e[TPK_LOOK].version == 3 && d2.e[TPK_LOOK].size == 100000);
    CHECK(d2.e[TPK_LOOK].nsect == 25 && rep.status[TPK_FILLER] == TPC_ST_EMPTY);
    static uint8_t back[1000000];
    CHECK(tpc_read_pack(&OPS, NULL, &d2.e[TPK_LOOK], back) && memcmp(back, pack_a, 100000) == 0);
    CHECK(tpc_holds(&d2, TPK_LOOK, sha_a) && !tpc_holds(&d2, TPK_LOOK, sha_b) && !tpc_holds(&d2, TPK_FILLER, sha_a));

    /* Several types side by side, each in its own sectors. */
    CHECK(tpc_store(&OPS, NULL, scratch, &d2, TPK_FILLER, "Fillers en", 1, pack_c, 50000, sha_c) == TPK_OK);
    CHECK(tpc_store(&OPS, NULL, scratch, &d2, TPK_GAME, "Memory", 1, pack_c, 50000, sha_c) == TPK_OK);
    tpc_scan(&OPS, NULL, scratch, &d, &rep);
    CHECK(rep.status[TPK_LOOK] == TPC_ST_OK && rep.status[TPK_FILLER] == TPC_ST_OK && rep.status[TPK_GAME] == TPC_ST_OK);
    CHECK(!tpc_overlap(&d.e[TPK_LOOK], &d.e[TPK_FILLER]) && !tpc_overlap(&d.e[TPK_FILLER], &d.e[TPK_GAME]) && !tpc_overlap(&d.e[TPK_LOOK], &d.e[TPK_GAME]));
    CHECK(violations == 0);

    /* The gates: wrong type, a bad name, zero, over the gate for the type, no room. */
    CHECK(tpc_store(&OPS, NULL, scratch, &d, 9, "X", 1, pack_a, 10, sha_a) == TPK_ERR_TYPE);
    CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "bad/name", 1, pack_a, 10, sha_a) == TPK_ERR_NAME);
    CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "X", 1, pack_a, 0, sha_a) == TPK_ERR_SIZE);
    CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_DANCE, "X", 1, pack_a, 100001, sha_a) == TPK_ERR_SIZE);
    CHECK(tpc_remove(&OPS, NULL, scratch, &d, 12) == TPK_ERR_TYPE);

    /* Remove: only the directory is written; removing what is not held writes nothing. */
    {
        const long before = op_count;
        CHECK(tpc_remove(&OPS, NULL, scratch, &d, TPK_SOUND) == TPK_OK && op_count == before);
        CHECK(tpc_remove(&OPS, NULL, scratch, &d, TPK_GAME) == TPK_OK && op_count == before + 2); /* erase + write of one directory sector */
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        CHECK(!d.have[TPK_GAME] && rep.status[TPK_GAME] == TPC_ST_EMPTY && rep.status[TPK_LOOK] == TPC_ST_OK);
    }

    /* Wear: the directory alternates between its two sectors, so neither is erased more than once more than the other. */
    flash_reset();
    tpc_scan(&OPS, NULL, scratch, &d, &rep);
    for (int i = 0; i < 40; i++) {
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", (uint32_t)i, (i % 2) ? pack_a : pack_b, (i % 2) ? 100000 : 120000, (i % 2) ? sha_a : sha_b) == TPK_OK);
    }
    CHECK(abs(erase_count[0] - erase_count[1]) <= 1 && erase_count[0] >= 19);
    CHECK(violations == 0);
    /* The data sectors rotate too: one run is reused only while it is the one holding the old pack... the point is that
     * no single data sector takes all 40 writes. */
    int worst = 0;
    for (int s = TPC_DIR_SECTORS; s < (int)(TPC_REGION_BYTES / TPC_SECTOR); s++) if (erase_count[s] > worst) worst = erase_count[s];
    CHECK(worst <= 20);
    printf("  after 40 changes: directory erases %d and %d, busiest data sector %d\n", erase_count[0], erase_count[1], worst);

    /* The same pack again writes nothing (the caller asks tpc_holds first). */
    CHECK(tpc_holds(&d, TPK_LOOK, sha_a) || tpc_holds(&d, TPK_LOOK, sha_b));

    /* Damage found at boot. A flipped bit in one pack's data: that type is built-in again, the others stay. */
    flash_reset();
    tpc_scan(&OPS, NULL, scratch, &d, &rep);
    CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, pack_a, 100000, sha_a) == TPK_OK);
    CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_FILLER, "Fillers en", 1, pack_c, 50000, sha_c) == TPK_OK);
    {
        const uint32_t at = TPC_DIR_SECTORS * TPC_SECTOR + (uint32_t)d.e[TPK_LOOK].first * TPC_SECTOR + 5000;
        flash[at] ^= 0x10;
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(rep.status[TPK_LOOK] == TPC_ST_DAMAGED && !d2.have[TPK_LOOK]);
        CHECK(rep.status[TPK_FILLER] == TPC_ST_OK && d2.have[TPK_FILLER]);
        flash[at] ^= 0x10;
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(rep.status[TPK_LOOK] == TPC_ST_OK);
    }
    /* A damaged directory sector falls back to the other one (the previous set of packs); both damaged: all built-in. */
    {
        const int cur = d.slot;
        flash[cur * TPC_SECTOR + 20] ^= 0x01;
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(rep.dir_found && rep.dir_corrupt && d2.slot == (uint8_t)(1 - cur));
        CHECK(rep.status[TPK_LOOK] == TPC_ST_OK && !d2.have[TPK_FILLER]); /* the older directory knows only the look */
        flash[(1 - cur) * TPC_SECTOR + 20] ^= 0x01;
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(!rep.dir_found && rep.dir_corrupt);
        for (int t = 0; t < TPK_TYPES; t++) CHECK(!d2.have[t]);
        flash[cur * TPC_SECTOR + 20] ^= 0x01;
        flash[(1 - cur) * TPC_SECTOR + 20] ^= 0x01;
    }
    /* A directory that names overlapping packs, a size that does not fit its sectors, a run outside the area, or a name
     * that is not a name: every one is "damaged", never trusted. */
    {
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        tpc_dir_t bad = d;
        bad.e[TPK_FILLER].first = bad.e[TPK_LOOK].first; /* same sectors as the look */
        static uint8_t sec[TPC_SECTOR];
        tpc_encode(&bad, sec);
        const int target = d.slot == 0 ? 1 : 0;
        memset(flash + target * TPC_SECTOR, 0xFF, TPC_SECTOR);
        memcpy(flash + target * TPC_SECTOR, sec, TPC_SECTOR);
        bad.seq = d.seq; /* encode used d.seq; make the crafted one newer */
        flash_reset();
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, pack_a, 100000, sha_a) == TPK_OK);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_FILLER, "Fillers en", 1, pack_c, 50000, sha_c) == TPK_OK);
        tpc_dir_t evil = d;
        evil.e[TPK_FILLER].first = evil.e[TPK_LOOK].first;
        evil.seq++;
        tpc_encode(&evil, sec);
        const int t2 = d.slot == 0 ? 1 : 0;
        memset(flash + t2 * TPC_SECTOR, 0xFF, TPC_SECTOR);
        memcpy(flash + t2 * TPC_SECTOR, sec, TPC_SECTOR);
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(rep.status[TPK_LOOK] == TPC_ST_OK && rep.status[TPK_FILLER] == TPC_ST_DAMAGED);
        evil = d;
        evil.e[TPK_FILLER].nsect = 3; /* size 50000 needs 13 sectors */
        evil.seq += 2;
        tpc_encode(&evil, sec);
        memset(flash + d.slot * TPC_SECTOR, 0xFF, TPC_SECTOR);
        memcpy(flash + d.slot * TPC_SECTOR, sec, TPC_SECTOR);
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(rep.status[TPK_FILLER] == TPC_ST_DAMAGED && rep.status[TPK_LOOK] == TPC_ST_OK);
        evil = d;
        evil.e[TPK_FILLER].first = (uint16_t)(TPC_DATA_SECTORS - 2); /* runs off the end */
        evil.seq += 4;
        tpc_encode(&evil, sec);
        memset(flash + d.slot * TPC_SECTOR, 0xFF, TPC_SECTOR);
        memcpy(flash + d.slot * TPC_SECTOR, sec, TPC_SECTOR);
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(rep.status[TPK_FILLER] == TPC_ST_DAMAGED);
    }
    /* Random damage to a quarter megabyte of an otherwise good cache: the scan never trusts a pack whose bytes are not the
     * ones its checksum names. */
    {
        flash_reset();
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, pack_a, 100000, sha_a) == TPK_OK);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_FILLER, "Fillers en", 1, pack_c, 50000, sha_c) == TPK_OK);
        static uint8_t saved[TPC_REGION_BYTES];
        memcpy(saved, flash, sizeof(flash));
        int trusted_wrong = 0;
        for (int k = 0; k < 3000; k++) {
            memcpy(flash, saved, sizeof(flash));
            const int hits = 1 + (int)(rnd() % 4);
            for (int i = 0; i < hits; i++) flash[rnd() % (TPC_DIR_SECTORS * TPC_SECTOR + 200 * TPC_SECTOR)] ^= (uint8_t)(1u << (rnd() % 8));
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            for (int t = 0; t < TPK_TYPES; t++) {
                if (!d2.have[t]) continue;
                const int w = which(&d2, t);
                if (w == 99) trusted_wrong++;
                if (!tpc_verify(&OPS, NULL, &d2.e[t])) trusted_wrong++;
            }
        }
        CHECK(trusted_wrong == 0);
    }

    /* POWER CUT at every step of replacing a pack, with room for both. After the reboot the type is the old pack, the new
     * pack, or empty: never a mixture; the other types are never touched; the next write works. */
    {
        int outcomes[4] = {0, 0, 0, 0};
        for (long cut = 0; cut < 68; cut++) {
            flash_reset();
            tpc_scan(&OPS, NULL, scratch, &d, &rep);
            CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, pack_a, 100000, sha_a) == TPK_OK);
            CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_FILLER, "Fillers en", 1, pack_c, 50000, sha_c) == TPK_OK);
            op_count = 0;
            cut_at   = cut;
            tpc_dir_t work = d;
            const tpk_err_t r = tpc_store(&OPS, NULL, scratch, &work, TPK_LOOK, "Pixel", 2, pack_b, 120000, sha_b);
            dead   = 0; /* the power is back */
            cut_at = -1;
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            const int w = which(&d2, TPK_LOOK);
            CHECK(w == 1 || w == 2 || w == 0);
            CHECK(which(&d2, TPK_FILLER) == 3 && rep.status[TPK_FILLER] == TPC_ST_OK);
            if (r == TPK_OK) CHECK(w == 2);
            outcomes[w]++;
            /* and the next change works from here */
            CHECK(tpc_store(&OPS, NULL, scratch, &d2, TPK_LOOK, "Pixel", 3, pack_a, 100000, sha_a) == TPK_OK);
            tpc_scan(&OPS, NULL, scratch, &d, &rep);
            CHECK(which(&d, TPK_LOOK) == 1 && which(&d, TPK_FILLER) == 3);
            CHECK(violations == 0);
        }
        printf("  cut while replacing (room for both): old %d, new %d, empty %d\n", outcomes[1], outcomes[2], outcomes[0]);
        CHECK(outcomes[1] > 0 && outcomes[2] > 0);
        CHECK(outcomes[0] == 0); /* with room for both the old pack is never lost */
    }

    /* POWER CUT with no room for both (a 1,000,000 byte look beside a 400,000 byte filler): the old look is dropped first, so
     * a cut leaves the built-in look, or the new one; never a half, and never the old look with its sectors overwritten. */
    {
        static uint8_t big_a[1000000], big_b[1000000];
        static uint8_t sa[32], sb[32], sf[32];
        fill(big_a, sizeof(big_a), 5);
        fill(big_b, sizeof(big_b), 6);
        sha_of(big_a, 1000000, sa);
        sha_of(big_b, 1000000, sb);
        sha_of(big_a, 400000, sf);
        int outcomes[4] = {0, 0, 0, 0};
        for (long cut = 0; cut < 520; cut += (cut < 12 || cut > 485) ? 1 : 9) {
            flash_reset();
            tpc_scan(&OPS, NULL, scratch, &d, &rep);
            CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, big_a, 1000000, sa) == TPK_OK);
            CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_FILLER, "Fillers en", 1, big_a, 400000, sf) == TPK_OK);
            op_count = 0;
            cut_at   = cut;
            tpc_dir_t work = d;
            const tpk_err_t r = tpc_store(&OPS, NULL, scratch, &work, TPK_LOOK, "Pixel", 2, big_b, 1000000, sb);
            dead   = 0;
            cut_at = -1;
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            int w = 0;
            if (d2.have[TPK_LOOK]) w = memcmp(d2.e[TPK_LOOK].sha, sa, 32) == 0 ? 1 : memcmp(d2.e[TPK_LOOK].sha, sb, 32) == 0 ? 2 : 99;
            CHECK(w == 0 || w == 1 || w == 2); /* old only when the cut came before the directory dropped it, and then it is whole (scan checks) */
            CHECK(d2.have[TPK_FILLER] && rep.status[TPK_FILLER] == TPC_ST_OK && memcmp(d2.e[TPK_FILLER].sha, sf, 32) == 0);
            if (r == TPK_OK) CHECK(w == 2);
            outcomes[w]++;
            CHECK(tpc_store(&OPS, NULL, scratch, &d2, TPK_LOOK, "Pixel", 4, big_b, 1000000, sb) == TPK_OK);
            tpc_scan(&OPS, NULL, scratch, &d, &rep);
            CHECK(d.have[TPK_LOOK] && d.have[TPK_FILLER] && memcmp(d.e[TPK_LOOK].sha, sb, 32) == 0);
        }
        printf("  cut while replacing (no room for both): old %d, new %d, empty %d\n", outcomes[1], outcomes[2], outcomes[0]);
        CHECK(outcomes[0] > 0 && outcomes[2] > 0 && outcomes[1] <= 2);
        CHECK(violations == 0);
    }

    /* A cache with no room at all for another pack says so in plain terms and writes nothing. */
    {
        static uint8_t sa[32];
        flash_reset();
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        sha_of(pack_a, 1000000, sa);
        uint8_t sf[32];
        sha_of(pack_a, 400000, sf);
        uint8_t sd[32];
        sha_of(pack_a, 100000, sd);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, pack_a, 1000000, sa) == TPK_OK);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_FILLER, "Fillers en", 1, pack_a, 400000, sf) == TPK_OK);
        /* 245 + 98 sectors used of 382: 39 free. A 200,000 byte language pack (49 sectors) does not fit. */
        const long before = op_count;
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LANGUAGE, "Spanish", 1, pack_a, 200000, sa) == TPK_ERR_FULL);
        CHECK(op_count == before);
        CHECK(strstr(tpk_say(TPK_ERR_FULL, 0), "storage is full") != NULL && strstr(tpk_say(TPK_ERR_FULL, 1), "lleno") != NULL);
        /* a small one does */
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_DANCE, "Waltz", 1, pack_a, 100000, sd) == TPK_OK);
    }

    CHECK(violations == 0);
    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
