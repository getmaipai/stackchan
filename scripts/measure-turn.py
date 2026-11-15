#!/usr/bin/env python3
"""Measure first model token and first speech audio from a local compatible service."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests


class StubHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        if self.path.endswith("chat/completions"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for value in ("This is a", " measured local stub reply."):
                data = json.dumps({"choices": [{"delta": {"content": value}}]})
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
        elif self.path.endswith("audio/speech"):
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.end_headers()
            self.wfile.write(b"RIFF\x00\x00\x00\x00WAVEfmt ")
            self.wfile.flush()
        else:
            self.send_error(404)

    def log_message(self, *_args):
        pass


def stream_once(base: str, model: str, timeout: float) -> tuple[float, float]:
    started = time.perf_counter()
    response = requests.post(
        f"{base.rstrip('/')}/v1/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": "Say hello."}], "stream": True},
        stream=True,
        timeout=timeout,
    )
    response.raise_for_status()
    first_token = None
    first_sentence = None
    pending = ""
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:") or "[DONE]" in line:
            continue
        item = json.loads(line[5:].strip())
        token = item["choices"][0].get("delta", {}).get("content", "")
        if token and first_token is None:
            first_token = time.perf_counter()
        pending += token
        if any(mark in pending for mark in (".", "!", "?")):
            first_sentence = time.perf_counter()
            break
    response.close()
    if first_token is None or first_sentence is None:
        raise RuntimeError("The model did not stream a complete first sentence.")
    # Measure speech service time to its first response byte for the first sentence.
    tts = requests.post(
        f"{base.rstrip('/')}/v1/audio/speech",
        json={"model": model, "input": pending, "response_format": "wav"},
        stream=True,
        timeout=timeout,
    )
    tts.raise_for_status()
    next((chunk for chunk in tts.iter_content(4096) if chunk), None)
    first_audio = time.perf_counter()
    tts.close()
    return first_token - started, first_audio - first_sentence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="base URL; otherwise probes local ports 8791, 8080, 11434")
    parser.add_argument("--model", default="local")
    parser.add_argument("-n", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    if args.n < 1:
        parser.error("-n must be at least 1")
    base = args.url
    real = False
    for candidate in ([base] if base else [f"http://127.0.0.1:{port}" for port in (8791, 8080, 11434)]):
        try:
            response = requests.post(
                f"{candidate.rstrip('/')}/v1/chat/completions",
                json={"model": args.model, "messages": [{"role": "user", "content": "Say hello."}], "stream": True},
                stream=True,
                timeout=min(args.timeout, 2),
            )
            response.raise_for_status()
            response.close()
            base = candidate
            real = True
            break
        except requests.RequestException:
            continue
    server = None
    thread = None
    if not real:
        server = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        print("No local model answered on ports 8791, 8080, or 11434; results below are STUB only.")
    values = []
    try:
        for _ in range(args.n):
            values.append(stream_once(base, args.model, args.timeout))
    finally:
        if server:
            server.shutdown()
            thread.join()
    label = "real local server" if real else "stub server"
    for index, title in ((0, "first-token"), (1, "first-sentence-to-audio")):
        samples = sorted(row[index] * 1000 for row in values)
        p95 = samples[min(len(samples) - 1, math.ceil(0.95 * len(samples)) - 1)]
        print(f"{title} ({label}): median {statistics.median(samples):.1f} ms, p95 {p95:.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
