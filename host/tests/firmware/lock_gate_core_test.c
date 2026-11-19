/* Host test of the lock gate table (patch SF106, review fix): which tools a locked unit refuses. */
#include <stdio.h>
#include "maipai_lock_gate_core.h"

static int fails;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)

int main(void)
{
    /* the network and pairing tools need an unlocked unit, the reads of saved networks included */
    const char* locked[] = {"self.wifi.list_saved", "self.wifi.add", "self.wifi.forget", "self.wifi.switch", "self.tailnet.set", "self.network.prefer_tailnet",
                            "self.link.pair", "self.link.anything_new", "self.brain.set_route", "self.wifi.a_tool_added_later"};
    for (unsigned i = 0; i < sizeof(locked) / sizeof(locked[0]); i++) CHECK(mlg_needs_unlock(locked[i]));
    /* everything else keeps working on a locked unit (the lock's own tools, status reads, the volume) */
    const char* open[] = {"self.lock.status", "self.lock.clear", "self.get_device_status", "self.audio_speaker.set_volume", "self.brain.status", "self.tailnet.status",
                          "self.network.test", "self.wifi", "self.wifix.add", "self.brain.set_route2", "", "self.screen.set_brightness"};
    for (unsigned i = 0; i < sizeof(open) / sizeof(open[0]); i++) CHECK(!mlg_needs_unlock(open[i]));
    CHECK(!mlg_needs_unlock(NULL));
    CHECK(strstr(MLG_REFUSAL, "Unlock it with the code") != NULL);
    printf(fails ? "lock_gate_core_test FAILED\n" : "lock_gate_core_test ok\n");
    return fails ? 1 : 0;
}
