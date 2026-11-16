/* Host test for the network test core (patch U04): cc -std=c99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <string.h>
#include "maipai_nettest_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static mn_input_t healthy(void)
{
    mn_input_t in;
    memset(&in, 0, sizeof(in));
    in.wifi_joined = 1;
    in.rssi = -55;
    in.has_ip = 1;
    in.saved_networks = 1;
    in.host_set = 1;
    in.host_link_up = 1;
    return in;
}

static int has(const char* text, const char* word) { return strstr(text, word) != NULL; }

static void test_all_good(void)
{
    mn_input_t in = healthy();
    mn_result_t r;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.problems == 0 && r.fix[0] == '\0');
    CHECK(r.state[0] == MN_OK && r.state[1] == MN_OK && r.state[2] == MN_SKIP);
    CHECK(has(r.line[0], "strong") && has(r.line[1], "connected") && has(r.line[2], "not in this build"));
    char sum[64];
    mn_summary(&r, MN_EN, sum, sizeof(sum));
    CHECK(strcmp(sum, "All good.") == 0);
}

static void test_wifi_problems_say_what_to_do(void)
{
    mn_input_t in = healthy();
    mn_result_t r;
    in.wifi_joined = 0;
    in.has_ip = 0;
    in.saved_networks = 0;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[0] == MN_BAD && r.state[1] == MN_SKIP && r.problems == 1);
    CHECK(has(r.fix, "Wi-Fi setup")); /* nothing saved: set it up */
    in.saved_networks = 2;
    mn_judge(&in, MN_EN, &r);
    CHECK(has(r.fix, "closer to the router"));
    in.wifi_joined = 1; /* joined but no address */
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[0] == MN_BAD);
}

static void test_weak_signal_is_a_hint_not_a_failure(void)
{
    mn_input_t in = healthy();
    mn_result_t r;
    in.rssi = -82;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[0] == MN_OK && r.problems == 0 && has(r.line[0], "weak") && has(r.fix, "weak"));
    CHECK(strcmp(mn_signal_word(-60, MN_EN), "strong signal") == 0 && strcmp(mn_signal_word(-70, MN_EN), "good signal") == 0);
    CHECK(strcmp(mn_signal_word(0, MN_EN), "signal unknown") == 0);
}

static void test_host_problems(void)
{
    mn_input_t in = healthy();
    mn_result_t r;
    in.host_set = 0;
    in.host_link_up = 0;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[1] == MN_BAD && has(r.line[1], "no address") && has(r.fix, "type it in"));
    in.host_set = 1;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[1] == MN_BAD && has(r.line[1], "not answering") && has(r.fix, "home computer is on"));
    char sum[64];
    mn_summary(&r, MN_EN, sum, sizeof(sum));
    CHECK(strcmp(sum, "1 thing(s) to check.") == 0);
}

static void test_private_network(void)
{
    mn_input_t in = healthy();
    mn_result_t r;
    in.tailnet_built = 1;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[2] == MN_SKIP && has(r.line[2], "no key"));
    in.tailnet_key = 1;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[2] == MN_SKIP && has(r.line[2], "standby")); /* home answers, so no problem */
    in.host_link_up = 0;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[2] == MN_BAD && r.problems == 2); /* the host is not answering and the private path is not up */
    CHECK(has(r.fix, "home computer is on")); /* the first problem's fix, not the last */
    in.tailnet_ready = 1;
    mn_judge(&in, MN_EN, &r);
    CHECK(r.state[2] == MN_OK && has(r.line[2], "connected"));
}

static void test_spanish_has_every_line_and_no_accents(void)
{
    mn_input_t cases[4];
    cases[0] = healthy();
    cases[1] = healthy();
    cases[1].wifi_joined = 0;
    cases[1].saved_networks = 0;
    cases[2] = healthy();
    cases[2].host_link_up = 0;
    cases[2].tailnet_built = 1;
    cases[2].tailnet_key = 1;
    cases[3] = healthy();
    cases[3].rssi = -85;
    for (int k = 0; k < 4; k++) {
        mn_result_t r;
        mn_judge(&cases[k], MN_ES, &r);
        for (int i = 0; i < MN_STEPS; i++) {
            CHECK(r.line[i][0] != '\0');
            for (const unsigned char* p = (const unsigned char*)r.line[i]; *p; p++) CHECK(*p < 128);
        }
        for (const unsigned char* p = (const unsigned char*)r.fix; *p; p++) CHECK(*p < 128);
    }
    mn_result_t r;
    mn_judge(&cases[0], MN_ES, &r);
    CHECK(has(r.line[0], "conectado"));
    char sum[64];
    mn_summary(&r, MN_ES, sum, sizeof(sum));
    CHECK(strcmp(sum, "Todo bien.") == 0);
}

int main(void)
{
    test_all_good();
    test_wifi_problems_say_what_to_do();
    test_weak_signal_is_a_hint_not_a_failure();
    test_host_problems();
    test_private_network();
    test_spanish_has_every_line_and_no_accents();
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
