# Next: network and security tools on the robot (owner idea, 2026-11-17)

Placement: a "Tools" app in the Apps wall. Radio-level tools run on the unit (it has the Wi-Fi radio and the network stack); heavier tools run on the host and show their result on the unit. Local. Anything that contacts the public internet is an owner-started test behind an "Internet tests" switch that is off by default (the same rule as every outside connection: nothing leaves the home unless the owner enabled it and asked).

**Tools (first set, in order of value)**
1. **Wi-Fi scan** (unit): networks around with name, signal, channel and security type (open, WPA2, WPA3), sorted by signal; flags a duplicate name with a different security or address as a possible look-alike network.
2. **Signal meter** (unit): live signal strength of the current network as a big number and bar, with a hint for placement ("move closer to the router"). Useful when carrying the robot.
3. **Ping** (unit): to the gateway, the host, the Home hub, or an address the owner types on the settings page; shows loss and round trip time. Public targets need the Internet tests switch.
4. **DNS check** (unit): resolves a name through the network's resolver and shows the answer and time; a captive portal check ("is the Wi-Fi asking for a login?").
5. **Route** (unit): hop list to a target by raising the time-to-live; LAN targets only unless Internet tests are on.
6. **Ports** (host): checks which of a short list of common ports are open on one device of the owner's own network (private address ranges only, one device at a time, rate limited, with a visible cue while it runs).
7. **Speed test** (host): speed between the robot and the host over the home network (the host serves a test endpoint, so nothing leaves the home); an internet speed test is a separate button behind the Internet tests switch and is run by the host, not the robot.
8. **Security check** (host plus unit): a short checklist screen: Wi-Fi security type, whether the host's settings page is reachable only from this computer, remote control off or on, update signing present, lock code set, private network key present. It reads the robot's own settings and the host's; it is a status screen, not a scanner.

**What it will not do:** no packet injection, no deauthentication, no password cracking, no capture of other devices' traffic, no scanning of public addresses, no scanning a network the unit is not joined to. Port and device checks are limited to the private ranges of the network the owner joined, one target at a time, and show a persistent on-screen cue while running. The tools are hidden while the robot is locked.

**Screens:** the Tools app opens a wall list of tiles (drawn icons: antenna, signal bars, ping pulse, globe, route, door, gauge, shield); each tool opens a result screen with big numbers and a Run button; results from the host arrive as cards. Long lists scroll; every screen has the drag bar and 44 px targets.

**Cost [estimate]:** the radio tools reuse the network test and the Wi-Fi code that already exist; ping, DNS and route use the stack's built-in functions, about 8 to 12 KB of flash and no steady internal RAM (a scan result list of up to 20 networks held in PSRAM while the screen is open). The host tools are Python and cost no firmware.

**Tests:** core logic (sorting, look-alike rule, ping statistics, hop parsing) in C; the private-range rule and the rate limits in Python with a fake network; a bench run on the unit for the scan and the meter.

**Build order:** (1) the Tools tile and the wall, Wi-Fi scan and signal meter; (2) ping, DNS and the captive portal check; (3) the host tools (ports, speed test) with the cue; (4) the security check screen; (5) route.
