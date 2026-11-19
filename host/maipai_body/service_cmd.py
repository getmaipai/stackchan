"""`stackchan service install|status|start|stop|logs|uninstall`: the host as a managed service.

launchd on a Mac, a systemd user unit on Linux and a Raspberry Pi, a scheduled task on Windows (written, not tested here: no Windows
machine). The same program runs either way: the service just runs `stackchan run`. Everything that touches the system goes through ``run``,
so tests use a fake. See docs/plan/service-and-supervision.md."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

LABEL = os.environ.get("MAIPAI_SERVICE_LABEL") or "com.maipai.stackchan"  # the override is for tests: a throwaway label never touches a real service
UNIT = "stackchan.service"
TASK = "MaiPai StackChan"


def _data_dir() -> Path:
    return Path(os.environ.get("MAIPAI_BOT_DATA_DIR") or (Path.home() / ".local/share/maipai-bot"))


def log_path() -> Path:
    return _data_dir() / "logs" / "stackchan.log"


def original_program() -> list[str]:
    """The command of the install this program runs from (before any `stackchan service update`)."""
    beside = Path(sys.executable).parent / "stackchan"
    found = str(beside) if beside.exists() else shutil.which("stackchan")
    return [found or sys.executable, "run"] if found else [sys.executable, "-m", "maipai_body.cli", "run"]


def program() -> list[str]:
    """The command the service runs: the version `stackchan service update` switched to, else the `stackchan` of this install."""
    from maipai_body.host_update import current_program

    updated = current_program(_data_dir())
    return [str(updated), "run"] if updated else original_program()


def system_name() -> str:
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    return "other"


def render_launchd(command: list[str], log: Path, env: dict[str, str]) -> str:
    args = "".join(f"    <string>{_x(a)}</string>\n" for a in command)
    variables = "".join(f"    <key>{_x(k)}</key><string>{_x(v)}</string>\n" for k, v in sorted(env.items()))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array>
{args}  </array>
  <key>EnvironmentVariables</key><dict>
{variables}  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>{_x(str(log))}</string>
  <key>StandardErrorPath</key><string>{_x(str(log))}</string>
</dict></plist>
"""


def render_systemd(command: list[str], env: dict[str, str]) -> str:
    exec_line = " ".join(_q(a) for a in command)
    variables = "".join(f'Environment="{k}={v}"\n' for k, v in sorted(env.items()))
    return f"""[Unit]
Description=MaiPai StackChan host
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
ExecStart={exec_line}
Restart=on-failure
RestartSec=5
{variables}
[Install]
WantedBy=default.target
"""


def _x(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _q(text: str) -> str:
    return f'"{text}"' if " " in text else text


def service_env() -> dict[str, str]:
    env = {"MAIPAI_LOG_FILE": str(log_path()), "MAIPAI_HUB_HOST": "1", "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    if os.environ.get("MAIPAI_BOT_DATA_DIR"):
        env["MAIPAI_BOT_DATA_DIR"] = os.environ["MAIPAI_BOT_DATA_DIR"]
    # A host started by hand with its own ports or body keeps them when it hands over to the service (decision 28): the service is the same host, not a new setup.
    for name in ("HOME", "MAIPAI_BODY", "MAIPAI_XIAOZHI_PORT", "MAIPAI_STACKCHAN_AVATAR_PORT", "MAIPAI_STACKCHAN_SETTINGS_PORT", "MAIPAI_VISION_PORT"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    return env


class Service:
    def __init__(self, *, system: str | None = None, home: Path | None = None, run: Callable[..., Any] = subprocess.run, uid: int | None = None, command: list[str] | None = None, say: Callable[[str], None] = print) -> None:
        self.system = system or system_name()
        self.home = home or Path.home()
        self._run, self._say = run, say
        self.uid = os.getuid() if uid is None and hasattr(os, "getuid") else (uid or 0)
        self.command = command or program()

    def original_command(self) -> list[str]:
        return original_program()

    # -- where the file goes ------------------------------------------------------------------------------------------------
    def file(self) -> Path:
        if self.system == "mac":
            return self.home / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        if self.system == "linux":
            return self.home / ".config" / "systemd" / "user" / UNIT
        return self.home / ".config" / "maipai" / "windows-task.cmd"

    def _do(self, command: list[str]) -> tuple[bool, str]:
        try:
            result = self._run(command, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            return False, f"{command[0]} could not run ({type(error).__name__})"
        return result.returncode == 0, (result.stdout or "") + (result.stderr or "")

    # -- commands ----------------------------------------------------------------------------------------------------------
    def install(self) -> int:
        if self.system == "other":
            self._say("This computer type is not supported by `stackchan service` yet. Run `stackchan run` by hand.")
            return 1
        log_path().parent.mkdir(parents=True, exist_ok=True)
        env = service_env()
        target = self.file()
        target.parent.mkdir(parents=True, exist_ok=True)
        if self.system == "mac":
            target.write_text(render_launchd(self.command, log_path(), env), encoding="utf-8")
            self._do(["launchctl", "bootout", f"gui/{self.uid}/{LABEL}"])  # replace an older copy
            ok, why = self._do(["launchctl", "bootstrap", f"gui/{self.uid}", str(target)])
            if not ok:
                self._say(f"The service file was written to {target}, but the system would not load it: {why.strip()[:160]}. Log out and in again, or run `stackchan service start`.")
                return 1
            self._say(f"Installed. The host starts at login and restarts itself if it stops. Service file: {target}. Logs: {log_path()}.")
            return 0
        if self.system == "linux":
            target.write_text(render_systemd(self.command, env), encoding="utf-8")
            for command in (["systemctl", "--user", "daemon-reload"], ["systemctl", "--user", "enable", "--now", UNIT]):
                ok, why = self._do(command)
                if not ok:
                    self._say(f"The service file was written to {target}, but `{' '.join(command)}` failed: {why.strip()[:160]}.")
                    return 1
            linger_ok, _ = self._do(["loginctl", "enable-linger", os.environ.get("USER", "")])
            self._say(f"Installed. The host restarts itself if it stops. Service file: {target}. Logs: {log_path()} and `journalctl --user -u stackchan`."
                      + ("" if linger_ok else " To start at boot without a login, an administrator runs: sudo loginctl enable-linger <your user>."))
            return 0
        line = " ".join(_q(a) for a in self.command)
        target.write_text(f'@echo off\nset MAIPAI_LOG_FILE={log_path()}\nset MAIPAI_HUB_HOST=1\n{line}\n', encoding="utf-8")
        ok, why = self._do(["schtasks", "/create", "/tn", TASK, "/tr", str(target), "/sc", "onlogon", "/f"])
        self._say("Installed as a scheduled task that starts at login. (Windows support is written but not tested yet.)" if ok else f"The scheduled task could not be created: {why.strip()[:160]}")
        return 0 if ok else 1

    def start(self) -> int:
        commands = {"mac": [["launchctl", "bootstrap", f"gui/{self.uid}", str(self.file())], ["launchctl", "kickstart", f"gui/{self.uid}/{LABEL}"]], "linux": [["systemctl", "--user", "start", UNIT]], "windows": [["schtasks", "/run", "/tn", TASK]]}.get(self.system, [])
        ok = False
        for command in commands:
            ok = self._do(command)[0] or ok
        self._say("Started." if ok else "It did not start. Run `stackchan service install` first, then `stackchan service status`.")
        return 0 if ok else 1

    def stop(self) -> int:
        command = {"mac": ["launchctl", "bootout", f"gui/{self.uid}/{LABEL}"], "linux": ["systemctl", "--user", "stop", UNIT], "windows": ["schtasks", "/end", "/tn", TASK]}.get(self.system)
        ok = bool(command) and self._do(command)[0]
        self._say("Stopped. It will start again at your next login." if ok else "It was not running, or it could not be stopped. Run `stackchan service status`.")
        return 0 if ok else 1

    def status(self) -> int:
        installed = self.file().exists()
        if not installed:
            self._say("The service is not installed. Run `stackchan service install`.")
            return 1
        command = {"mac": ["launchctl", "print", f"gui/{self.uid}/{LABEL}"], "linux": ["systemctl", "--user", "is-active", UNIT], "windows": ["schtasks", "/query", "/tn", TASK]}[self.system]
        ok, text = self._do(command)
        running = ("state = running" in text) if self.system == "mac" else (text.strip().startswith("active") if self.system == "linux" else ok)
        self._say("The service is installed and running." if running else "The service is installed but not running. Run `stackchan service start`, then `stackchan service logs`.")
        self._say_last_update()
        return 0 if running else 1

    def _say_last_update(self) -> None:
        """The outcome of the last `stackchan service update`, when it did not take (so the person is not left wondering)."""
        import json

        try:
            kept = json.loads((_data_dir() / "host-versions" / "last-update.json").read_text())
        except (OSError, ValueError):
            return
        if kept.get("ok") is False:
            self._say("Last update: " + str(kept.get("message", "it did not take")))

    def logs(self, lines: int = 60) -> int:
        path = log_path()
        if not path.exists():
            self._say(f"No log yet at {path}. The host writes it once it runs as a service.")
            return 1
        tail = path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
        self._say("\n".join(tail))
        return 0

    def uninstall(self) -> int:
        self.stop()
        if self.system == "linux":
            self._do(["systemctl", "--user", "disable", UNIT])
        if self.system == "windows":
            self._do(["schtasks", "/delete", "/tn", TASK, "/f"])
        target = self.file()
        if target.exists():
            target.unlink()
        if self.system == "linux":
            self._do(["systemctl", "--user", "daemon-reload"])
        self._say("Removed. Your settings, pairings and notes are untouched.")
        return 0
