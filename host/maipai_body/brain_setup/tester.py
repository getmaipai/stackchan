"""The test buttons of mode (b): each answers in plain words. A session is injected so tests never touch the network."""

from __future__ import annotations

from typing import Any

import requests


def _fail(why: str) -> dict[str, Any]:
    return {"ok": False, "message": why}


def _get(session: Any, url: str, headers: dict[str, str] | None) -> Any:
    try:
        return session.get(url, headers=headers, timeout=6)
    except requests.exceptions.ConnectionError:
        return _fail("Nothing answered at that address. Check that the program is running and the address and port are right.")
    except requests.exceptions.Timeout:
        return _fail("The address did not answer in six seconds. Check that the program is running and not busy.")
    except requests.exceptions.RequestException:
        return _fail("That address is not valid. Type it as http:// or https:// followed by the host name or number.")


def test_model(url: str, api_key: str = "", model: str = "", session: Any = None) -> dict[str, Any]:
    """The language model address: ``/v1/models`` answers, and the named model is in its list when it gives one."""
    from maipai_body.brain.own_llm import _endpoint

    session = session or requests
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    response = _get(session, _endpoint(url, "/v1/models"), headers)
    if isinstance(response, dict):
        return response
    if response.status_code in (401, 403):
        return _fail("The model server refused the key. Check the key variable and that it holds the right key.")
    if response.status_code == 404:
        return _fail("The server answered but has no /v1/models. Use the address of an OpenAI-style server (the part before /v1).")
    if response.status_code >= 400:
        return _fail(f"The model server answered with an error ({response.status_code}). Check its own log.")
    try:
        names = [m.get("id", "") for m in response.json().get("data", []) if isinstance(m, dict)]
    except ValueError:
        names = []
    if model and names and model not in names:
        return {"ok": False, "message": f"The server is there, but it has no model named {model}. It has: {', '.join(names[:5])}.", "models": names[:20]}
    return {"ok": True, "message": "The model server answered." + (f" Models: {', '.join(names[:5])}." if names else ""), "models": names[:20]}


def test_speech(url: str, kind: str, session: Any = None) -> dict[str, Any]:
    """A speech-to-text or text-to-speech address: something answers there. Any HTTP answer counts as 'there'."""
    session = session or requests
    response = _get(session, url, None)
    if isinstance(response, dict):
        return response
    word = "speech-to-text" if kind == "stt" else "text-to-speech"
    if response.status_code >= 500:
        return _fail(f"The {word} server answered with an error ({response.status_code}). Check its own log.")
    return {"ok": True, "message": f"The {word} server answered."}
