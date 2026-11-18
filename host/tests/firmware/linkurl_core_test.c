/* Host test for the encrypted address rule (patch SF33). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include <stdlib.h>
#include "maipai_linkurl_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static int rw(const char* in, char* out, size_t cap) { return mlu_rewrite(in, out, cap); }

int main(void)
{
    char o[96];
    CHECK(rw("ws://192.0.2.10:8765/xiaozhi/v1/", o, sizeof o) && strcmp(o, "wss://192.0.2.10:18775/xiaozhi/v1/") == 0);
    CHECK(rw("ws://host.local:8766/avatar", o, sizeof o) && strcmp(o, "wss://host.local:18776/avatar") == 0);
    CHECK(rw("http://192.0.2.10:8767/photo/1", o, sizeof o) && strcmp(o, "https://192.0.2.10:8777/photo/1") == 0);
    CHECK(rw("ws://192.0.2.10:8765", o, sizeof o) && strcmp(o, "wss://192.0.2.10:18775") == 0);
    CHECK(rw("ws://192.0.2.10:8765?x=1", o, sizeof o) && strcmp(o, "wss://192.0.2.10:18775?x=1") == 0);
    /* not rewritten: another port, no port, another scheme, an already encrypted address, a wrong scheme for the port */
    CHECK(!rw("ws://192.0.2.10:9000/x", o, sizeof o) && o[0] == '\0');
    CHECK(!rw("ws://192.0.2.10/x", o, sizeof o));
    CHECK(!rw("wss://192.0.2.10:18775/x", o, sizeof o));
    CHECK(!rw("http://192.0.2.10:8765/x", o, sizeof o));
    CHECK(!rw("ws://:8765/x", o, sizeof o));
    CHECK(!rw("ws://h:87650/x", o, sizeof o));
    CHECK(!rw(NULL, o, sizeof o));
    /* a small output buffer never overflows */
    CHECK(!rw("ws://192.0.2.10:8765/xiaozhi/v1/", o, 10) && o[0] == '\0');
    CHECK(mlu_is_link_port(18775) && mlu_is_link_port(18776) && mlu_is_link_port(8777) && !mlu_is_link_port(443) && !mlu_is_link_port(8765));
    if (failures) return 1;
    printf("linkurl core ok\n");
    return 0;
}
