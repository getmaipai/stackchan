"""The Home Assistant connection: conversation text in, speech text out; one camera picture on request."""

from __future__ import annotations

import base64
import os
import re
import unicodedata
from collections.abc import Callable
from urllib.parse import urlsplit

import requests

MAX_REPLY_CHARS = 400
MAX_SNAPSHOT_BYTES = 3 * 1024 * 1024
_ENTITY = re.compile(r"^camera\.[a-z0-9_]+$")


class HomeAssistantError(RuntimeError):
    """A plain message the robot can say: what went wrong and what to do."""


def _scrub_speech(text: object) -> str:
    """Text the robot will say: no brackets or angle brackets (reply tags), no hidden or control characters, a length limit."""
    swapped = str(text).replace("[", " ").replace("]", " ").replace("<", " ").replace(">", " ")
    kept = "".join(ch for ch in swapped if not (unicodedata.category(ch)[0] == "C" or unicodedata.category(ch) in ("Zl", "Zp")) or ch in "\n\t ")
    return " ".join(kept.split())[:MAX_REPLY_CHARS]


class HomeAssistant:
    def __init__(
        self,
        url: str,
        *,
        token_env: str = "STACKCHAN_HA_TOKEN",
        trigger: str = "home assistant",
        cameras: dict[str, str] | None = None,
        language: str = "en",
        ask_model: Callable[[str, bytes], str] | None = None,
        session: requests.Session | None = None,
        timeout: float = 10.0,
        allow_plain_http: bool = False,
        allow_unidentified: bool = False,
        speakers: list[str] | None = None,
        child_present: Callable[[], bool] | None = None,
    ) -> None:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise HomeAssistantError("The Home Assistant address must start with http:// or https://. Fix url under [packages.home_assistant] in robot.toml.")
        if parts.scheme == "http" and parts.hostname not in {"127.0.0.1", "localhost", "::1"} and not allow_plain_http:
            raise HomeAssistantError("The Home Assistant token would travel in clear text. Use an https:// address, or set allow_plain_http = true under [packages.home_assistant] if you accept that on your home network.")
        self.allow_unidentified = allow_unidentified
        self.speakers = [name.lower() for name in (speakers or [])]
        self._child_present = child_present
        self.base = url.rstrip("/")
        self.token_env, self.trigger, self.language = token_env, trigger.lower().strip(), language
        self.cameras = {name.lower(): entity for name, entity in (cameras or {}).items() if _ENTITY.match(entity)}
        self._ask_model = ask_model
        self._session, self._timeout = session or requests.Session(), timeout

    def _headers(self) -> dict[str, str]:
        token = os.environ.get(self.token_env, "")
        if not token:
            raise HomeAssistantError(f"The Home Assistant token is not set. Create a long-lived access token in Home Assistant and export it as {self.token_env}.")
        return {"Authorization": f"Bearer {token}"}

    # ---- the spoken request -------------------------------------------------------------

    def handle(self, text: str, speaker: str | None = None) -> str | None:
        """A reply when ``text`` is for Home Assistant, else None (the model answers as usual)."""
        lowered = text.strip().lower()
        if not lowered.startswith(self.trigger):
            return None
        request = text.strip()[len(self.trigger):].lstrip(" ,:;.-").strip()
        if not request:
            return "What should I ask Home Assistant?"
        if self._child_present is not None and self._child_present():
            return "I will not do that while a child is near."
        if not self._speaker_allowed(speaker):
            return "I only do that for a person I know. Ask the owner to turn on Home Assistant for everyone."
        try:
            for name, entity in self.cameras.items():
                if re.search(r"\b(?:camera|see|show|look|what'?s)\b", request, re.I) and name in request.lower():
                    return self.describe_camera(entity, request)
            return self.converse(request)
        except HomeAssistantError as error:
            return str(error)

    def _speaker_allowed(self, speaker: str | None) -> bool:
        if speaker:
            return not self.speakers or speaker.lower() in self.speakers
        return self.allow_unidentified  # nobody was identified: only when the owner allowed that

    def converse(self, request: str) -> str:
        try:
            response = self._session.post(
                f"{self.base}/api/conversation/process",
                json={"text": request, "language": self.language},
                headers=self._headers(),
                timeout=self._timeout,
            )
            response.raise_for_status()
            speech = response.json()["response"]["speech"]["plain"]["speech"]
        except HomeAssistantError:
            raise
        except (requests.RequestException, KeyError, TypeError, ValueError):
            raise HomeAssistantError("I could not reach Home Assistant. Check its address and token in robot.toml.") from None
        speech = _scrub_speech(speech)
        return speech if speech else "Home Assistant did not answer."

    # ---- one camera picture -------------------------------------------------------------

    def snapshot(self, entity: str) -> bytes:
        if not _ENTITY.match(entity) or entity not in self.cameras.values():
            raise HomeAssistantError("That camera is not on the list. Add it under cameras in robot.toml.")
        try:
            response = self._session.get(f"{self.base}/api/camera_proxy/{entity}", headers=self._headers(), timeout=self._timeout)
            response.raise_for_status()
        except HomeAssistantError:
            raise
        except requests.RequestException:
            raise HomeAssistantError("I could not get a picture from that camera. Check that it is on.") from None
        data = response.content
        if not data or len(data) > MAX_SNAPSHOT_BYTES or not data.startswith(b"\xff\xd8"):
            raise HomeAssistantError("That camera did not send a usable picture.")
        return data

    def describe_camera(self, entity: str, request: str) -> str:
        if self._ask_model is None:
            raise HomeAssistantError("No picture-reading model is set up, so I cannot describe a camera. Set the model under [llm] in robot.toml.")
        jpeg = self.snapshot(entity)
        try:
            return _scrub_speech(self._ask_model(request, jpeg)) or "I could not make out the picture."
        except Exception:
            raise HomeAssistantError("The model could not read the picture. Use a model that accepts images.") from None


def image_question(llm_url: str, model: str, api_key_env: str | None, session: requests.Session | None = None, timeout: float = 30.0) -> Callable[[str, bytes], str]:
    """A function asking the configured chat model one question about one picture (OpenAI-style image message)."""
    http = session or requests.Session()
    from maipai_body.brain.own_llm import _endpoint

    def ask(question: str, jpeg: bytes) -> str:
        image = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")
        headers = {"Content-Type": "application/json"}
        if api_key_env and os.environ.get(api_key_env):
            headers["Authorization"] = f"Bearer {os.environ[api_key_env]}"
        body = {"model": model, "messages": [{"role": "user", "content": [{"type": "text", "text": question + " Answer in one or two short sentences."}, {"type": "image_url", "image_url": {"url": image}}]}]}
        response = http.post(_endpoint(llm_url, "/v1/chat/completions"), json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"]).strip()

    return ask
