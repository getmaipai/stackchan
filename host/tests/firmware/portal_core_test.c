/* Host test for the Wi-Fi portal core (patches P01 to P04): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers>.
 * With the arguments "table en|es" it prints that language's string table as JSON instead of testing. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_portal_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

static void test_strings(void)
{
    CHECK(MP_S_COUNT == 15);
    for (int lang = 0; lang < 2; lang++) {
        for (int i = 0; i < MP_S_COUNT; i++) {
            CHECK(strlen(mp_str(lang, i)) > 3);
            CHECK(strstr(mp_str(lang, i), "\xe2\x80\x94") == NULL); /* no em dash */
        }
    }
    for (int i = 0; i < MP_S_COUNT; i++) {
        CHECK(strcmp(mp_str(MP_LANG_EN, i), mp_str(MP_LANG_ES, i)) != 0);
    }
    CHECK(strcmp(mp_str(5, 0), "") == 0 && strcmp(mp_str(0, 99), "") == 0);
    char buf[2048];
    for (int lang = 0; lang < 2; lang++) {
        size_t n = mp_table_json(lang, buf, sizeof(buf));
        CHECK(n > 400 && n < 1792);
        CHECK(buf[0] == '[' && buf[n - 1] == ']');
        int quotes = 0;
        for (size_t i = 0; i < n; i++) quotes += buf[i] == '"';
        CHECK(quotes == 2 * MP_S_COUNT);
    }
    CHECK(mp_table_json(0, buf, 100) == 0);
    CHECK(mp_lang_from_code("es") == MP_LANG_ES && mp_lang_from_code("es-ES") == MP_LANG_ES);
    CHECK(mp_lang_from_code("ES_mx") == MP_LANG_ES);
    CHECK(mp_lang_from_code("en-US") == MP_LANG_EN && mp_lang_from_code("zh-CN") == MP_LANG_EN);
    CHECK(mp_lang_from_code("est") == MP_LANG_EN && mp_lang_from_code(NULL) == MP_LANG_EN);
}

static void test_ssid(void)
{
    char s[33];
    mp_ssid(s, sizeof(s), 0x0a, 0xB3);
    CHECK(strcmp(s, "MaiPai-StackChan-0AB3") == 0);
    CHECK(strlen(s) <= 32);
}

static void test_code(void)
{
    char c[MP_PORTAL_CODE_LEN + 1];
    mp_code_make(42u, c);
    CHECK(strcmp(c, "000042") == 0);
    mp_code_make(1234567u, c);
    CHECK(strcmp(c, "234567") == 0);
    CHECK(mp_code_match("234567", "234567") && mp_code_match("234567", " 234 567 ") && mp_code_match("234567", "234-567"));
    CHECK(!mp_code_match("234567", "234568") && !mp_code_match("234567", "23456") && !mp_code_match("234567", "2345678"));
    CHECK(!mp_code_match("234567", "") && !mp_code_match("234567", NULL) && !mp_code_match("234567", "23456a"));
    for (uint32_t r = 0; r < 5000u; r += 7u) {
        mp_code_make(r * 2654435761u, c);
        CHECK(strlen(c) == MP_PORTAL_CODE_LEN);
        for (int i = 0; i < MP_PORTAL_CODE_LEN; i++) CHECK(c[i] >= '0' && c[i] <= '9');
    }
}

static void test_guard(void)
{
    mp_guard_t g;
    mp_guard_reset(&g);
    CHECK(mp_guard_check(&g, "111111", "111111") == -1);
    for (int i = 0; i < MP_PORTAL_MAX_BAD_CODES - 1; i++) {
        CHECK(mp_guard_check(&g, "111111", "000000") == MP_S_BADCODE);
    }
    CHECK(mp_guard_check(&g, "111111", "000000") == MP_S_LOCKED);
    CHECK(mp_guard_check(&g, "111111", "111111") == MP_S_LOCKED); /* the right code is too late */
    mp_guard_reset(&g);
    CHECK(mp_guard_check(&g, "111111", "111111") == -1);
    /* a right code between wrong ones clears the count */
    CHECK(mp_guard_check(&g, "111111", "0") == MP_S_BADCODE);
    CHECK(mp_guard_check(&g, "111111", "111111") == -1 && g.bad == 0);
}

static mp_net_t net(const char* ssid, int rssi, int secure)
{
    mp_net_t n;
    memset(&n, 0, sizeof(n));
    strncpy(n.ssid, ssid, 32);
    n.rssi = (int8_t)rssi;
    n.secure = (uint8_t)secure;
    return n;
}

static void test_nets(void)
{
    mp_net_t a[8] = {net("far", -85, 1), net("", -40, 1), net("near", -35, 0), net("far", -60, 1), net("mid", -70, 1)};
    int n = mp_nets_tidy(a, 5);
    CHECK(n == 3);
    CHECK(strcmp(a[0].ssid, "near") == 0 && strcmp(a[1].ssid, "far") == 0 && strcmp(a[2].ssid, "mid") == 0);
    CHECK(a[1].rssi == -60); /* the strongest copy of a repeated name */
    char j[256];
    size_t len = mp_nets_json(a, n, j, sizeof(j));
    CHECK(len == strlen(j));
    CHECK(strcmp(j, "[[\"near\",-35,0],[\"far\",-60,1],[\"mid\",-70,1]]") == 0);

    mp_net_t q[1] = {net("a\"b\\c", -50, 1)};
    mp_nets_json(q, 1, j, sizeof(j));
    CHECK(strcmp(j, "[[\"a\\\"b\\\\c\",-50,1]]") == 0);
    mp_net_t t[1] = {net("tab\there", -50, 1)};
    mp_nets_json(t, 1, j, sizeof(j));
    CHECK(strstr(j, "\\u0009") != NULL);

    mp_net_t many[40];
    for (int i = 0; i < 40; i++) {
        char nm[8];
        snprintf(nm, sizeof(nm), "n%d", i);
        many[i] = net(nm, -90 + i, 1);
    }
    CHECK(mp_nets_tidy(many, 40) == MP_PORTAL_MAX_NETS);
    CHECK(many[0].rssi == -51 && many[1].rssi == -52);
    char small[16];
    mp_nets_json(many, 3, small, sizeof(small));
    CHECK(strlen(small) < sizeof(small) && small[strlen(small) - 1] == ']'); /* never writes past the buffer */
    CHECK(mp_nets_tidy(a, 0) == 0);
}

static void test_ssid_ok(void)
{
    CHECK(mp_ssid_ok("Home") && mp_ssid_ok("a") && mp_ssid_ok("12345678901234567890123456789012"));
    CHECK(!mp_ssid_ok("") && !mp_ssid_ok(NULL) && !mp_ssid_ok("123456789012345678901234567890123"));
    CHECK(!mp_ssid_ok("bad\nname"));
}

static void test_host(void)
{
    char o[80];
    CHECK(mp_host_url("", o, sizeof(o)) == 0 && mp_host_url(NULL, o, sizeof(o)) == 0);
    CHECK(mp_host_url("192.0.2.10", o, sizeof(o)) == 1 && strcmp(o, "ws://192.0.2.10:8765") == 0);
    CHECK(mp_host_url("192.0.2.10:9000", o, sizeof(o)) == 1 && strcmp(o, "ws://192.0.2.10:9000") == 0);
    CHECK(mp_host_url("ws://hub.example.com:8765", o, sizeof(o)) == 1 && strcmp(o, "ws://hub.example.com:8765") == 0);
    CHECK(mp_host_url("wss://hub.example.com", o, sizeof(o)) == 1 && strcmp(o, "wss://hub.example.com:8765") == 0);
    CHECK(mp_host_url("hub.example.com", o, sizeof(o)) == 1 && strcmp(o, "ws://hub.example.com:8765") == 0);
    CHECK(mp_host_url("http://192.0.2.10", o, sizeof(o)) == -1);
    CHECK(mp_host_url("192.0.2.10:", o, sizeof(o)) == -1 && mp_host_url(":80", o, sizeof(o)) == -1);
    CHECK(mp_host_url("192.0.2.10:80a", o, sizeof(o)) == -1 && mp_host_url("a:1:2", o, sizeof(o)) == -1);
    CHECK(mp_host_url("a b", o, sizeof(o)) == -1 && mp_host_url("a/b", o, sizeof(o)) == -1);
    CHECK(mp_host_url("ws://", o, sizeof(o)) == -1);
    CHECK(mp_host_url("192.0.2.10:123456", o, sizeof(o)) == -1);
    CHECK(mp_host_url("192.0.2.10", o, 8) == -1); /* too small an output: refused, not cut */
    char big[200];
    memset(big, 'a', sizeof(big) - 1);
    big[sizeof(big) - 1] = 0;
    CHECK(mp_host_url(big, o, sizeof(o)) == -1);
}

int main(int argc, char** argv)
{
    if (argc == 3 && strcmp(argv[1], "table") == 0) {
        char buf[2048];
        mp_table_json(strcmp(argv[2], "es") == 0 ? MP_LANG_ES : MP_LANG_EN, buf, sizeof(buf));
        printf("%s", buf);
        return 0;
    }
    test_strings();
    test_ssid();
    test_code();
    test_guard();
    test_nets();
    test_ssid_ok();
    test_host();
    if (failures) { printf("%d failure(s)\n", failures); return 1; }
    printf("portal core: all passed\n");
    return 0;
}
