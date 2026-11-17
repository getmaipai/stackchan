# Egress proof attempt, 2026-11-15

## Result

No proof. No capture point available from the build Mac sees the unit's traffic, so no destination list exists. The privacy claim stays as written: built so, until a capture proves it. Nothing here shows an outbound call, and nothing here rules one out.

## What was tried (read-only; nothing flashed, no hub or network change)

1. Packet capture on the build Mac. `tcpdump` is installed but the capture devices are root-only and `sudo` needs a password, which an agent may not type. `tshark` is not installed. Even with root, the Mac is a wired client on a switched network (gateway 192.0.2.1), so it only sees broadcast and its own traffic. The unit joins the hub host's Wi-Fi, a different segment path, so its unicast traffic (DNS, SNTP, TLS) never reaches the Mac's interface.
2. ARP table. It lists about 30 LAN neighbors but no entry can be tied to the unit without its MAC, and ARP shows peers only, not what they connect to. Not a capture.
3. Unit serial log (115200 baud, port free, opened without reset). Release logs are WARN level (`CONFIG_LOG_DEFAULT_LEVEL_WARN=y`), and DNS, connect and SNTP lines are not logged at that level. A 25 second read showed only battery info lines and the known "Unknown tool" errors. Serial can show a destination only in an INFO-level build, which needs a flash, so it was not done.

The idle (10 minute) and busy (self-test rounds) windows were not run: a window with a blind capture point would only fake a result.

## Classification

| Class | Destinations seen |
|---|---|
| Configured host | none observed (not visible) |
| Local network | none observed |
| Time server (configured SNTP value) | none observed |
| Public | none observed, none ruled out |

## The one thing that fixes it

A capture point that carries the unit's traffic, with one of:
- the hub host acting as the Wi-Fi access point or router: run `tcpdump -n -i <wifi interface> ether host <unit MAC>` there (needs root on that host), then `scripts/stackchan-egress-proof.sh <capture> <host IP>`; or
- a port mirror or router-side flow log that lists the unit's connections.

Run it for 10 minutes idle and across the self-test rounds, with DNS lookups included (unit to port 53 and the configured resolver). Until then, the static audit in `egress-audit.md` (old base, rebuild pending) is the only evidence.
