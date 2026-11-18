# Troubleshooting

| What you see | What to do |
|---|---|
| The view shows only the face, or says the screens are not built | Build them once: `bash scripts/virtual-unit/build-face.sh`, then `bash scripts/virtual-unit/build-screens.sh`. |
| The address does not open | Check the port. Start it on another one: `python3 scripts/virtual-unit/view.py 8781`. |
| The 3D view is empty | The viewer needs its drawing library. If you are offline, the flat screen still works. |
| A screen looks different from a picture here | The pictures follow the newest firmware tree. Rebuild the screens, then run `python3 scripts/virtual-unit/scenarios.py`. |
| No sound | The playground does not play sound yet. Open the WAV files in `docs/dev/game-sounds/` instead. |

Back: [Start here](start-here.md).
