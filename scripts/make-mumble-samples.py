#!/usr/bin/env python3
"""Make the offline mumble samples to listen to: docs/dev/mumble/<lang>.wav (8 kHz, 16 bit, about 3 seconds each) from the reference implementation
(scripts/virtual-unit/mumble.py, the same algorithm as the unit's maipai_mumble_core.h), and docs/dev/mumble/samples.json (the text, the length, the mouth levels every 33 ms).
Usage: python3 scripts/make-mumble-samples.py. Original synthesis, released as CC0-1.0. Placement: docs tooling. Upstream: none."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
import mumble  # noqa: E402

OUT = ROOT / "docs" / "dev" / "mumble"
SAMPLES = [
    ("en", "English", "Hello! I am your robot. How can I help you today?", 3300),
    ("es", "Spanish", "¡Hola! Soy tu robot. ¿En qué puedo ayudarte hoy?", 3300),
    ("fr", "French", "Bonjour ! Je suis ton robot. Comment puis-je t'aider aujourd'hui ?", 3800),
    ("de", "German", "Hallo! Ich bin dein Roboter. Wie kann ich dir heute helfen?", 3500),
    ("pt", "Portuguese", "Olá! Eu sou o teu robô. Como posso ajudar-te hoje?", 3200),
    ("it", "Italian", "Ciao! Sono il tuo robot. Come posso aiutarti oggi?", 3200),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for code, name, text, ms in SAMPLES:
        b = mumble.blips(text, 0, ms)
        mumble.write_wav(str(OUT / f"{code}.wav"), mumble.render(b))
        manifest.append({"id": code, "language": name, "text": text, "caption_ms": ms, "blips": len(b), "mouth_33ms": mumble.mouth_schedule(b)})
    (OUT / "samples.json").write_text(json.dumps({"license": "CC0-1.0", "rate_hz": 8000, "samples": manifest}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.glob("*.wav"))
    print(f"wrote {len(SAMPLES)} samples to {OUT.relative_to(ROOT)} ({total / 1000:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
