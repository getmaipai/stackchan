# The host API for a live playground (owner decision 21)

The local playground can run a simulation or connect to one of the person's registered robots through THEIR host. Many robots are registered; one playground connection is active at a time; a robot accepts one playground control session at a time. All per robot (decision 16).

Status 2026-11-18: the lease and the token scope are built and tested (`host/maipai_body/playground_lease.py`). The HTTP routes below are the shape the playground track's client adapter should code against; they are not served yet. The playground track edits this file to agree or change a shape.

## Auth

A token with scope `playground`, made on the host's settings page (this computer or signed-in phone), listed there, revocable, never printed in logs. It cannot call lock, update, pairing, key-exchange, settings, wifi or package tools (`FORBIDDEN_PREFIXES`) and cannot read camera frames unless the person has allowed live view for that robot. A call outside the scope gets `403` with a plain sentence.

## Routes (all under `/api/playground`, JSON, per robot)

| Route | What it does |
|---|---|
| `GET /units` | `[{"id","name","online","profile","version","battery","power","lease":"free"|"held by <who>"}]` |
| `POST /units/<id>/lease` `{"who": "Ana's laptop"}` | takes the lease; `409` with the plain refusal when another session holds it; returns `{"session","ttl_s":15}` |
| `POST /units/<id>/heartbeat` `{"session"}` | renews; the lease ends after 15 s without one |
| `DELETE /units/<id>/lease` `{"session"}` | clean release (the page does this on disconnect) |
| `GET /units/<id>/state` (Server-Sent Events) | a throttled stream (at most 10 events a second): head angles, ring pixels, privacy state, battery, power and ports, limiter status, device events; one `event:` name per kind |
| `GET /units/<id>/snapshot` | the screen frame as PNG, on demand, at most one a second |
| `POST /units/<id>/tool` `{"session","name","arguments"}` | a tool call through the normal controller path (limiter, mute, privacy, lock all apply), refused without the lease or outside the scope |

## What the person sees

While a playground session holds a robot, the robot shows the remote-control cue (firmware TB05) and the host logs one row per session (who, started, ended, why: released or no heartbeat). The health page lists a held robot as "controlled from a playground by <who>".

## Tests

Lease and scope: `host/tests/test_playground_lease.py`. The route tests (two virtual units registered as robots, a second session refused, expiry without heartbeats, a forbidden tool refused, the stream throttled) are written with the routes.

## Client side (playground track, 2026-11-18)

The playground's adapter is built against the routes above and tested against a fake host that uses the host's own lease and scope code: `scripts/virtual-unit/backends.py` (`Simulation`, `Live`, `BackendManager`) and `scripts/virtual-unit/fake_host.py`; tests `host/tests/test_playground_backends.py`. It keeps one active connection (taking a second robot releases the first), renews the lease every 5 seconds from `tick()`, falls back to the Simulation with the host's reason when the lease is lost, shows a LIVE banner, and turns every refusal into a sentence (another playground holds it, the robot is offline, the token is wrong, the host cannot be reached). Not yet: the host does not serve the routes, and `view.py` and the page have no picker (the proposed `GET /backends`, `POST /backend` and `backend` field are in `docs/plan/view-requests.md`); the live state stream (Server-Sent Events) and the snapshot throttle are not used by the adapter yet (it polls `state` and `snapshot`).
