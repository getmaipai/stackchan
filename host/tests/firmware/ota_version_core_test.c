/* Host test of the numeric firmware version (patch SF110): the vendor update check reads dotted numbers only. */
#include <stdio.h>
#include <string.h>
#include "maipai_ota_version_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

static int is(const char* in, const char* want, size_t n)
{
    char out[32];
    memset(out, 'x', sizeof out);
    size_t len = mov_numeric(in, out, n);
    return strcmp(out, want) == 0 && len == strlen(want);
}

int main(void)
{
    CHECK(is("1.6.2-maipai.1", "1.6.2", 24));
    CHECK(is("1.6.2", "1.6.2", 24));
    CHECK(is("2.0.0+build", "2.0.0", 24));
    CHECK(is("1.6.", "1.6", 24));
    CHECK(is("abc", "0", 24));
    CHECK(is("", "0", 24));
    CHECK(is("1.2.3.4.5", "1.2.3", 6)); /* cut to the buffer, still terminated */
    char one[1] = {'x'};
    CHECK(mov_numeric("1.2", one, 1) == 0 && one[0] == 0); /* a buffer of 1 gets the terminator only */
    CHECK(mov_numeric("1.2", NULL, 0) == 0);
    char z[8];
    CHECK(mov_numeric(NULL, z, sizeof z) == 1 && strcmp(z, "0") == 0);
    printf(fails ? "ota_version_core_test FAILED\n" : "ota_version_core_test ok\n");
    return fails ? 1 : 0;
}
