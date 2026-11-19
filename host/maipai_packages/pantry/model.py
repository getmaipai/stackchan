"""The owner's own model as a plain function ``ask(prompt) -> text`` for the pantry (an OpenAI-style chat address from `[llm]` in robot.toml).

Nothing is sent anywhere else; the address is the one the owner set. A missing address or an unreachable model raises, and the callers stop and try later."""

from __future__ import annotations

import os

import requests


def chat_function(url: str, model: str = "", api_key_env: str = "", timeout: float = 60.0):
    if not url:
        raise ValueError("No model address is set. Choose a brain on the Brain page, then try again.")
    base = url.rstrip("/")
    endpoint = base if base.endswith("/chat/completions") else base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions")
    headers = {"Authorization": "Bearer " + os.environ[api_key_env]} if api_key_env and os.environ.get(api_key_env) else {}

    def ask(prompt: str) -> str:
        body = {"messages": [{"role": "user", "content": prompt}], "temperature": 0.8, "stream": False}
        if model:
            body["model"] = model
        reply = requests.post(endpoint, json=body, headers=headers, timeout=timeout)
        reply.raise_for_status()
        return reply.json()["choices"][0]["message"]["content"] or ""

    return ask
