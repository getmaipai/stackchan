# The minimal local stack and the three ways to get a brain

Owner decision 12 of 2026-11-18: a friend picks one of three at first run, without a terminal.

| | What it is | What the person needs |
|---|---|---|
| (a) MaiPai Home | The robot uses a Home hub: its address, then pairing | A hub on the network |
| (b) Your own stack | The person's own language model, speech-to-text and text-to-speech servers | Three addresses, a test button for each |
| (c) A minimal local stack | The host downloads small defaults for all three and runs them on this computer | About 2 GB of disk, 2 GB of free memory, a network connection for the download only |

Nothing leaves the computer in (c) after the download, and the host calls no address the owner did not configure: the three download addresses are shown on the install page before anything starts, and the install is an explicit button.

## Components (candidates and picks)

All open, permissively licensed, CPU-only on a laptop. Downloaded at install time, never vendored, each pinned by exact release and SHA-256 (taken from the publisher's release metadata on 2026-11-18; the installer refuses a file that does not match).

| Stage | Pick | License | Download | On disk | Why this one |
|---|---|---|---|---|---|
| Language model runtime | llama.cpp `llama-server`, release b12503 (macOS arm64 17.3 MB, macOS x64 13.1 MB, Linux x64 23.8 MB, Linux arm64 19.4 MB) | MIT | 13 to 24 MB | about 50 MB | Serves the OpenAI-style `/v1/chat/completions` the host already speaks; one static binary; Apple, x64 and Raspberry Pi builds |
| Language model | Qwen2.5-0.5B-Instruct, Q4_K_M GGUF | Apache-2.0 | 491 MB | 491 MB | Smallest model that holds a short spoken conversation; fastest turn |
| Language model (better) | Qwen2.5-1.5B-Instruct, Q4_K_M GGUF | Apache-2.0 | 1.12 GB | 1.12 GB | Noticeably better answers; offered when the computer has 8 GB or more and a quick CPU |
| Speech to text | Moonshine tiny English, int8 (sherpa-onnx package) | MIT | 108 MB | about 190 MB | Built for short live speech on a CPU; the host's engine (`MoonshineStt`) already reads exactly these files |
| Text to speech | Piper `en_US-ljspeech-medium`, int8 (sherpa-onnx package) | Piper MIT; voice data public domain (LJ Speech) | 21 MB | about 90 MB with the espeak data | Natural for its size; the host's `PiperTts` already reads these files. The Amy voice was rejected: its dataset license is "see URL" and not clear |

Pins are in `host/maipai_body/brain_setup/catalog.py`; licenses go in `THIRD-PARTY.md` (Qwen2.5 0.5B and 1.5B are Apache-2.0; the 3B and 72B sizes are not, so they are not offered).

Python runtime for the speech parts: `sherpa-onnx==1.13.8` (Apache-2.0), installed into the host's own Python by the installer (`uv pip install`, else `pip`) when it is missing; `pypi.org` is shown on the install page with the other two sites.

## Sizes and needs shown before starting

- Download: 0.5B choice about 640 MB; 1.5B choice about 1.27 GB (runtime plus model plus speech).
- Disk: the download size plus 25 percent, checked with the free space of the target folder; the page names the folder and refuses with a plain message when there is not enough.
- Memory: 0.5B about 1.0 GB while running; 1.5B about 2.0 GB. The host reads the computer's memory and recommends 0.5B below 8 GB.

## Time per stage

Measured on 2026-11-18 on the development Mac (Apple silicon, arm64), with the real installer, the real pinned downloads and the small model:

| Stage | Measured here | Estimate on a Raspberry Pi 5 (not measured) |
|---|---|---|
| Speech to text, a 6.6 s spoken sentence | 0.06 s (heard it correctly) | 1 to 2 s |
| Model, first word (Qwen2.5 0.5B) | 0.36 s | 1 to 2 s |
| Model, a 10-word reply, in all | 0.39 s | 3 to 6 s |
| Text to speech, first sentence | 0.06 s | 0.6 to 1.2 s |
| Time to first spoken word, in all | about 0.5 s | about 3 to 5 s |

The install downloaded 637 MB, passed every checksum and took about 25 seconds on a fast connection. The installer repeats the measurement on the person's own computer at the end of the install (a timed model turn and a timed speech clip from the Moonshine package) and the page shows it. If the total is over 6 s, the page says so in plain words and offers a smaller model or the other two ways. The better (1.5B) model was not timed here; expect about three times the model time.

## What the host does

- `brain_setup/catalog.py`: the pinned list, per platform.
- `brain_setup/installer.py`: downloads each file to a temporary name, checks size and SHA-256, unpacks into `<data dir>/local-stack/`, writes `robot.toml` for mode (c), starts `llama-server` as a child of the host on `127.0.0.1` only, reports progress as one JSON state (`idle`, `downloading file N of M, percent`, `unpacking`, `testing`, `ready`, `failed: reason`), can be stopped (the partial file is removed) and removed (the folder and the config lines go). The downloader is injected, so tests use a fake.
- `brain_setup/modes.py`: applies one of the three modes to `robot.toml` through the existing config writer, one place.
- `brain_setup/tester.py`: the test buttons for mode (b): the model address (`/v1/models`, the `/v1` handling that `stackchan check` uses), the speech to text address and the text to speech address, each answering in plain words.
- Settings page: a "Brain" page (mode, the three forms, install progress, remove) and a first-run page that opens when no brain is set.
- Mode (a) reuses the existing Home address and pairing.

## Risks

- The pinned llama.cpp release will age; a new pin is a deliberate commit (the catalog test fails when a SHA changes without its version).
- Qwen2.5 0.5B gives short, sometimes wrong answers. The page says "small model" and offers 1.5B; the owner's rule that the own-LLM brain adds no content filter stays (decision 13 of the earlier list).
- `sherpa-onnx` must load on the person's machine; the installer's last test turn proves it and says what to do when it does not (a plain message, not a trace).
- Raspberry Pi: the Linux arm64 build has no GPU path and is slow; the page shows the measured time and does not hide it.
- The download hosts (GitHub release assets, Hugging Face) are third parties; each address is shown before the install and nothing else is contacted.
- Antivirus or a proxy can block the downloads: the failure says which file and address, and offers to keep the folder so a retry resumes.
