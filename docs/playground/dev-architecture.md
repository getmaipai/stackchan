# Architecture of the virtual unit

The virtual unit is a body for the real host and the real display code, built from the pieces below. All of it lives in `scripts/virtual-unit/` unless noted.

| Piece | What it is |
|---|---|
| **Renderer** | The unit's own LVGL display code (the face, banner, pages, settings, More, first run) compiled for the computer by `scripts/fw-face-render/`. It reads one command a line and writes pictures. Built by `build-face.sh` and `build-screens.sh`. |
| **Cores** | The unit's own C headers (dance ladder, reconnect rules, game sounds, first run) compiled to small libraries and called with ctypes: `dance_core.py`, `host_away.py`. Nothing is copied by hand. |
| **Tool registry** | One handler per firmware tool (`tools/*.py`), checked against `schema/tools.json`. |
| **Fake clock** | `VirtualUnit.advance(ms)` moves time. Tickers (the dance, the memory sweep) run after every slice. |
| **Hardware model** | `hw.py`: battery, power, USB ports, carried and tilted, the dance paths. Values that were not measured are marked assumed. |
| **Memory model** | `memory_model.py`, from `schema/memory-budget.json`. |
| **Asset store** | `assets_sim.py`, from `schema/asset-kinds.json`. |
| **Physics and 3D** | `physics/`, `view3d.js`, the model in `model/`. |
| **E2E rigs** | `e2e*.py` run the real host against virtual units. |

Back: [index](index.md).
