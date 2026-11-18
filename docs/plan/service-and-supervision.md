# The host as a managed service, with supervised parts

Owner decision 16 (2026-11-18): many robots, and nothing that quietly dies.

## What runs

One host process (`stackchan run`) that is the same program whether a person starts it or the system does.

| Part | What it is | Per unit? |
|---|---|---|
| Voice server (xiaozhi socket, encrypted twin) | accepts units, runs their turns | one session per unit |
| Avatar server (camera, expressions) | accepts units' second socket | one session per unit |
| Turn bridge | speech to text, the brain, text to speech, for one turn | per turn, per unit |
| Brain | own model or Home | shared, called with the unit named |
| Settings server | the settings, Brain, health and parent pages | shared |
| Pairing and key exchange | pair, approve, link keys | per unit state |
| Update | firmware update checks and pushes | per unit |
| Packages | memory notes, Home Assistant, coding companion, wake word maker | shared, optional |
| Local model server | llama.cpp child, when way 3 is the brain | shared |
| Background loops | timers, privacy read-back, sounds, light, idle motion, self-heal, check-in, roster | per unit where they hold unit state |

## Running as a service (decision 16b)

`stackchan service install|status|start|stop|logs|uninstall`.

| System | Mechanism | Starts | Restarts |
|---|---|---|---|
| Mac | launchd agent in `~/Library/LaunchAgents/` (`com.maipai.stackchan.plist`) | at login (`RunAtLoad`); a login-less always-on Mac uses a LaunchDaemon, named in the page | `KeepAlive` with `ThrottleInterval` 10 s (a crash loop is slowed, not stopped) |
| Linux, Raspberry Pi | systemd user unit (`~/.config/systemd/user/stackchan.service`) plus `loginctl enable-linger` so it starts at boot without a login | at boot | `Restart=on-failure`, `RestartSec=5`, `StartLimitBurst` generous with `RestartSec` growing is not available in systemd, so the host's own supervisor handles the slow back-off for workers; the process itself restarts every 5 s |
| Windows | a scheduled task (`schtasks /create /sc onlogon`, restart on failure through the task's settings) | at login | task setting; marked "planned: not tested here" because no Windows machine is available |

The unit file runs `stackchan run` with the same environment variables the person would use; logs go to a rotating file (`<data dir>/logs/stackchan.log`, 5 files of 5 MB) and also to the system log. The install command prints the exact path and what it did in plain words and never needs a terminal knowledge beyond running it once; the first-run page offers the same install as a button (it calls the same function).

## Supervision inside the host (decision 16c)

`maipai_body/supervisor.py`: every worker is registered with a name, a way to start it, an optional heartbeat, and the unit it belongs to. A watchdog thread checks each worker every second:

- dead (its thread ended without being asked to stop) or silent (no heartbeat for its limit): restart that worker only, with back-off 1, 2, 4 ... up to 60 seconds, reset after it has run for two minutes;
- after 5 restarts in 10 minutes the worker is marked **failed** and stops being retried until a person presses restart on the health page or the host restarts; the reason and the time are kept;
- the other workers are never touched.

The threads started through `service_threads.start` are supervised automatically: the registry now keeps how to start each one again.

## Health and status

- `GET /api/stackchan/health` (settings server, this computer only) returns one JSON document: the service, each part (name, unit, state `ok|restarting|failed|off`, last error in plain words, since when, what to do), each unit (connected, last seen, parts).
- The settings server serves a Health page at `/health` with the same content in plain words.
- `stackchan status` asks the running host for that document and prints it; when the host is not running it says so and prints the one command that fixes it (`stackchan service start`), and still lists the paired units.
- A failed part that matters to the robot (speech, brain) is sent to the unit as the existing error line (the unit already shows "what went wrong and what to do" text from the host); the plain message is the same string.

## Many units (decision 16a): audit of single-unit assumptions

| Area | State today | Needed |
|---|---|---|
| Voice and avatar sessions, per-unit brain, persona, history, volume cap, alarms | per unit | done |
| Privacy state and read-back | per unit (`PrivacyUnits`), events of other units polled | done |
| Timers | per unit service (ae064f2) | done |
| Face, notify, photo and camera calls | name the unit or the turn's unit; the resting face goes to every unit | done |
| Sounds, music features, idle motion settings | pushed to every unit | done (fan-out) |
| Touch events, reactions, rest state (`wake_on_touch`) | first unit only | per unit behavior object: open, needs a second unit on the bench |
| Music dance, self-heal hold, light service, alarm service | first unit only | per unit instance each, open |
| Shared queues and locks | the turn bridge keeps per-session dicts; the supervisor registry is per worker | review with the isolation tests |

Isolation tests with 2 and 10 simulated units: the unit-level fake (many `StackChanFirmware` instances in the virtual rig) connects N units, drives a turn on each, drops one and requires the others unaffected. The first is built here for 2 and 10 fake sockets at the server level (`host/tests/test_many_units.py`); the e2e rig version needs the playground's multi-instance rig.

## Host updates keep the service up (decision 16e)

`stackchan service update` (planned): install the new version beside the old (a new virtual environment folder), stop the service, switch a symlink, start, wait for the health document to say `ok` within 60 s, otherwise switch back and start the old one. Built 2026-11-18 (`host_update.py`): the rollback rule is tested with fakes for every failure (install fails, stop fails, new version unhealthy, first update unhealthy); the real venv install and a real service manager were not exercised here.

## Chaos tests (decision 16f)

A test mode injects faults and requires recovery with no person acting: kill a worker (supervisor restarts it), kill the settings server thread, drop a unit's connection mid-turn (the turn ends, the unit reconnects, other units unaffected), kill the whole host process (the service manager restarts it; the units reconnect with their token). Unit-level versions run in `host/tests/test_supervisor.py` and `test_many_units.py`; the process-level ones use the e2e rig's host restart.

## Failure table

| Failure | Detection | Action | What the person sees |
|---|---|---|---|
| Host process crashes | the service manager sees the exit | restart after 5 s (launchd 10 s); units reconnect with back-off | The robot shows its "away" state, then recovers; the log says why it stopped |
| A worker thread dies | watchdog: thread not alive | restart that worker with back-off | Health: "restarting"; no change for the others |
| A worker hangs | watchdog: heartbeat late | restart that worker | Health: "restarting, was not responding" |
| A worker keeps failing | 5 restarts in 10 minutes | mark failed, stop retrying | Settings page banner and `stackchan status`: the part, the last error, what to do |
| Settings server stops | supervised like any worker | restart | The page reloads after a moment |
| Local model server exits (way 3) | watchdog: child process ended | restart it | Health: "the local model restarted"; a turn in progress ends with the plain error line |
| A unit disconnects | socket closes | nothing else is touched; the unit reconnects | That unit's row says disconnected, with the time |
| A unit's turn fails | turn error | the error line goes to that unit only | That unit shows the plain error |
| Disk full or log too big | rotating log keeps 25 MB at most | n/a | n/a |
| Host update fails | health not ok after the switch | roll back and start the old version | The page says the update did not take and nothing changed |

## Status of the build (2026-11-18)

Built and tested: `stackchan service install|status|start|stop|logs|uninstall` for launchd (the plist passes `plutil -lint`) and systemd (the unit text is tested; not installed on a Linux machine here), Windows written and untested; the rotating log (5 files of 5 MB); `supervisor.py` (watchdog, heartbeat, back-off, failed state, per-unit workers) with the threads started through `service_threads` supervised automatically and the settings page restarted when it dies; the health document, the `/health` page, `/api/stackchan/health` and `stackchan status`; per-unit isolation tests with 2 and 10 units; chaos tests at the thread level (kill a worker, kill the settings server, a worker that keeps failing).

Built since: the host update that installs beside, switches and rolls back (`stackchan service update`); the process-level chaos scenarios in the e2e rig (host kill at 2 and 10 units, cut connection mid-turn, internal workers with `MAIPAI_CHAOS`, launchd kill -9); per-unit behavior objects for touch, reactions, orientation and rest (docs/plan/per-unit-behavior.md; music dance, self-heal hold, light and alarm services are with the cloud session); a heartbeat for the voice and avatar servers (one worker, `voice server`; reported on the status page, not restarted, because the servers cannot be swapped inside a running host).

Still open: the first-run page button for the service install (a button that changes system files from a web page needs its own decision); a heartbeat for the local model server (way 3); pushing a degraded part to the robot's screen; a real launchd or systemd swap of `stackchan service update` (a bench step).

## Tests from the playground track (2026-11-18)

Built in `scripts/virtual-unit/e2e_fleet.py` and run by `host/tests/test_e2e_fleet.py` (details: `docs/dev/e2e-virtual-unit.md`, "Many robots, faults and the service"):

- **Isolation with 2, 10 and 25 units** against the real host: words, answers, moods and speech frames stay with their unit, one slow unit holds nobody, a timer lives on one unit, a cut connection heals alone.
- **Chaos:** host killed mid-turn with 2 and 10 units and restarted, speech, model and voice servers down in turn, a relay that delays, swallows and cuts packets.
- **Service:** `stackchan service install` on this Mac under a temporary label and home (the module's `LABEL` and `service_env` are replaced by the scenario, nothing of the real install is touched), `kill -9`, launchd brings it back, the unit reconnects, the service is removed. systemd is not tested here (no Linux machine or container); the unit text is tested in `host/tests/test_service_and_health.py`.

Found and for the app track: (1) a turn's mood frame goes to every connected unit; (2) no fault hook: add `MAIPAI_CHAOS=1` and a localhost POST that kills one named worker so the supervisor tests can run inside a real host; (3) 25 units asking at the same instant lose turns (20 are fine); (4) the unit's Offline label after 45 s (patch 143) is firmware logic; the host has no part in it.


## The chaos hook (built 2026-11-18)

`MAIPAI_CHAOS="kill=<worker name>@<seconds>,..."` kills the named worker that many seconds after the host starts, only when the variable is set (the host logs one warning line when it is). `chaos.py` calls `Supervisor.kill`; a worker has a kill hook when it registered one: the settings page (its serving loop ends) and every thread started through `service_threads` (the thread ends and its stop event is cleared). The supervisor then restarts it with nobody acting. Used by the e2e scenario `chaos_internal_workers`, which passes: the settings server is killed 25 s in and is back inside 30 s. No release path sets the variable.

## Fleet findings fixed (2026-11-18)

- A turn's face and thinking cue went to every connected unit: the side worker threads lost the talking unit. The unit now travels with the event (`contextvars` copied into the side worker, the thinking cue sent only to the talking unit). `fleet_25` passes the mood isolation check.
- Capacity: the default thread pool (CPU count plus four, at most 32) let about twenty turns work at once because each turn holds threads for blocking work (speech to text listens for the whole utterance). The host now sets a pool of 256 workers (`MAIPAI_WORKERS`) and tells a turn that has to wait (more than 64 in flight) with the caption and error tone "I am busy with other requests. One moment." `fleet_25`: all 25 units got an answer.
