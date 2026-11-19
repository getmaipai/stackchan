"""Apply one of the three modes to robot.toml with a small line editor that keeps the rest of the file (comments and all)."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import tomllib
from pathlib import Path
from typing import Any

from maipai_body.brain_setup import catalog

_WRITE_LOCK = threading.RLock()  # one writer at a time in this process: read, edit and replace happen under it
_TABLE = re.compile(r"^\s*\[([^\[\]]+)\]\s*(?:#.*)?$")


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))  # a TOML basic string is JSON-compatible for the characters we write


def set_values(path: Path, table: str, values: dict[str, Any], remove: tuple[str, ...] = ()) -> None:
    """Set keys in ``[table]`` (``""`` is the top of the file) and drop the keys in ``remove``. Other lines stay as they are.
    The file is written to a temp file beside it and swapped in, so a crash never leaves it half written."""
    with _WRITE_LOCK:
        _set_values(Path(path), table, values, remove)


def _set_values(path: Path, table: str, values: dict[str, Any], remove: tuple[str, ...]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out: list[str] = []
    current = ""
    seen: set[str] = set()
    last_in_table = -1
    table_seen = table == ""
    for line in lines:
        m = _TABLE.match(line)
        if m:
            if current == table and not seen >= set(values):  # leaving the table: add what was missing
                missing = [k for k in values if k not in seen]
                out[last_in_table + 1 : last_in_table + 1] = [f"{k} = {_fmt(values[k])}" for k in missing]
                seen |= set(missing)
            current = m.group(1).strip()
            table_seen = table_seen or current == table
        key = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", line)
        if key and current == table:
            name = key.group(1)
            if name in remove:
                continue
            if name in values:
                line = f"{name} = {_fmt(values[name])}"
                seen.add(name)
        out.append(line)
        if current == table and line.strip():
            last_in_table = len(out) - 1
    missing = [k for k in values if k not in seen]
    if missing:
        block = [f"{k} = {_fmt(values[k])}" for k in missing]
        if table == "":
            out[0:0] = block
        elif table_seen and current == table:
            out[last_in_table + 1 : last_in_table + 1] = block
        elif table_seen:
            # the table exists but is followed by others and had no room above: place after its last line
            index = next((i for i, l in enumerate(out) if (mm := _TABLE.match(l)) and mm.group(1).strip() == table), len(out) - 1)
            out[index + 1 : index + 1] = block
        else:
            out += ([""] if out and out[-1].strip() else []) + [f"[{table}]"] + block
    text = "\n".join(out) + "\n"
    tomllib.loads(text)  # never leave a file the host cannot read
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def apply_home(path: Path, url: str) -> None:
    url = url.strip()
    if not re.match(r"^https?://[^\s]+$", url):
        raise ValueError("Type Home's address as http:// or https:// followed by the host name or number, for example http://192.0.2.10:8000.")
    set_values(path, "", {"brain": "home"})
    set_values(path, "home", {"url": url})


def apply_own(path: Path, llm_url: str, model: str, stt_url: str, tts_url: str, api_key_env: str = "") -> None:
    for name, value in (("model", llm_url), ("speech-to-text", stt_url), ("text-to-speech", tts_url)):
        if not re.match(r"^https?://[^\s]+$", value.strip()):
            raise ValueError(f"The {name} address must start with http:// or https://. Check it and try again.")
    values: dict[str, Any] = {"url": llm_url.strip(), "model": model.strip(), "stt_url": stt_url.strip(), "tts_url": tts_url.strip()}
    if api_key_env.strip():
        values["api_key_env"] = api_key_env.strip()
    set_values(path, "", {"brain": "llm"})
    set_values(path, "llm", values, remove=("stt_model_dir", "tts_model", "tts_tokens", "tts_data_dir"))
    set_values(path, "local_stack", {"enabled": False})


def apply_local(path: Path, choice: str, paths: dict[str, str]) -> None:
    set_values(path, "", {"brain": "llm"})
    set_values(path, "llm", {
        "url": f"http://127.0.0.1:{catalog.LLAMA_PORT}", "model": catalog.MODEL_NAMES[choice],
        "stt_model_dir": paths["stt_model_dir"], "tts_model": paths["tts_model"],  # the voice's tokens and data folder are found beside the model
    }, remove=("stt_url", "tts_url", "api_key_env", "tts_tokens", "tts_data_dir"))
    set_values(path, "local_stack", {"enabled": True, "choice": choice})


def clear_local(path: Path) -> None:
    """After a removal: the model, speech and stack lines go (the brain setting stays for the person to choose again)."""
    set_values(path, "llm", {}, remove=("stt_model_dir", "tts_model", "tts_tokens", "tts_data_dir"))
    set_values(path, "local_stack", {"enabled": False}, remove=("choice",))
