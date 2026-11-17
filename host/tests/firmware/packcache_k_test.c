/* Host test for the pack cache with the phrase type and the format 2 directory (patch K10): the new type beside the old ones,
 * a format 1 directory (six types) still read, and a power cut at EVERY flash operation while a language pack, a phrase pack and
 * a look are written, replaced and removed. Same flash model as packcache_core_test.c (a write can only clear bits; a cut leaves
 * the operation half done). cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> packcache_k_test.c -lm. */
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
static uint8_t blob_look[300000], blob_filler[200000], blob_phrase[60000], blob_phrase2[61000], blob_lang[1500], blob_lang2[900];
static uint8_t sha_look[32], sha_filler[32], sha_phrase[32], sha_phrase2[32], sha_lang[32], sha_lang2[32];

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

/* What the old firmware (patch TB02) wrote: format 1, six entries, the checksum over six entries. */
static void encode_legacy(const tpc_dir_t* d, uint8_t out[TPC_SECTOR])
{
    memset(out, 0xFF, TPC_SECTOR);
    uint8_t count = 0;
    for (int t = 0; t < TPK_LEGACY_TYPES; t++) count += d->have[t] ? 1 : 0;
    tpc_put32(out, TPC_MAGIC);
    tpc_put16(out + 4, 1);
    tpc_put16(out + 6, count);
    tpc_put32(out + 8, d->seq);
    tpc_put32(out + 12, 0);
    for (int t = 0; t < TPK_LEGACY_TYPES; t++) {
        uint8_t* p = out + TPC_HDR_BYTES + (size_t)t * TPC_ENTRY_BYTES;
        memset(p, 0xFF, TPC_ENTRY_BYTES);
        if (!d->have[t]) continue;
        const tpc_entry_t* e = &d->e[t];
        p[0] = e->type;
        p[1] = e->name_len;
        tpc_put16(p + 2, e->first);
        tpc_put16(p + 4, e->nsect);
        tpc_put16(p + 6, 0);
        tpc_put32(p + 8, e->version);
        tpc_put32(p + 12, e->size);
        memcpy(p + 16, e->sha, 32);
        memset(p + 48, 0, TPK_NAME_MAX + 1);
        memcpy(p + 48, e->name, e->name_len);
        memset(p + 89, 0, 7);
    }
    tpc_put32(out + 12, tpk_crc32(0, out, TPC_HDR_BYTES + TPK_LEGACY_TYPES * TPC_ENTRY_BYTES));
}

static int holds_sha(const tpc_dir_t* d, int type, const uint8_t sha[32]) { return d->have[type] && memcmp(d->e[type].sha, sha, 32) == 0; }

/* a stored pack reads back byte for byte */
static int reads_back(const tpc_dir_t* d, int type, const uint8_t* want, size_t n)
{
    static uint8_t buf[400000];
    if (!d->have[type] || d->e[type].size != n) return 0;
    return tpc_read_pack(&OPS, NULL, &d->e[type], buf) && memcmp(buf, want, n) == 0;
}

static void load_set(tpc_dir_t* d)
{
    /* look (300 KB), filler (200 KB), language (1.5 KB), phrase (60 KB) */
    tpc_report_t rep;
    flash_reset();
    tpc_scan(&OPS, NULL, scratch, d, &rep);
    CHECK(tpc_store(&OPS, NULL, scratch, d, TPK_LOOK, "Pixel", 1, blob_look, sizeof(blob_look), sha_look) == TPK_OK);
    CHECK(tpc_store(&OPS, NULL, scratch, d, TPK_FILLER, "Fillers en", 1, blob_filler, sizeof(blob_filler), sha_filler) == TPK_OK);
    CHECK(tpc_store(&OPS, NULL, scratch, d, TPK_LANGUAGE, "Francais", 1, blob_lang, sizeof(blob_lang), sha_lang) == TPK_OK);
    CHECK(tpc_store(&OPS, NULL, scratch, d, TPK_PHRASE, "Phrases en", 1, blob_phrase, sizeof(blob_phrase), sha_phrase) == TPK_OK);
}

int main(void)
{
    tpc_dir_t d, d2;
    tpc_report_t rep;
    fill(blob_look, sizeof(blob_look), 1);
    fill(blob_filler, sizeof(blob_filler), 2);
    fill(blob_phrase, sizeof(blob_phrase), 3);
    fill(blob_phrase2, sizeof(blob_phrase2), 4);
    fill(blob_lang, sizeof(blob_lang), 5);
    fill(blob_lang2, sizeof(blob_lang2), 6);
    sha_of(blob_look, sizeof(blob_look), sha_look);
    sha_of(blob_filler, sizeof(blob_filler), sha_filler);
    sha_of(blob_phrase, sizeof(blob_phrase), sha_phrase);
    sha_of(blob_phrase2, sizeof(blob_phrase2), sha_phrase2);
    sha_of(blob_lang, sizeof(blob_lang), sha_lang);
    sha_of(blob_lang2, sizeof(blob_lang2), sha_lang2);

    /* The new type: its place in the tables, its gate, and a directory that still fits one sector. */
    CHECK(TPK_PHRASE == 6 && TPK_TYPES == 7 && TPK_LEGACY_TYPES == 6 && TPC_FORMAT == 2 && TPC_FORMAT_LEGACY == 1);
    CHECK(strcmp(TPK_TYPE_NAMES[TPK_PHRASE], "phrase") == 0 && tpk_type_by_name("phrase") == TPK_PHRASE);
    CHECK(TPK_MAX_BYTES[TPK_PHRASE] == 150000u);
    CHECK(TPC_ENTRY_BYTES * TPK_TYPES + TPC_HDR_BYTES <= TPC_SECTOR && sizeof(tpc_dir_t) < 900);
    CHECK(strstr(tpk_say(TPK_ERR_TYPE, 0), "phrase") != NULL && strstr(tpk_say(TPK_ERR_TYPE, 1), "phrase") != NULL);
    /* the gate: 150,000 is the most, 150,001 is refused, a name rule applies as for the others */
    {
        flash_reset();
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        static uint8_t big[150001];
        fill(big, sizeof(big), 9);
        uint8_t sb[32], sb1[32];
        sha_of(big, 150001, sb1);
        sha_of(big, 150000, sb);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_PHRASE, "Phrases en", 1, big, 150001, sb1) == TPK_ERR_SIZE);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_PHRASE, "Phrases en", 1, big, 150000, sb) == TPK_OK);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_PHRASE, "bad/name", 1, big, 1000, sb) == TPK_ERR_NAME);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_PHRASE, "Phrases en", 1, big, 0, sb) == TPK_ERR_SIZE);
    }

    /* All four types side by side, from a cold scan: each whole, each in its own sectors, nothing overlapping. */
    load_set(&d);
    tpc_scan(&OPS, NULL, scratch, &d2, &rep);
    CHECK(rep.status[TPK_LOOK] == TPC_ST_OK && rep.status[TPK_FILLER] == TPC_ST_OK && rep.status[TPK_LANGUAGE] == TPC_ST_OK && rep.status[TPK_PHRASE] == TPC_ST_OK);
    CHECK(reads_back(&d2, TPK_LOOK, blob_look, sizeof(blob_look)) && reads_back(&d2, TPK_FILLER, blob_filler, sizeof(blob_filler)));
    CHECK(reads_back(&d2, TPK_LANGUAGE, blob_lang, sizeof(blob_lang)) && reads_back(&d2, TPK_PHRASE, blob_phrase, sizeof(blob_phrase)));
    CHECK(!tpc_overlap(&d2.e[TPK_LANGUAGE], &d2.e[TPK_PHRASE]) && !tpc_overlap(&d2.e[TPK_PHRASE], &d2.e[TPK_FILLER]) && !tpc_overlap(&d2.e[TPK_LOOK], &d2.e[TPK_PHRASE]));
    CHECK(violations == 0);
    CHECK(flash[4] == 2); /* the directory the new firmware writes is format 2 (the current slot is 0 or 1, both carry the format) */

    /* A format 1 directory written by the old firmware is read: the look and the filler pack survive, the new types are empty,
     * and the first write after the update leaves a format 2 directory that still names the old packs. */
    {
        flash_reset();
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, blob_look, sizeof(blob_look), sha_look) == TPK_OK);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_FILLER, "Fillers en", 1, blob_filler, sizeof(blob_filler), sha_filler) == TPK_OK);
        d.seq += 1;
        uint8_t legacy[TPC_SECTOR];
        encode_legacy(&d, legacy);
        /* put it in the slot the other directory is not in, as the old firmware would have (newest wins) */
        const int slot = d.slot == 0 ? 1 : 0;
        for (size_t i = 0; i < TPC_SECTOR; i++) flash[(size_t)slot * TPC_SECTOR + i] = 0xFF;
        memcpy(flash + (size_t)slot * TPC_SECTOR, legacy, TPC_SECTOR);
        d.seq += 0;
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(rep.dir_found && rep.status[TPK_LOOK] == TPC_ST_OK && rep.status[TPK_FILLER] == TPC_ST_OK);
        CHECK(rep.status[TPK_LANGUAGE] == TPC_ST_EMPTY && rep.status[TPK_PHRASE] == TPC_ST_EMPTY && !d2.have[TPK_PHRASE]);
        CHECK(reads_back(&d2, TPK_LOOK, blob_look, sizeof(blob_look)) && reads_back(&d2, TPK_FILLER, blob_filler, sizeof(blob_filler)));
        CHECK(tpc_store(&OPS, NULL, scratch, &d2, TPK_PHRASE, "Phrases en", 1, blob_phrase, sizeof(blob_phrase), sha_phrase) == TPK_OK);
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        CHECK(holds_sha(&d, TPK_LOOK, sha_look) && holds_sha(&d, TPK_FILLER, sha_filler) && holds_sha(&d, TPK_PHRASE, sha_phrase));
        CHECK(flash[(size_t)d.slot * TPC_SECTOR + 4] == 2);
        CHECK(violations == 0);
        /* a damaged legacy directory (one flipped bit in an entry) is refused like any damaged one */
        flash_reset();
        tpc_scan(&OPS, NULL, scratch, &d, &rep);
        CHECK(tpc_store(&OPS, NULL, scratch, &d, TPK_LOOK, "Pixel", 1, blob_look, sizeof(blob_look), sha_look) == TPK_OK);
        d.seq += 1;
        encode_legacy(&d, legacy);
        legacy[TPC_HDR_BYTES + 20] ^= 0x04;
        for (int s = 0; s < 2; s++) { for (size_t i = 0; i < TPC_SECTOR; i++) flash[(size_t)s * TPC_SECTOR + i] = 0xFF; }
        memcpy(flash, legacy, TPC_SECTOR);
        tpc_scan(&OPS, NULL, scratch, &d2, &rep);
        CHECK(!rep.dir_found && !d2.have[TPK_LOOK]);
    }

    /* POWER CUT at every single flash operation while the phrase pack is replaced (with every other type held). After the
     * reboot the phrase type is the old pack, the new pack or empty, never a mixture, and the other three types are whole. */
    {
        int outcomes[3] = {0, 0, 0}; /* old, new, empty */
        long ops_total  = 0;
        for (long cut = 0; cut < 200; cut++) {
            load_set(&d);
            op_count       = 0;
            cut_at         = cut;
            tpc_dir_t work = d;
            const tpk_err_t r = tpc_store(&OPS, NULL, scratch, &work, TPK_PHRASE, "Phrases en", 2, blob_phrase2, sizeof(blob_phrase2), sha_phrase2);
            const long used = op_count;
            dead   = 0;
            cut_at = -1;
            if (r == TPK_OK && used <= cut) { ops_total = used; break; } /* the cut point is past the end: every earlier one was tried */
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            const int is_old = holds_sha(&d2, TPK_PHRASE, sha_phrase), is_new = holds_sha(&d2, TPK_PHRASE, sha_phrase2);
            CHECK((is_old ? 1 : 0) + (is_new ? 1 : 0) + (!d2.have[TPK_PHRASE] ? 1 : 0) == 1);
            if (is_old) CHECK(reads_back(&d2, TPK_PHRASE, blob_phrase, sizeof(blob_phrase)) && rep.status[TPK_PHRASE] == TPC_ST_OK);
            if (is_new) CHECK(reads_back(&d2, TPK_PHRASE, blob_phrase2, sizeof(blob_phrase2)) && rep.status[TPK_PHRASE] == TPC_ST_OK);
            CHECK(reads_back(&d2, TPK_LOOK, blob_look, sizeof(blob_look)) && reads_back(&d2, TPK_FILLER, blob_filler, sizeof(blob_filler)));
            CHECK(reads_back(&d2, TPK_LANGUAGE, blob_lang, sizeof(blob_lang)));
            outcomes[is_old ? 0 : is_new ? 1 : 2]++;
            /* the next change works from here, and the new pack is whole afterwards */
            CHECK(tpc_store(&OPS, NULL, scratch, &d2, TPK_PHRASE, "Phrases en", 3, blob_phrase2, sizeof(blob_phrase2), sha_phrase2) == TPK_OK);
            tpc_scan(&OPS, NULL, scratch, &d, &rep);
            CHECK(reads_back(&d, TPK_PHRASE, blob_phrase2, sizeof(blob_phrase2)));
            CHECK(violations == 0);
        }
        printf("  cut at every one of %ld operations replacing a phrase pack: old %d, new %d, empty %d\n", ops_total, outcomes[0], outcomes[1], outcomes[2]);
        CHECK(ops_total > 30 && outcomes[0] > 0 && outcomes[1] > 0 && outcomes[2] == 0); /* room for both: the old pack is never lost */
    }

    /* The same sweep for a language pack (one sector, the common case) and for the first write of each new type, and for a remove. */
    {
        int old_n = 0, new_n = 0, none_n = 0;
        for (long cut = 0; cut < 12; cut++) {
            load_set(&d);
            op_count       = 0;
            cut_at         = cut;
            tpc_dir_t work = d;
            (void)tpc_store(&OPS, NULL, scratch, &work, TPK_LANGUAGE, "Deutsch", 2, blob_lang2, sizeof(blob_lang2), sha_lang2);
            dead   = 0;
            cut_at = -1;
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            const int is_old = holds_sha(&d2, TPK_LANGUAGE, sha_lang), is_new = holds_sha(&d2, TPK_LANGUAGE, sha_lang2);
            CHECK((is_old ? 1 : 0) + (is_new ? 1 : 0) == 1); /* a language pack is never half there and never gone */
            CHECK(reads_back(&d2, TPK_PHRASE, blob_phrase, sizeof(blob_phrase)));
            old_n += is_old;
            new_n += is_new;
        }
        CHECK(old_n > 0 && new_n > 0);
        for (long cut = 0; cut < 40; cut++) { /* the first write of a phrase pack, nothing held before */
            flash_reset();
            tpc_scan(&OPS, NULL, scratch, &d, &rep);
            op_count       = 0;
            cut_at         = cut;
            tpc_dir_t work = d;
            const tpk_err_t r = tpc_store(&OPS, NULL, scratch, &work, TPK_PHRASE, "Phrases en", 1, blob_phrase, sizeof(blob_phrase), sha_phrase);
            const long used = op_count;
            dead   = 0;
            cut_at = -1;
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            if (d2.have[TPK_PHRASE]) CHECK(reads_back(&d2, TPK_PHRASE, blob_phrase, sizeof(blob_phrase))); else none_n++;
            if (r == TPK_OK) CHECK(d2.have[TPK_PHRASE]);
            if (r == TPK_OK && used <= cut) break;
        }
        CHECK(none_n > 0);
        for (long cut = 0; cut < 4; cut++) { /* a remove is one directory write: the pack is there or gone, the rest is untouched */
            load_set(&d);
            op_count       = 0;
            cut_at         = cut;
            tpc_dir_t work = d;
            (void)tpc_remove(&OPS, NULL, scratch, &work, TPK_PHRASE);
            dead   = 0;
            cut_at = -1;
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            if (d2.have[TPK_PHRASE]) CHECK(reads_back(&d2, TPK_PHRASE, blob_phrase, sizeof(blob_phrase)));
            CHECK(reads_back(&d2, TPK_LOOK, blob_look, sizeof(blob_look)) && reads_back(&d2, TPK_LANGUAGE, blob_lang, sizeof(blob_lang)));
        }
        CHECK(violations == 0);
    }

    /* Damage found at boot: one flipped bit in the language pack's sector, and in the phrase pack's, makes only that type built-in. */
    {
        for (int which_type = 0; which_type < 2; which_type++) {
            const int type = which_type ? TPK_PHRASE : TPK_LANGUAGE;
            load_set(&d);
            const uint32_t at = TPC_DIR_SECTORS * TPC_SECTOR + (uint32_t)d.e[type].first * TPC_SECTOR + 7;
            flash[at] ^= 0x10;
            tpc_scan(&OPS, NULL, scratch, &d2, &rep);
            CHECK(rep.status[type] == TPC_ST_DAMAGED && !d2.have[type]);
            CHECK(reads_back(&d2, TPK_LOOK, blob_look, sizeof(blob_look)) && reads_back(&d2, TPK_FILLER, blob_filler, sizeof(blob_filler)));
            CHECK(rep.status[which_type ? TPK_LANGUAGE : TPK_PHRASE] == TPC_ST_OK);
        }
    }

    CHECK(violations == 0);
    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
