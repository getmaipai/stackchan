/* Host test for travel with the private network (patch TN01): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_tailnet_core.h"

static int failures;
#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL line %d: %s\n", __LINE__, #cond);               \
            failures++;                                                  \
        }                                                                \
    } while (0)

static void test_guard(void)
{
    mt_guard_t g;
    memset(&g, 0xff, sizeof(g)); /* garbage RTC memory after a power cycle */
    CHECK(mt_guard_boot(&g, 1) == 1 && g.crashes == 0);
    mt_guard_started(&g);
    CHECK(mt_guard_boot(&g, 1) == 1 && g.crashes == 1);
    mt_guard_started(&g);
    CHECK(mt_guard_boot(&g, 1) == 1 && g.crashes == 2);
    mt_guard_started(&g);
    CHECK(mt_guard_boot(&g, 1) == 0 && g.crashes == 3); /* three crashed boots in a row: off */
    memset(&g, 0, sizeof(g));
    mt_guard_boot(&g, 0);
    mt_guard_started(&g);
    mt_guard_boot(&g, 1);
    mt_guard_stable(&g); /* a boot that stayed up resets the count */
    CHECK(g.crashes == 0);
}

static void test_addresses(void)
{
    char out[16];
    CHECK(mt_parse_ip("100.64.0.1") == 0x64400001u);
    CHECK(mt_parse_ip("100.64.0.1x") == 0 && mt_parse_ip("256.1.1.1") == 0 && mt_parse_ip("") == 0 && mt_parse_ip(NULL) == 0);
    mt_ip_to_str(0x647f0001u, out);
    CHECK(strcmp(out, "100.127.0.1") == 0);
    CHECK(mt_peer_ok("100.64.0.0") && mt_peer_ok("100.127.255.255"));
    CHECK(!mt_peer_ok("100.63.255.255") && !mt_peer_ok("100.128.0.0") && !mt_peer_ok("192.0.2.10") && !mt_peer_ok("10.0.0.1"));
    CHECK(!mt_peer_ok("") && !mt_peer_ok(NULL) && !mt_peer_ok("hub.example.com"));
}

static void test_key_shape(void)
{
    CHECK(mt_key_ok("tskey-auth-FAKETESTKEY000"));
    CHECK(!mt_key_ok("tskey-") && !mt_key_ok("tskey-short") && !mt_key_ok("abcdefghijklmnop"));
    CHECK(!mt_key_ok("tskey-auth-FAK space") && !mt_key_ok("tskey-auth-FAKE;colon") && !mt_key_ok(NULL) && !mt_key_ok(""));
    char big[200];
    memset(big, 'a', sizeof(big));
    memcpy(big, "tskey-", 6);
    big[121] = 0;
    CHECK(!mt_key_ok(big)); /* 121 characters */
    big[120] = 0;
    CHECK(mt_key_ok(big));  /* 120 characters */
}

static void test_start_decision(void)
{
    /* args: enabled, guard_ok, can_join, fails, already, free, largest */
    CHECK(mt_start_decision(1, 1, 1, 3, 0, 60000, 30000) == MT_START);
    CHECK(mt_start_decision(1, 1, 1, 2, 0, 60000, 30000) == MT_WAIT);           /* the hub still answers, mostly */
    CHECK(mt_start_decision(0, 1, 1, 9, 0, 60000, 30000) == MT_OFF);            /* switched off */
    CHECK(mt_start_decision(1, 0, 1, 9, 0, 60000, 30000) == MT_OFF);            /* the boot-loop guard */
    CHECK(mt_start_decision(1, 1, 1, 9, 1, 60000, 30000) == MT_OFF);            /* already running */
    CHECK(mt_start_decision(1, 1, 0, 9, 0, 60000, 30000) == MT_NEEDS_SETUP);    /* no key, never joined */
    CHECK(mt_start_decision(1, 1, 1, 9, 0, MT_START_MIN_FREE - 1, 30000) == MT_NO_MEMORY);
    CHECK(mt_start_decision(1, 1, 1, 9, 0, 60000, MT_START_MIN_BLOCK - 1) == MT_NO_MEMORY);
    CHECK(mt_start_decision(1, 1, 1, 9, 0, MT_START_MIN_FREE, MT_START_MIN_BLOCK) == MT_START);
    /* at home the hub answers: the failure count stays 0 and nothing ever starts */
    CHECK(mt_start_decision(1, 1, 1, 0, 0, 90000, 50000) == MT_WAIT);
}

static void test_route(void)
{
    mt_route_t r = {0, 0};
    /* not ready: always home */
    CHECK(mt_route_choose(&r, 0, 1) == 0);
    mt_route_result(&r, 0, 0, 1);
    mt_route_result(&r, 0, 0, 1);
    mt_route_result(&r, 0, 0, 1);
    CHECK(mt_route_choose(&r, 0, 1) == 0);
    /* ready: two failures on home send the next connect the private way */
    CHECK(mt_route_choose(&r, 1, 1) == 0);
    mt_route_result(&r, 0, 1, 1);
    CHECK(mt_route_choose(&r, 1, 1) == 0);
    mt_route_result(&r, 0, 1, 1);
    CHECK(mt_route_choose(&r, 1, 1) == 1);
    mt_route_result(&r, 1, 1, 1); /* it worked: it stays */
    CHECK(mt_route_choose(&r, 1, 1) == 1);
    mt_route_result(&r, 0, 1, 1);
    CHECK(mt_route_choose(&r, 1, 1) == 1);
    mt_route_result(&r, 0, 1, 1); /* two failures on the private route: back to home */
    CHECK(mt_route_choose(&r, 1, 1) == 0);
    /* the client went away: home again at once */
    r.route = 1;
    CHECK(mt_route_choose(&r, 0, 1) == 0);
    /* no hub address saved: never private */
    r.route = 1;
    CHECK(mt_route_choose(&r, 1, 0) == 0);
}

static void test_url(void)
{
    char out[64];
    CHECK(mt_url_with_host("ws://192.0.2.10:8765/xiaozhi/v1/", "100.64.0.7", out, sizeof(out)) == 1);
    CHECK(strcmp(out, "ws://100.64.0.7:8765/xiaozhi/v1/") == 0);
    CHECK(mt_url_with_host("wss://hub.example.com/ws", "100.64.0.7", out, sizeof(out)) == 1);
    CHECK(strcmp(out, "wss://100.64.0.7/ws") == 0);
    CHECK(mt_url_with_host("ws://192.0.2.10:8765", "100.64.0.7", out, sizeof(out)) == 1);
    CHECK(strcmp(out, "ws://100.64.0.7:8765") == 0);
    CHECK(mt_url_with_host("192.0.2.10:8765", "100.64.0.7", out, sizeof(out)) == 0); /* no scheme */
    CHECK(mt_url_with_host("ws://:8765", "100.64.0.7", out, sizeof(out)) == 0);      /* no host */
    CHECK(mt_url_with_host("ws://192.0.2.10:8765", "", out, sizeof(out)) == 0);
    CHECK(mt_url_with_host("ws://192.0.2.10:8765", "a/b", out, sizeof(out)) == 0);
    CHECK(mt_url_with_host("ws://192.0.2.10:8765", "u@h", out, sizeof(out)) == 0);
    char tiny[12];
    CHECK(mt_url_with_host("ws://192.0.2.10:8765/path", "100.64.0.7", tiny, sizeof(tiny)) == 0); /* does not fit */
}

int main(void)
{
    test_guard();
    test_addresses();
    test_key_shape();
    test_start_decision();
    test_route();
    test_url();
    if (failures) {
        printf("%d check(s) failed\n", failures);
        return 1;
    }
    printf("all checks passed\n");
    return 0;
}
