#!/usr/bin/env python3
"""Writes firmware/maipai_facedet.compile_req.yml: the op list the face models need, so esp-dl compiles only those (patch FD01).

Intent: esp-dl compiles every one of its 81 operators and every convolution kernel unless a model component hands it a compile_req
file (cmake/compile_register.cmake). Without one the library is 1.44 MB of code; the two face model families use ten operators.
The operators a model uses are plain strings in its .espdl file, so this finds them there. The convolution kernels a model picks
are chosen at run time by shape, so every 8-bit kernel of the chip's family (the ESP32-S3 vector kernels and the C ones) stays in: only
the unused operators and the 16-bit kernels go. A model that needs an operator this list lacks fails to load with an esp-dl error, never silently.
Usage: python3 scripts/fw-facedet-req.py <managed_components dir> <out yml>
Placement: developer tooling (reads the downloaded model package; nothing runs on the robot). Upstream: none (ours).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MODELS = (
    "human_face_detect_msr_s8_v1.espdl",
    "human_face_detect_mnp_s8_v1.espdl",
    "espdet_pico_224_224_face.espdl",
)
# Operators the postprocessing or a model variant could still need that are cheap: kept as a margin.
MARGIN = ("Reshape", "Transpose", "Sigmoid", "Slice", "Identity")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    comp = Path(argv[1])
    dl = comp / "espressif__esp-dl"
    text = (dl / "spec" / "ops.yml").read_text()
    ops = re.findall(r"^  ([A-Za-z0-9_]+):\s*$", text.split("\nops:", 1)[1], re.M)
    blobs = [(comp / "espressif__human_face_detect" / "models" / "s3" / name).read_bytes() for name in MODELS]
    used = sorted({op for op in ops if any(op.encode() in blob for blob in blobs)} | set(MARGIN))
    kernels_text = (dl / "spec" / "kernels.yml").read_text()
    abi = int(re.search(r"^kernel_abi:\s*(\d+)", kernels_text, re.M).group(1))
    syms = re.findall(r"^  - (\S+)$", kernels_text, re.M)
    # Both model families are 8-bit (s8). The 16-bit and the 8-bit-weight/16-bit-activation kernels (a third of the kernel code) stay out.
    kernels = [s for s in syms if "esp32p4" not in s and "_s16_" not in s and "w8a16" not in s]
    lines = [f"kernel_abi: {abi}", "ops:", *[f"  - {o}" for o in used], "kernels:", *[f"  - {k}" for k in kernels], ""]
    Path(argv[2]).write_text("\n".join(lines))
    print(f"{len(used)} of {len(ops)} operators, {len(kernels)} kernels: {', '.join(used)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
