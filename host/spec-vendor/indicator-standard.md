# Ring indicator standard

Status: approved by the owner 2026-11-13.

## The ring table

| Key | Meaning | Colour | Style | Period | Brightness | Notes |
|---|---|---|---|---:|---:|---|
| `live` | Connected | green | steady | 0s | 0.5 | Body connected |
| `camera` | Camera capture | pink | flash | 0.5s | 0.5 | Capture active |
| `pairing` | Pairing | cyan | pulse | 2s | 0.6 | Owner action |
| `attention` | Fault, offline, low battery | amber | pulse | 10s | 0.3 | One amber meaning |
| `listening` | Listening | blue | steady | 0s | 1.0 | Audio capture |
| `dance` | Dance | magenta | steady | 0s | 0.5 | Decorative |
| `idle` | Idle | dark | steady | 0s | 0 | No active state |

## Priority

Live, camera, pairing, attention, listening, dance, idle.
