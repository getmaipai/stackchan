# Unit watchdog inventory and the several-robots rules (owner decision 16)

Firmware track, 2026-11-18. The supervisor rule is `maipai_super_core.h`, the reconnect rule `maipai_reconnect_core.h` (host tests `super_core_test.c`, `reconnect_core_test.c`); the wiring is patch SF49 (not landed yet: it waits for the b45 and b46 plain boot proofs).

## The supervisor

One `esp_timer` once a second (`maipai_super.cc`): no task of its own. A task registers with a timeout and beats; a stale task is **kicked** (its socket is closed so a blocked call returns), a timeout later **restarted** (replaced on the main task), a timeout later the **unit restarts** through `maipai_heal_restart("watchdog:<name>", 2000)`, which records the reason in flash, counts it and refuses a third restart in an hour (a fault that survives a restart never becomes a reboot loop). `self.version.get` reports `reset_reason`, `self_restarts_this_hour`, `self_restart_held` and a `watchdog` list (kicks, restarts, reboots, age per task).

## Every long-running task

| Task | Created | Supervised | By | Note |
|---|---|---|---|---|
| `ws_reconnect` (voice socket, reconnect state machine) | boot | **yes (SF49)**: beat every 5 s, timeout 3 min | supervisor | kick closes the socket; restart replaces the task; the last step restarts the unit |
| main loop | boot | yes (existing, patch 085) | `maipai_heal_watch` on the motion sensor task: 30 s without a tick asks for a restart ("stall") | |
| `stackchan` (screen and logic) | boot | partly | the main-loop tick runs from it; a frozen screen task stops the tick | register it with its own beat in the next step |
| `servo_step` | boot | no | | beat from the loop, timeout 5 s; a stuck servo task means a frozen head, not a dead unit; restart is safe |
| `audio_input`, `audio_output`, `opus_codec` | boot | no | | the voice bench counts stalls; register with a beat per frame batch, timeout 10 s; the restart is the audio service's own restart |
| tool server (MCP over the voice socket) | with the socket | through the reconnect task | | a stuck tool handler blocks the socket's receive callback: the reconnect task's heartbeat does not see that; add a beat in the receive path |
| `avatar_lan`, `avatar_rx` | on first use (SF47) | no | | optional; the camera stream (SF44) will register its sender |
| timers (alarms, ring) | boot | no | | a one-second tick in the main loop: covered by the main-loop watch |
| sound output (ring of the ready tone, chimes) | on use | no | | transient |
| seek (turn toward faces) | with the setting | no | | optional task on a PSRAM stack; stalls cannot reach flash |
| `tailnet` | after three failed connects, when built | no | | optional |
| the self-restart task (`heal_restart`) | on request | no | | transient by design |

The rule for a new long-running task: register with the supervisor, beat inside its timeout, disarm when it stops on purpose; a task that cannot beat is not allowed to be long-running.

## The host-away rules (SF49)

- Reconnect with exponential backoff and jitter: 1 s doubling to a 30 s cap, jitter up to a quarter of the delay; after ten minutes away the cap is 120 s so a gone host does not keep the radio busy. A host that returns is found within one cap plus one connect.
- All local features keep working: the reconnect task only keeps trying; nothing local waits for the host.
- After ten minutes away the screen says, in plain words: "Can't reach Home. Check it is on and on the same Wi-Fi. I keep trying." Then again every 30 minutes. The existing offline strip (45 s) and offline tone (3 minutes) stay.
- The soak (kill the host 50 times, each time the unit reconnects within the cap without a reboot) is a bench item: the `watchdog` list in `self.version.get` must stay at zero kicks, restarts and reboots.

## Several units on one network

- **Device id:** the Wi-Fi MAC, sent as `Device-Id` on every socket, so ids are unique per unit by construction; the pairing token and the link key are per unit.
- **No shared state on the unit:** every setting is in the unit's own NVS; nothing is read from another unit; the avatar socket and the voice socket carry the unit's own ids.
- **Discovery:** each unit connects to the saved host address (there is no broadcast discovery that two units could answer for each other). The Home hub's address is configured per unit.
- **Host-side (app track):** the host-id first-wins window, the pairing queue and the per-unit attempt limits are per `Device-Id` on the host (the avatar server and the pairing store already key on it; the app track's tests cover several units).
- **To verify on the bench:** two units on the same host at once, both connected, both reconnecting after a host restart without one taking the other's session (the host closes a stale socket of the same device id only).
