"""Locate an OpenSSL CLI with Ed25519 support."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def openssl_cli() -> str:
    """Return an OpenSSL executable that can generate Ed25519 keys."""
    candidates = [shutil.which("openssl")]
    candidates.extend(
        (
            "/opt/homebrew/bin/openssl",
            "/opt/homebrew/opt/openssl@3/bin/openssl",
            "/usr/local/opt/openssl@3/bin/openssl",
        )
    )
    checked: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        resolved = str(Path(candidate))
        if resolved in checked:
            continue
        checked.add(resolved)
        try:
            result = subprocess.run(
                [resolved, "genpkey", "-algorithm", "Ed25519", "-out", "/dev/null"],
                capture_output=True,
                check=False,
            )
        except OSError:
            continue
        if result.returncode == 0:
            return resolved
    raise RuntimeError("OpenSSL with Ed25519 support is required; install it with brew install openssl@3.")
