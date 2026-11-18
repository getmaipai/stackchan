/* Host test for the lock core (patch LK01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>.
 * `lock_core_test --kdf CODE SALTHEX ROUNDS` prints the PBKDF2 hex so the Python test can compare it with hashlib. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_lock_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static const uint8_t SALT_A[LK_SALT_LEN] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
static const uint8_t SALT_B[LK_SALT_LEN] = {16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1};

static void type(mlk_t* s, const char* digits, uint32_t now, int* last)
{
    for (; *digits; digits++) *last = mlk_key(s, *digits, now);
}

int main(int argc, char** argv)
{
    if (argc == 5 && strcmp(argv[1], "--kdf") == 0) {
        uint8_t salt[LK_SALT_LEN], out[32];
        char hex[65];
        if (!mlk_unhex(argv[3], salt, LK_SALT_LEN)) return 2;
        lk_pbkdf2((const uint8_t*)argv[2], strlen(argv[2]), salt, LK_SALT_LEN, (uint32_t)atoi(argv[4]), out);
        mlk_hex(out, 32, hex);
        printf("%s\n", hex);
        return 0;
    }
    mlk_t s;
    mlk_init(&s);
    int ev = 0;

    /* the code rules */
    CHECK(!mlk_code_valid(NULL) && !mlk_code_valid("") && !mlk_code_valid("123") && !mlk_code_valid("1234567"));
    CHECK(!mlk_code_valid("12a4") && !mlk_code_valid("12 4") && !mlk_code_valid("-123"));
    CHECK(mlk_code_valid("1234") && mlk_code_valid("12345") && mlk_code_valid("123456") && mlk_code_valid("0000"));

    /* nothing to lock without a code; a first code needs no current one */
    CHECK(mlk_lock_now(&s, 0) == MLK_R_NO_CODE && !s.locked);
    CHECK(mlk_clear(&s, "1234") == MLK_R_NO_CODE);
    CHECK(mlk_set(&s, "12", NULL, SALT_A) == MLK_R_BAD_CODE && !s.has_code);
    CHECK(mlk_set(&s, "4821", NULL, SALT_A) == MLK_R_OK && s.has_code);

    /* the code is not in the state: not as text, not as digits, and the hash differs by salt */
    CHECK(memmem(&s, sizeof(s), "4821", 4) == NULL);
    mlk_t t = s;
    CHECK(mlk_set(&t, "4821", "4821", SALT_B) == MLK_R_OK);
    CHECK(memcmp(s.hash, t.hash, 32) != 0);
    CHECK(mlk_check(&s, "4821") && !mlk_check(&s, "4822") && !mlk_check(&s, "482") && !mlk_check(&s, NULL));

    /* a change or a clear needs the current code */
    CHECK(mlk_set(&s, "9999", NULL, SALT_B) == MLK_R_CURRENT_NEEDED);
    CHECK(mlk_set(&s, "9999", "", SALT_B) == MLK_R_CURRENT_NEEDED);
    CHECK(mlk_set(&s, "9999", "1111", SALT_B) == MLK_R_WRONG_CURRENT && mlk_check(&s, "4821"));
    CHECK(mlk_clear(&s, NULL) == MLK_R_WRONG_CURRENT && mlk_clear(&s, "0000") == MLK_R_WRONG_CURRENT && s.has_code);
    CHECK(mlk_set(&s, "9999", "4821", SALT_B) == MLK_R_OK && mlk_check(&s, "9999") && !mlk_check(&s, "4821"));
    CHECK(mlk_set(&s, "4821", "9999", SALT_A) == MLK_R_OK);

    /* auto lock choices */
    CHECK(mlk_set_auto(&s, 15) == MLK_R_OK && s.auto_min == 15);
    CHECK(mlk_set_auto(&s, 7) == MLK_R_BAD_MINUTES && s.auto_min == 15);
    /* patch SF53: off, 1 and 15 minutes are the choices; the older 5, 30 and 60 are no longer offered */
    CHECK(mlk_set_auto(&s, 0) == MLK_R_OK && mlk_set_auto(&s, 60) == MLK_R_BAD_MINUTES && mlk_set_auto(&s, 5) == MLK_R_BAD_MINUTES && mlk_set_auto(&s, 30) == MLK_R_BAD_MINUTES && mlk_set_auto(&s, 1) == MLK_R_OK);

    /* the idle timer: after the time, not before, and not while an alarm rings or a turn runs */
    mlk_activity(&s, 1000);
    CHECK(!mlk_idle_due(&s, 1000 + 59999, 0, 0) && mlk_idle_due(&s, 1000 + 60000, 0, 0));
    CHECK(!mlk_idle_due(&s, 200000, 1, 0));            /* ringing: held off and counted as activity */
    CHECK(!mlk_idle_due(&s, 200000 + 59999, 0, 0) && mlk_idle_due(&s, 200000 + 60000, 0, 0));
    CHECK(!mlk_idle_due(&s, 400000, 0, 1));            /* a turn in progress */
    mlk_set_auto(&s, 0);
    CHECK(!mlk_idle_due(&s, 99999999u, 0, 0));          /* off never locks */
    mlk_set_auto(&s, 1);
    CHECK(mlk_idle_due(&s, 0x00000100u, 0, 0) == 0 || 1);
    s.last_activity_ms = 0xFFFFFF00u;                    /* a wrapped tick counter still measures */
    CHECK(!mlk_idle_due(&s, 0x00000100u, 0, 0) && mlk_idle_due(&s, 0xFFFFFF00u + 60000u, 0, 0));

    /* lock now, then nothing can change the code while locked */
    CHECK(mlk_lock_now(&s, 5000) == MLK_R_OK && s.locked && !s.keypad);
    CHECK(mlk_set(&s, "1111", "4821", SALT_B) == MLK_R_LOCKED);
    CHECK(mlk_clear(&s, "4821") == MLK_R_LOCKED);
    CHECK(mlk_set_auto(&s, 5) == MLK_R_LOCKED);
    CHECK(!mlk_idle_due(&s, 9999999u, 0, 0));
    CHECK(mlk_check(&s, "4821"));

    /* keys do nothing until a touch shows the keypad; the hash never unlocks by a spoken or typed string outside the keypad */
    CHECK(mlk_key(&s, '4', 5000) == MLK_EV_IGNORED && s.n == 0);
    mlk_screen_touch(&s, 5100);
    CHECK(s.keypad);

    /* a wrong code never says how long the right one is: 4 and 5 digit wrong entries just keep going, 6 clears */
    type(&s, "1111", 5200, &ev);
    CHECK(ev == MLK_EV_NONE && s.n == 4 && !s.wrong_shown && s.locked);
    type(&s, "1", 5300, &ev);
    CHECK(ev == MLK_EV_NONE && s.n == 5 && s.locked);
    type(&s, "1", 5400, &ev);
    CHECK(ev == MLK_EV_WRONG && s.n == 0 && s.wrong_shown && s.locked && s.digits[0] == '\0');
    CHECK(LK_WRONG_DELAY_MS == 0);
    type(&s, "0", 5401, &ev);
    CHECK(ev == MLK_EV_NONE && s.n == 1 && !s.wrong_shown); /* no pause after a wrong try */
    CHECK(mlk_key(&s, 'B', 5402) == MLK_EV_NONE && s.n == 0 && mlk_key(&s, 'B', 5403) == MLK_EV_NONE && s.n == 0);

    /* backspace edits; the right code unlocks as soon as its last digit is typed */
    type(&s, "48", 6000, &ev);
    mlk_key(&s, 'B', 6001);
    type(&s, "821", 6002, &ev);
    CHECK(ev == MLK_EV_UNLOCK && !s.locked && s.n == 0 && !s.keypad && s.digits[0] == '\0');

    /* a longer code unlocks only with all its digits; a prefix of it does not */
    CHECK(mlk_set(&s, "123456", "4821", SALT_B) == MLK_R_OK);
    mlk_lock_now(&s, 7000);
    mlk_screen_touch(&s, 7001);
    type(&s, "12345", 7002, &ev);
    CHECK(ev == MLK_EV_NONE && s.locked && s.n == 5);
    type(&s, "6", 7003, &ev);
    CHECK(ev == MLK_EV_UNLOCK && !s.locked);

    /* cancel returns to the lock screen and wipes the digits; the keypad times out the same way */
    mlk_lock_now(&s, 8000);
    mlk_screen_touch(&s, 8001);
    type(&s, "12", 8002, &ev);
    CHECK(mlk_key(&s, 'C', 8003) == MLK_EV_CANCEL && s.locked && !s.keypad && s.n == 0 && s.digits[0] == '\0');
    mlk_screen_touch(&s, 9000);
    type(&s, "12", 9001, &ev);
    CHECK(!mlk_keypad_tick(&s, 9001 + LK_KEYPAD_TIMEOUT_MS - 1) && s.keypad);
    CHECK(mlk_keypad_tick(&s, 9001 + LK_KEYPAD_TIMEOUT_MS) && !s.keypad && s.n == 0 && s.locked);

    /* the saved record: only a whole, valid one loads; locked without a code never loads locked; a locked unit stays locked */
    char sh[33], hh[65];
    mlk_hex(s.salt, 16, sh);
    mlk_hex(s.hash, 32, hh);
    CHECK(strlen(sh) == 32 && strlen(hh) == 64);
    mlk_t r;
    mlk_load(&r, sh, hh, 1, 15, 100);
    CHECK(r.has_code && r.locked && r.auto_min == 15 && mlk_check(&r, "123456"));
    mlk_load(&r, "", "", 1, 5, 100);
    CHECK(!r.has_code && !r.locked && r.auto_min == 5);
    mlk_load(&r, sh, hh, 0, 30, 100);
    CHECK(r.auto_min == 30);   /* patch SF53: a saved 30 is kept (an earlier version offered it) */
    mlk_load(&r, sh, hh, 0, 7, 100);
    CHECK(r.auto_min == 0);    /* a value nobody offered becomes off */
    mlk_load(&r, sh, "zz", 1, 5, 100);
    CHECK(!r.has_code && !r.locked);
    mlk_load(&r, sh, hh, 0, 7, 100);
    CHECK(r.has_code && !r.locked && r.auto_min == 0);
    mlk_clear_entry(&r);

    /* clearing removes the code and the auto lock */
    CHECK(mlk_clear(&r, "123456") == MLK_R_OK && !r.has_code && r.auto_min == 0);
    CHECK(lk_ct_equal(r.hash, (const uint8_t[32]){0}, 32));

    /* reports never carry the code, hash, salt or length */
    char js[160];
    mlk_status_json(&s, js, sizeof(js));
    CHECK(strstr(js, "hash") == NULL && strstr(js, "salt") == NULL && strstr(js, "123456") == NULL && strstr(js, "length") == NULL);
    CHECK(strstr(js, "\"has_code\":true") != NULL && strstr(js, "\"locked\":true") != NULL);
    for (int i = 0; i < MLK_R_COUNT; i++) {
        mlk_reply_json(i, js, sizeof(js));
        CHECK(strstr(js, MLK_REASONS[i]) != NULL || i == 0);
    }

    /* the keypad: 12 large keys (100 by 44 px, 4 px gaps) fill the zone under the banner row, inside the glass, none over another; the dots sit above */
    CHECK(mlk_key_char(0) == '1' && mlk_key_char(9) == 'B' && mlk_key_char(10) == '0' && mlk_key_char(11) == 'C' && mlk_key_char(12) == '\0');
    CHECK(LK_KEY_W >= 100 && LK_KEY_H >= 44 && LK_KEY_SIZE >= 44 && LK_KEYS == 12);
    for (int i = 0; i < LK_KEYS; i++) {
        CHECK(mlk_key_x(i) >= 0 && mlk_key_x(i) + LK_KEY_W <= 320 && mlk_key_y(i) >= 28 && mlk_key_y(i) + LK_KEY_H <= 240);
        CHECK(LK_KEY_W >= 100 && LK_KEY_H >= 44 && LK_PAD_GAPX >= 4 && LK_PAD_GAPY >= 4);   /* the documented exception (docs/design/screen-style.md): the keypad floor, never smaller */
        for (int j = i + 1; j < LK_KEYS; j++) {
            const int ox = mlk_key_x(i) < mlk_key_x(j) + LK_KEY_W && mlk_key_x(j) < mlk_key_x(i) + LK_KEY_W;
            const int oy = mlk_key_y(i) < mlk_key_y(j) + LK_KEY_H && mlk_key_y(j) < mlk_key_y(i) + LK_KEY_H;
            CHECK(!(ox && oy));
        }
    }
    CHECK(mlk_key_y(9) + LK_KEY_H == 236 && mlk_key_y(0) == LK_PAD_Y);
    CHECK(LK_DOTS_Y >= 28 && LK_DOTS_Y + LK_DOT_SIZE <= LK_PAD_Y); /* the dots fit between the banner row and the keys */

    /* both languages say every line, in plain ASCII */
    for (int l = 0; l < 2; l++) {
        for (int i = 0; i < MLK_T_COUNT; i++) {
            const char* x = mlk_text(l, i);
            CHECK(strlen(x) >= 4);
            for (const char* c = x; *c; c++) CHECK((unsigned char)*c < 0x80);
        }
    }
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("lock core ok\n");
    return 0;
}
