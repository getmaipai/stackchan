"""The pinned downloads of the minimal local stack (docs/plan/minimal-stack.md).

Every file is named by its exact address, size and SHA-256, taken from the publisher's release metadata on 2026-11-18. The installer
refuses a file that does not match. A new version is a deliberate change here, with its test.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass

LLAMA_RELEASE = "b12503"
_LLAMA = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_RELEASE}/llama-{LLAMA_RELEASE}-bin-"
_SHERPA = "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
_QWEN = "https://huggingface.co/Qwen/{repo}/resolve/{rev}/{file}"


@dataclass(frozen=True)
class Item:
    """One download. ``kind`` is "archive" (unpacked into ``dest``) or "file" (kept as ``dest`` / the file name)."""

    id: str
    label: str
    url: str
    sha256: str
    size: int
    kind: str
    dest: str
    license: str
    source: str  # who serves it, shown on the install page


RUNTIMES = {
    "macos-arm64": Item("llama-server", "Language model runtime (llama.cpp)", _LLAMA + "macos-arm64.tar.gz", "e88d7e91198d0de6ceb3d33711ac01ee0d5b519cd9ba4e81854e3bba84f22214", 17282183, "archive", "runtime", "MIT", "github.com"),
    "macos-x64": Item("llama-server", "Language model runtime (llama.cpp)", _LLAMA + "macos-x64.tar.gz", "4c42388726490b1ed7864dc621dd29526f0ced3d617a96c5ac111287a7a68ba5", 13055174, "archive", "runtime", "MIT", "github.com"),
    "linux-x64": Item("llama-server", "Language model runtime (llama.cpp)", _LLAMA + "ubuntu-x64.tar.gz", "0d585f8a78ffdfdc4f6303a089aaa1379c15323b33483b6548c85c774a376a9d", 23784463, "archive", "runtime", "MIT", "github.com"),
    "linux-arm64": Item("llama-server", "Language model runtime (llama.cpp)", _LLAMA + "ubuntu-arm64.tar.gz", "e2b566c5368e2e781b73e5c6222f9512c9e6bc563cf4863a42b675356fb6df6a", 19377874, "archive", "runtime", "MIT", "github.com"),
}

# Qwen2.5 0.5B and 1.5B are Apache-2.0 (the 3B and 72B sizes are not, so they are not offered).
MODELS = {
    "small": Item(
        "model", "Language model (Qwen2.5 0.5B, small and quick)",
        _QWEN.format(repo="Qwen2.5-0.5B-Instruct-GGUF", rev="9217f5db79a29953eb74d5343926648285ec7e67", file="qwen2.5-0.5b-instruct-q4_k_m.gguf"),
        "74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db", 491400032, "file", "model/qwen2.5-0.5b-instruct-q4_k_m.gguf", "Apache-2.0", "huggingface.co",
    ),
    "better": Item(
        "model", "Language model (Qwen2.5 1.5B, better answers, slower)",
        _QWEN.format(repo="Qwen2.5-1.5B-Instruct-GGUF", rev="91cad51170dc346986eccefdc2dd33a9da36ead9", file="qwen2.5-1.5b-instruct-q4_k_m.gguf"),
        "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e", 1117320736, "file", "model/qwen2.5-1.5b-instruct-q4_k_m.gguf", "Apache-2.0", "huggingface.co",
    ),
}
MODEL_NAMES = {"small": "qwen2.5-0.5b-instruct", "better": "qwen2.5-1.5b-instruct"}
MODEL_MEMORY_MB = {"small": 1000, "better": 2000}

SPEECH_TO_TEXT = Item(
    "stt", "Speech to text (Moonshine tiny, English)",
    _SHERPA + "asr-models/sherpa-onnx-moonshine-tiny-en-int8.tar.bz2",
    "d5fe6ec4334fef36255b2a4010412cad4c007e33103fec62fb5d17cad88086f2", 107600538, "archive", "stt", "MIT", "github.com",
)
TEXT_TO_SPEECH = Item(
    "tts", "Text to speech (Piper ljspeech, English)",
    _SHERPA + "tts-models/vits-piper-en_US-ljspeech-medium-int8.tar.bz2",
    "24dc3bd77dd48c291e52c297878d3437c9492f245d823d7f6a06c4bbb67f4b6b", 21090429, "archive", "tts", "MIT (voice data public domain)", "github.com",
)
STT_FOLDER = "sherpa-onnx-moonshine-tiny-en-int8"  # inside the unpacked archive
TTS_FOLDER = "vits-piper-en_US-ljspeech-medium-int8"
SHERPA_PACKAGE = "sherpa-onnx==1.13.8"  # Apache-2.0, from the Python package index; the speech models above run on it
SHERPA_SOURCE = "pypi.org"
LLAMA_PORT = 8081
DISK_MARGIN = 1.25  # the download plus a quarter, for unpacking


def detect_platform(system: str | None = None, machine: str | None = None) -> str | None:
    """macos-arm64, macos-x64, linux-x64 or linux-arm64; None on anything else (the page says it is not supported yet)."""
    system = (system or sys.platform).lower()
    machine = (machine or platform.machine()).lower()
    arm = machine in ("arm64", "aarch64")
    x64 = machine in ("x86_64", "amd64")
    if system == "darwin":
        return "macos-arm64" if arm else "macos-x64" if x64 else None
    if system.startswith("linux"):
        return "linux-arm64" if arm else "linux-x64" if x64 else None
    return None


def plan(platform_id: str, choice: str) -> list[Item]:
    """The files to fetch, in order, for this computer and model choice. Raises ValueError with a plain message."""
    if platform_id not in RUNTIMES:
        raise ValueError("This computer type is not supported by the local stack yet. Use your own stack or MaiPai Home.")
    if choice not in MODELS:
        raise ValueError("Pick the small or the better model.")
    return [RUNTIMES[platform_id], MODELS[choice], SPEECH_TO_TEXT, TEXT_TO_SPEECH]


def needs(platform_id: str, choice: str) -> dict[str, int]:
    """Download bytes, disk bytes and memory megabytes the install and the running stack need."""
    items = plan(platform_id, choice)
    download = sum(i.size for i in items)
    return {"download_bytes": download, "disk_bytes": int(download * DISK_MARGIN) + 250_000_000, "memory_mb": MODEL_MEMORY_MB[choice] + 400}


def recommended_choice(memory_mb: int | None) -> str:
    """The better model only on 8 GB or more; the small one otherwise or when the memory is unknown."""
    return "better" if memory_mb and memory_mb >= 8000 else "small"
