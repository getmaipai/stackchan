# User docs claims audit

Audited all Markdown pages in `docs/user/` against the host code, package code, configuration, schemas, firmware patch order and patch headers. The three rows per page group claims by type: commands, paths and keys; settings and defaults; and counts, named features, screens, tools and build status. Inline code values, numbers and bold UI labels are listed in the claim cell.

Results use `ok`, `fixed` or `unverifiable`. A claim group is `fixed` if the page had a stale claim in that group and it was corrected. Claims about product behavior without source support were removed or labeled as coming. External comparison statements on `compare.md` keep their official source links.

## Summary

- Pages audited: 56
- Claim groups checked: 168
- Claim groups fixed: 25
- Claim groups ok: 143
- Claim groups unverifiable: 0

## Page audit

### `about.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `/about` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 3.0, 3, 2.0, 5; This project:; StackChan firmware base and xiaozhi-esp32:; StackChan structure files used for the 3D model:; Espressif ESP-SR and ESP-IDF:; LVGL:; esptool-js:; The local stack (downloaded on request): | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `bench-listening.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `MAIPAI_BENCH_MIN_LISTEN_S=12` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 6 s, 8, 12, 12 s, 60; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `camera.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 22, 18, 2; This is a convenience, not a safety device.; snapshots; Take a photo; Turn toward faces.; Wave and mirror.; Planned; coming; built; default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `character-packs.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan character build FOLDER pack.zip --name NAME --author YOU --license "own work"`; `stackchan character check pack.zip` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `neutral.png`; `happy.png`; `docs/design/character-pack-format.md` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3, 4, 5; Look; Character pack; Install the pack; Send to the unit | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `choose-a-brain.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `http://127.0.0.1:8051/brain` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 127.0, 0.1, 8051, 1, 2, 3, 2 GB; 1. MaiPai Home; 2. Your own stack; 3. A small stack on this computer; Use MaiPai Home; Test; A: Hosted by M5Stack/Xiaozhi.; Your voice leaves your home; B: Custom.; Planned | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `coding-companion.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan coding-token` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `show_request_text = true`; `robot.toml`; `enabled = true`; `[packages.coding_companion]`; `
python -m maipai_packages.coding_companion.hook working --project my-app
python -m maipai_packages.coding_companion.hook waiting --kind permission --project my-app
python -m maipai_packages.coding_companion.hook finished --project my-app
`; `

   Use the Python that `; ` installed for the host (`; ` shows where it is). The hook never fails the agent: if the robot cannot be reached it prints one line and exits cleanly. To post from another tool, send JSON such as `; ` to `; ` with ` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3, 127.0, 0.1, 8052; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `compare.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `brain = "llm"`; `brain = "home"` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 2026, 11, 15, 150 ms, 300 ms, 8, 548 KB, 24 KB, 76 KB, 4, 400 ms, 27; How to read the ratings:; Privacy and security:; Speed and answer quality:; What MaiPai Home adds:; What you give up:; Memory, people, calendars and rules; Planned; coming; built; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `face-and-look.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan face set UNIT --color mint`; `stackchan face set UNIT --captions on`; `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `face_style`; `robot.toml`; `[scene rainy_day]`; `[scene off]` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 60 s, 6, 33, 40 rows, 20 s, 12 people, 12 frames, 14, 000, 000 bytes, 3, 12, 31, 20 percent, 10 percent, 5 percent; Big eyes; stock; minimal; Use on this unit; Send to the unit; Picture only; Picture with eyes and mouth drawn on top; A short run of frames; Look; Captions; Status icons; Planned; built; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `faq.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan forget`; `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 5, 3.0; Feature statements and page controls | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `features.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `brain = "home"` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 28, 18 s, 10, 31, 8, 20 percent, 5, 2026, 11, 18, 3 s; MaiPai for StackChan runs on your own model, with no Home needed.; Wake word and voice; Follow-ups; Voice commands; Offline phrases; Persona, speech speed and pitch; Six languages; Weather and mood overlays; CRT and color effects; Top banner and subtitle strip; Filler sounds; Language packs; Turn toward faces; Face-seen icon; Lock tile on the control sheet; Smoother eyes and mouth; Your own picture faces; Faces and color | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `find-and-remote.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan units`; `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `enabled = true`; `[remote]`; `robot.toml`; `enabled = false` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 5, 85; Find; Last seen.; Beep and flash.; Make it beep; Warmer or colder.; Place names, private by default.; Your phone's hotspot.; A map, if you choose.; Beep; Turn the lights on; Talk; Pan and tilt; Home; Planned; coming; built; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `games-and-pet.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 15, 2, 3, 10, 20, 30, 6, 9, 8; Color memory.; Whack-a-mole.; Tic-Tac-Toe.; Do It.; Rock Paper Scissors.; Play again; Quit; Rematch; Magic 8-Ball.; Dice and Coin.; Games; More games; Best scores by person; Show games and best scores; Talk games; coming; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `getting-started.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `pipx install "git+https://github.com/getmaipai/stackchan#subdirectory=host"`; `stackchan service install`; `stackchan status`; `stackchan pair`; `stackchan check`; `stackchan forget` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `http://127.0.0.1:8051/brain`; `stackchan-` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 20 minutes, 5, 1, 2, 127.0, 0.1, 8051, 3, 4, 6 digit, 10 minutes, 6, 22; First:; Install the host.; Choose a brain.; Flash the robot.; Pair.; Check.; Talk.; Hosted by M5Stack/Xiaozhi; Custom; Planned | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `glossary.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 5, 6 digit; Robot; Host; Brain; MaiPai Home; Local LLM; Wake word; Light bars; Pairing; Snapshot; `robot.toml`; Factory firmware | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `hardware-and-models.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `http://192.0.2.10:8080/v1` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 4, 400 ms, 27, 3 GB, 8, 5, 6 GB, 16, 18 GB, 1, 2, 3, 192.0, 2.10, 8080; A 4B-class model; A 27B-class model; Memory is the limit.; Pick a model server app; Download a model; Turn on the server; Let the host reach it.; Type that address; On the host.; On a bigger computer on your network.; On MaiPai Home.; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `home-assistant.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `STACKCHAN_HA_TOKEN`; `robot.toml`; `[packages.home_assistant]`; `enabled = true`; `url`; `cameras`; `allow_unidentified = true`; `speakers`; `http://`; `https://`; `allow_plain_http = true` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `home-tools.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; Planned; built; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `index.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; First:; Other sections:; coming | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `install-the-host.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `pipx install "git+https://github.com/getmaipai/stackchan#subdirectory=host"`; `stackchan --help`; `stackchan run`; `stackchan status`; `stackchan service install`; `stackchan service status`; `pipx upgrade maipai-bot`; `stackchan service uninstall`; `pipx uninstall maipai-bot` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `pipx`; `http://127.0.0.1:8051/brain`; `~/.config/maipai/robot.toml`; `~/.local/share/maipai-bot/stackchan-pairing.json`; `MAIPAI_XIAOZHI_PORT` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 5, 1, 2, 3, 4, 127.0, 0.1, 8051; default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `jokes-and-games-content.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml`; `enabled = true`; `[packages.pantry]`; `adult_humor = true`; `pantry` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 100, 40, 2, 00, 5; Built-in set; Shape.; Kids.; Facts.; Riddles.; Copies.; Games and fun; Jokes and games content; Delete; Never again; Refill now; line; built; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `languages.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `language`; `[home]`; `robot.toml` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 24 hour; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `lights-and-sounds.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 2 s, 10 s, 20 percent; Green; Pink; Cyan; Amber; Blue; White; Dim amber; Red and blue; Dark; Red light at the back | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `local-stack.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `/brain` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 8 GB, 5, 2.0, 1, 2, 3, 4; Install; Stop; Remove it | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `local-vs-home.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; Your own model:; MaiPai Home:; coming; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `lock.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 4, 6 digits, 3, 15 minutes, 5, 30, 60 minutes; Security; Lock now; Auto lock; default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `memory-notes.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml`; `[packages.memory_notes]`; `enabled = true`; `people`; `default_person`; `notes`; `~/.local/share/maipai-bot/notes/alex.md` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 300, 1, 2, 30 minutes, 10 minutes, 3; notes passphrase; household; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `more-games.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 8, 6, 6 s; coming; Four in a Row.; Play again; Quit; coming; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `moves-and-moods.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `cues` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 180, 50, 30, 15, 8 percent, 12, 20 percent, 10 percent, 5 percent, 15 percent, 10 s, 22; coming | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `music-and-dance.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 8 s, 8, 16; sway; nod yes; shake no; wiggle; bow; groove; Dance to music; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `mute-and-camera-off.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `local_unmute` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 30 s; This is a convenience, not a safety device.; Mute; Camera off; Full quiet; Quiet now; default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `no-stealth.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; Watching; Remote; Planned; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `offline-lines.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 20 s, 1, 2, 3; Greetings:; Touch and movement:; Link:; Care:; Mood:; Games and fun; Jokes and games content; line; Delete; Never again; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `offline-mumble.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; off by default; mumble; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `parent-view.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml`; `lan = true`; `[settings]` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 6, 3, 10 minutes, 4; Family and safety; Robot:; Microphone:; Camera:; Lock:; Who controlled the robot lately:; Show a pairing code; Pair a robot; Approve; Show the phone code; Planned; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `privacy.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan forget`; `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml`; `[llm]`; `url`; `stt_url`; `tts_url`; `brain = "home"`; `[update]` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; Planned | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `question-games.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 12, 106; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `release-notes.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1.0, 0, 8; Planned; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `run-as-a-service.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `bash
stackchan service install
`; `

What it does:

- **Mac:** starts the host when you log in, and starts it again if it stops.
- **Linux and Raspberry Pi:** starts the host when the computer starts and starts it again if it stops. If it says it needs one more step for starting before anyone logs in, it prints the exact line for an administrator.
- **Windows:** Host service support is coming after v1.

No terminal? Open the status page on the host computer (`; `) and press **Keep the host running** when it is shown. It does the same thing, once, and the page stops for about a minute while the host restarts as a service. If the service does not come up healthy, the host is started the old way and the page says why on your next visit.

It runs the same program you would start by hand. Your settings, pairings and notes are not touched.

## Look after it

| Command | What it does |
|---|---|
| `; ` | Says if it is installed and running |
| `; ` | Starts it |
| `; ` | Stops it until your next login |
| `; ` | Shows the last lines of the log |
| `; ` | Removes it. Your settings stay |
| `; ` | Installs the new version beside the old one, switches to it and checks it is healthy. If it is not healthy within a minute, it goes back to the old version by itself |

The log is kept in your data folder under `; `. It never grows past about 25 MB: old files are replaced.

## Update with a safety net

`; ` never replaces the running host in place. It installs the new version in its own folder, stops the service, switches, starts, and waits up to 60 seconds for the status page to say everything runs. If it does not, the old version is started again and `; ` says the update did not take. The last two versions are kept.

## If it keeps stopping

The host restarts itself, and a part that keeps failing is reported on the [status page](status-and-health.md) with what to do. If the whole program keeps stopping, run ` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 25 MB, 60 s; Mac:; Linux and Raspberry Pi:; Windows:; Keep the host running; coming | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `security.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan pair`; `stackchan forget`; `stackchan settings-token`; `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `lan = true` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 6 digit, 127.0, 0.1, 1, 2, 3; Pairing needs you in the room.; Revocable access.; Tokens on everything that is on.; Signed updates.; Remote control is off by default.; The camera cue cannot be switched off.; The link on your home network is plain.; The Wi-Fi setup page is a short window.; Someone with the robot in hand can read its memory over USB.; Settings; Reset; Planned; built; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `settings.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check`; `stackchan settings-token`; `stackchan face set UNIT --style big_eyes --color mint --captions on` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml`; `face_style`; `face_color`; `captions`; `night_mode`; `language`; `languages.md`; `brain`; `llm`; `home`; `url`; `stt_url`; `tts_url`; `[llm]`; `stt_model_dir`; `tts_model`; `tts_tokens`; `tts_data_dir`; `voice`; `thinking_cue`; `[update] source`; `trusted_key`; `preset`; `lan = true`; `[settings]`; `http://<the host's address>:8051/settings?token=<the token>`; `[llm] url`; `[llm] stt_url`; `[home] url`; `speech_speed`; `speech_pitch`; `hourly_chime`; `persona`; `quiet_from`; `quiet_to`; `idle_motion`; `local_unmute`; `[update] trusted_key`; `[update] preset`; `core` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | fixed | Corrected the stale key or path; checked the remaining references. |
| Counts, limits, names, controls and status: 8051, 0.75, 1.5, 1, 12, 12 s, 0, 24 hour; Search settings; Advanced; Quiet now; Quiet on a schedule; Face; Voice; Time; Pictures; Reactions; People; Games; Privacy; System; Units; Language; Remote controls; coming; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `status-and-health.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `/health`; `http://127.0.0.1:8051/health`; `bash
stackchan status
`; `

It prints the same information. If the host is not running, it says so and tells you to run ` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 127.0, 0.1, 8051; Running:; Restarting:; Stopped after repeated failures: | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `swipe-pages.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `self.pages.status`; `self.pages.get`; `self.pages.set`; `self.page.show`; `self.page.tiles`; `pages_cfg`; `page_tiles` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 2026, 11, 17, 20 s, 6 s, 1, 5, 10 minutes, 8 s, 10, 15, 30, 45, 60 minutes, 2, 3, 2 s, 7, 4 s, 4, 300 s, 15 s; Clock.; Timers.; Games.; Quick actions.; Pictures.; Dashboard.; Behavior; Swipe pages; Show on the robot; Send sample tiles; coming; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `switch-from-the-factory-firmware.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check`; `stackchan forget` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3, 4, 5; Setup; Only Official | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `timers-and-alarms.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 5, 10 minutes, 22, 8 s, 60 percent, 10, 30, 5 minutes; Quiet on a schedule; Quiet now; Planned | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `troubleshooting.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check`; `stackchan pair`; `stackchan status`; `stackchan run` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `--:--`; `docs/dev/build-from-source.md`; `camera = true`; `MAIPAI_XIAOZHI_PORT`; `MAIPAI_STACKCHAN_AVATAR_PORT`; `MAIPAI_STACKCHAN_SETTINGS_PORT` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 60 s, 3 s; More; Version; Reset; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `try-the-virtual-robot.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `bash
python3 scripts/virtual-unit/view.py 8780
`; `

2. Open this address in your browser: http://127.0.0.1:8780/

The address only works on your own Mac. Nothing leaves it.

## What you can do

- Click the screen to tap it. Drag across it to swipe. Swipe up from the bottom edge to open the control sheet, swipe left for the next page, swipe right to come back to the face. The Gestures buttons do the same for you.
- Pick a face button to change the face.
- Use the side panel to call any of the robot's tools by name and see what comes back.
- Press Record, use the robot, press Stop, name it and press Save. The file lands in `; `. Pick `; ` in the scenario list to replay it with the same waits.
- Pick a scenario and press Play to watch a screen or a story run in real time.

## If it does not start

- The screens come from a program you build once: see ` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 8780, 2, 127.0, 0.1, 3; Feature statements and page controls | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `updates.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan update --dry-run`; `stackchan update`; `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml`; `[update]`; `source`; `--source FOLDER`; `trusted_key`; `preset`; `core`; `home`; `docs/dev/build-from-source.md` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3, 20 percent, 4, 120 s, 62 percent, 22; Planned; built; default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `use-it-anywhere.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 3 times, 1, 2, 3, 4; Feature statements and page controls | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `use-your-own-stack.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `/brain`; `/v1`; `robot.toml` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3, 4, 5; Language model address.; Test; Model name.; Speech to text address; Text to speech address.; Key variable (optional).; Use my own stack | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `voice.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `persona`; `robot.toml`; `speech_speed`; `speech_pitch`; `url`; `stt_url`; `tts_url`; `[llm]`; `stt_model_dir`; `tts_model`; `tts_tokens`; `tts_data_dir` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3, 22, 40, 50 percent, 0.75, 1.5, 12, 12 s, 0; Planned; built; default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `wake-word-maker.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `robot.toml`; `enabled = true`; `[packages.wake_word_maker]`; `pippa` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 12 times, 3, 4, 5; on the host computer; Record the word; Record other speech; Train and check; Install; Start over; built; default; off by default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `watch-and-alerts.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; This is a convenience, not a safety device.; Planned; coming | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `watch-the-room.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: No numeric limits or counts; This is a convenience, not a safety device.; Planned; coming; built | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `web-flasher.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: No shell commands or flags | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 1, 2, 3, 4; Install | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | ok | Checked feature names, defaults, controls and status against source. |

### `which-setup.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: No inline paths, keys or endpoint values | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | ok | Checked the listed values against their config or source. |
| Counts, limits, names, controls and status: 5; Planned; coming; default | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |

### `with-maipai-home.md`

| Claim | Where verified | Result | Note |
|---|---|---|---|
| Commands and flags: `stackchan check` | `host/maipai_body/cli.py`, `host/maipai_body/service_cmd.py` | ok | Command names and accepted arguments match the parser. |
| Paths, keys, endpoints and defaults: `http://127.0.0.1:8051/brain`; `http://192.0.2.20:3000`; `brain = "home"`; `url`; `[home]`; `robot.toml` | `host/robot.example.toml`, `host/maipai_body/config.py`, package config and `schema/*.json` as relevant | fixed | Corrected the stale key or path; checked the remaining references. |
| Counts, limits, names, controls and status: 1, 127.0, 0.1, 8051, 2, 192.0, 2.20, 3000, 3; Use MaiPai Home; coming | `firmware/patches/ORDER`, feature patch headers/sources, host feature modules and `schema/tools.json` as relevant | fixed | Corrected stale status or behavior claims and removed unsupported test claims. |
