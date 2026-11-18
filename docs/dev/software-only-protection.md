# Protecting the lock code, tokens and link key with software only (owner decision 14: no eFuse, ever)

Firmware track, 2026-11-18. Owner decision 14: nothing burns an eFuse, so there is no flash encryption, no NVS encryption keyed from the chip and no secure boot key. `scripts/efuse-check.py` (run by `scripts/check.sh` and by every build) fails if a config, a patch, a script or an image could burn one. This note says what the software-only protection is, and exactly what a person with the unit and a USB cable can read.

## Where each secret lives

| Secret | Where | Form |
|---|---|---|
| Lock code | NVS namespace `mp_lock` | a 16 byte random salt and a PBKDF2 (HMAC-SHA-256, 2000 rounds) hash; the code itself is never stored; the hash is never in any report |
| Host pairing token | NVS namespace `websocket` (key `token`) | plain text |
| Wi-Fi passwords | the radio's own NVS partition area (`nvs.net80211`) | plain text |
| Link key `K` (encrypted link) | NVS namespace `mp_link` | 32 raw bytes |
| Privacy state, lock attempt counters, build floor | NVS namespaces `maipai_priv`, `mp_lock`, `mp_update` | plain values |
| Update signature public key | in the firmware image | a public key: no secret |

## What someone with the unit and a USB cable can read

Everything in the table. `esptool read_flash 0x9000 0x4000` returns the NVS partition in seconds; no password protects the USB boot loader and nothing is encrypted. So that person gets:

- the pairing token and the link key `K` (and can impersonate the unit to its host, and decrypt the encrypted link traffic they captured),
- the Wi-Fi passwords,
- the lock hash and salt, and from them the lock code: a 4 to 6 digit code has at most 1,111,100 possibilities, so any password-stretching setting still falls to a laptop in minutes to hours (2000 rounds: seconds; 100,000 rounds: well under an hour on a graphics card). **No software-only hash can protect a short code from someone who holds the flash.**
- they can also simply erase the lock record and set a new one, or flash their own image.

## What the software protects against

| Threat | Protection |
|---|---|
| A visitor touching the unit | the lock keypad; the code is checked on the unit; auto lock; a locked unit refuses voice and tools that change settings |
| A person on the network guessing the code through the unit's tools | the lock tools refuse after 5 wrong "current" codes for 60 s, the lockout doubles on each repeat, and the count and the lockout survive a restart (patches SF01, SF13, SF16) |
| A person on the home network reading or changing traffic | the encrypted link (TLS pre-shared key from the pairing exchange) once it is on; plain WebSocket before |
| A stolen unit used to reach the household's host | the host can revoke the unit's pairing; the stolen unit's token and link key then stop working at the host |
| A wrong or old update | signed update header with build number, board id and a floor that survives a USB flash (SF25, SF37, SF41) |

It does not protect secrets from someone who can read the flash; it limits what a stolen unit can do once the household acts (revoke the pairing at the host, change Wi-Fi passwords).

## The lock hash: parameters and what can still be done

- **Today:** PBKDF2-HMAC-SHA-256, 2000 rounds, 16 byte salt, constant-time compare. The keypad checks the code on every digit from the fourth, so a six-digit entry runs the hash up to three times; at about 2 SHA-256 blocks per round that is about 4000 blocks per check, estimated at 40 to 80 ms in the portable C core (to measure).
- **Raising the rounds** costs the person at the keypad time on each digit (the budget is about 300 ms per check) and buys a small constant factor against the offline attack above. If the owner wants it anyway, the safe way is a versioned record: store the round count beside the hash, accept old records at 2000 rounds and re-hash at the new count on the next correct unlock. That needs the unit's measured time per round first.
- **To measure on the unit:** the time of 2000 rounds in the current core and with the chip's SHA hardware (mbedTLS/PSA) behind it; `self.bench.lock_kdf_time {rounds}` is not built yet. Numbers needed: ms for 2000, 10,000 and 50,000 rounds.
- **The keypad has no lockout** (owner decision 2026-11-17: none for now). A person at the keypad can try codes without delay. The repository's note `docs/design/lock-and-radio-2026-11-17.md` names the risk; `LK_WRONG_DELAY_MS` is the one place to raise it.

## What would protect against a person with USB access

Only a secret the flash does not hold: a chip-bound key (eFuse HMAC) or flash encryption, both of which burn an eFuse and are ruled out; or a longer secret typed by the owner (a passphrase, not four digits), which the keypad does not offer. State it in the owner's own words on the lock page: the lock keeps visitors and the network out, it does not stop someone who takes the unit apart.

## Rules kept

No eFuse writes, no secure boot, no flash or NVS encryption, no HMAC key block (`scripts/efuse-check.py`, in `scripts/check.sh`, and the build prints it at the end); secrets never in logs or reports; the key and token in normal NVS with the limits above.
