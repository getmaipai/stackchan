/* Host test of leaving the hosted brain (patch SF98): a fake NVS with hosted and unrelated namespaces; leaving erases exactly the cl_ ones. */
#include <stdio.h>
#include <string.h>
#include "maipai_hosted_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

typedef struct { const char* ns; int keys; } ns_t;
static ns_t nvs[] = {
    {"websocket", 3}, {"cl_websocket", 4}, {"cl_mqtt", 5}, {"maipai_priv", 3}, {"warm_boot", 2}, {"cl_activation", 2}, {"mp_brain", 1}, {"clean", 1}, {"servo", 2},
};
#define N (int)(sizeof(nvs) / sizeof(nvs[0]))
static int fail_on = -1;
static int erase(void* ctx, const char* ns)
{
    (void)ctx;
    for (int i = 0; i < N; i++) {
        if (strcmp(nvs[i].ns, ns) == 0) {
            if (i == fail_on) return -1;
            nvs[i].keys = 0;
            return 0;
        }
    }
    return -1;
}
static int hosted_keys(void) { int n = 0; for (int i = 0; i < N; i++) if (mhs_is_hosted_ns(nvs[i].ns)) n += nvs[i].keys; return n; }
static int keys_of(const char* ns) { for (int i = 0; i < N; i++) if (strcmp(nvs[i].ns, ns) == 0) return nvs[i].keys; return -1; }

int main(void)
{
    const char* names[N];
    for (int i = 0; i < N; i++) names[i] = nvs[i].ns;
    CHECK(mhs_is_hosted_ns("cl_websocket") && mhs_is_hosted_ns("cl_x") && !mhs_is_hosted_ns("clean") && !mhs_is_hosted_ns("websocket") && !mhs_is_hosted_ns(NULL));
    CHECK(hosted_keys() == 11);
    /* a failed erase is reported, the others are still done, and a second call finishes the job */
    fail_on = 2;
    CHECK(mhs_leave(names, N, erase, NULL) == -1);
    CHECK(keys_of("cl_websocket") == 0 && keys_of("cl_mqtt") == 5 && keys_of("cl_activation") == 0);
    fail_on = -1;
    CHECK(mhs_leave(names, N, erase, NULL) == 3);
    CHECK(hosted_keys() == 0);
    CHECK(mhs_leave(names, N, erase, NULL) == 3);                               /* repeating is harmless */
    CHECK(hosted_keys() == 0);
    /* nothing else was touched: the host pairing, the privacy bits, the route choice and the head calibration */
    CHECK(keys_of("websocket") == 3 && keys_of("maipai_priv") == 3 && keys_of("warm_boot") == 2 && keys_of("mp_brain") == 1 && keys_of("clean") == 1 && keys_of("servo") == 2);
    /* the factory reset erases cl_ too: it is not on the keep list (and the route choice, which is not cl_, goes with everything else) */
    CHECK(!mrc_keep_namespace("cl_websocket") && !mrc_keep_namespace("cl_mqtt") && !mrc_keep_namespace(MHS_ROUTE_NS) && mrc_keep_namespace("servo"));
    CHECK(strstr(mhs_removed_text(0), "Hosted link removed") != NULL && strstr(mhs_removed_text(0), "console") != NULL && strstr(mhs_removed_text(1), "consola") != NULL);
    CHECK(strchr(mhs_removed_text(0), 0x97) == NULL);                           /* no em dash byte */
    printf(fails ? "hosted_core_test FAILED\n" : "hosted_core_test ok\n");
    return fails ? 1 : 0;
}
