#!/usr/bin/env python3
# Intent: print the mouth cue rate and levels for a speech WAV (16-bit mono or stereo), to check the 4 to 11 a second baseline.
# Usage: measure-mouth-cues.py reply.wav
# Placement: host script. Upstream: none.
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "host"))
from maipai_body import mouth_cues  # noqa: E402


def main(path: str) -> int:
    with wave.open(path, "rb") as wav:
        rate, width, channels = wav.getframerate(), wav.getsampwidth(), wav.getnchannels()
        if width != 2:
            print("The file must be 16-bit PCM. Convert it first.", file=sys.stderr)
            return 2
        data = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels)[:, 0]
    cues = mouth_cues.mouth_cues(data, rate)
    print(f"{len(cues)} cues over {cues[-1][0] / 1000:.1f} s, {mouth_cues.rate_hz(cues):.1f} a second, levels {sorted({l for _, l in cues})}")
    return 0 if 4.0 <= mouth_cues.rate_hz(cues) <= 11.0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else print("usage: measure-mouth-cues.py reply.wav") or 2)
