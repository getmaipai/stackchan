"""The Brain page's one object: what is set now, the test buttons, applying a mode, and the local stack's install, start and removal."""

from __future__ import annotations

import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from maipai_body import brain_route
from maipai_body.brain_setup import catalog, modes, runner, tester
from maipai_body.brain_setup.installer import Installer


class BrainSetup:
    def __init__(
        self,
        config_path: Path,
        stack_folder: Path,
        *,
        installer: Installer | None = None,
        llama: runner.LlamaServer | None = None,
        session: Any = None,
        timer: Callable[[str, str], dict[str, Any]] | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.on_leave_hosted: Callable[[], object] | None = None  # the host asks each unit to erase its vendor link
        self.llama = llama or runner.LlamaServer()
        self._session = session
        self._timer = timer or self._measure
        self.installer = installer or Installer(stack_folder, test_turn=self._test_turn, on_ready=self._installed)
        if installer is not None:
            installer._test_turn, installer._on_ready = installer._test_turn or self._test_turn, installer._on_ready or self._installed

    # -- reading ---------------------------------------------------------------------------------------------------------
    def current(self) -> dict[str, Any]:
        try:
            raw = tomllib.loads(self.config_path.read_text(encoding="utf-8")) if self.config_path.exists() else {}
        except tomllib.TOMLDecodeError:
            return {"mode": "none", "problem": "robot.toml could not be read. Fix it, or press a mode below to write it again."}
        llm, local = raw.get("llm", {}), raw.get("local_stack", {})
        brain = raw.get("brain", "")
        if brain == "home" and raw.get("home", {}).get("url"):
            mode = "home"
        elif local.get("enabled"):
            mode = "local"
        elif llm.get("url") or llm.get("stt_url") or llm.get("tts_url"):
            mode = "own"
        else:
            mode = "none"
        return {
            "mode": mode,
            "route": brain_route.read(self.config_path),
            "hosted_proven": brain_route.HOSTED_PROVEN,
            "voice_line": brain_route.VOICE_LINE,
            "home_url": raw.get("home", {}).get("url", ""),
            "llm_url": llm.get("url", ""), "model": llm.get("model", ""), "stt_url": llm.get("stt_url", ""), "tts_url": llm.get("tts_url", ""), "api_key_env": llm.get("api_key_env", ""),
        }

    def needs_choice(self) -> bool:
        """True on a first run: no brain is set yet, so the first-run page asks."""
        return self.current()["mode"] == "none"

    def view(self) -> dict[str, Any]:
        return {**self.current(), "install": self.installer.state(), "overview": self.installer.overview(), "running": self.llama.running()}

    # -- the test buttons (mode b) -----------------------------------------------------------------------------------------
    def test(self, kind: str, url: str, model: str = "", api_key: str = "") -> dict[str, Any]:
        if kind == "model":
            return tester.test_model(url, api_key, model, self._session)
        if kind in ("stt", "tts"):
            return tester.test_speech(url, kind, self._session)
        return {"ok": False, "message": "Pick one of model, stt or tts."}

    # -- applying a mode ---------------------------------------------------------------------------------------------------
    def apply(self, mode: str, body: dict[str, Any]) -> dict[str, Any]:
        was_hosted = brain_route.read(self.config_path) == "hosted"
        leave = {"note": brain_route.LEAVE_NOTE} if was_hosted else {}
        try:
            if mode == "hosted":
                if not brain_route.HOSTED_PROVEN:
                    return {"ok": False, "error": "The hosted route is planned, not ready: it needs a test build that shows M5Stack/Xiaozhi's server accepts this firmware. Pick Custom for now."}
                modes.set_values(self.config_path, "", {"brain_route": "hosted"})
                return {"ok": True, "message": "Saved. Your voice now goes to M5Stack/Xiaozhi's servers, outside your home."}
            if mode == "home":
                modes.apply_home(self.config_path, str(body.get("url", "")))
                modes.set_values(self.config_path, "", {"brain_route": "custom"})
                self._leave_hosted_units(was_hosted)
                return {"ok": True, "message": "Saved. The host now uses MaiPai Home. Restart the host, then pair the robot with Home.", **leave}
            if mode == "own":
                modes.apply_own(self.config_path, str(body.get("llm_url", "")), str(body.get("model", "")), str(body.get("stt_url", "")), str(body.get("tts_url", "")), str(body.get("api_key_env", "")))
                modes.set_values(self.config_path, "", {"brain_route": "custom"})
                self._leave_hosted_units(was_hosted)
                return {"ok": True, "message": "Saved. The host now uses your own stack. Restart the host to use it.", **leave}
        except ValueError as error:
            return {"ok": False, "error": str(error)}
        return {"ok": False, "error": "Pick hosted, home or own. The local stack is installed with the Install button."}

    def _leave_hosted_units(self, was_hosted: bool) -> None:
        """Only after the new setting is saved: each unit erases its vendor link and restarts."""
        if was_hosted and self.on_leave_hosted is not None:
            try:
                self.on_leave_hosted()
            except Exception:
                pass  # the saved route already changed; the unit keeps its link until asked again

    # -- the local stack ---------------------------------------------------------------------------------------------------
    def install(self, choice: str) -> dict[str, Any]:
        return self.installer.start(choice)

    def _installed(self, choice: str) -> None:
        modes.apply_local(self.config_path, choice, self.installer.paths(choice))

    def _test_turn(self, folder: Path, choice: str) -> dict[str, Any]:
        paths = self.installer.paths(choice)
        result: dict[str, Any] = {}
        try:
            self.llama.start(paths["server"], paths["model"])
            base = f"http://127.0.0.1:{catalog.LLAMA_PORT}"
            if not runner.wait_until_up(base):
                raise RuntimeError("The local model server did not start in time. Press Install to try again, or pick the small model.")
            result.update(self._timer(base, catalog.MODEL_NAMES[choice]))
        finally:
            pass
        result.update(runner.time_speech(paths))
        return result

    @staticmethod
    def _measure(base: str, model: str) -> dict[str, Any]:
        return runner.time_one_turn(base, model)

    def remove(self) -> dict[str, Any]:
        self.llama.stop()
        result = self.installer.remove()
        if self.config_path.exists():
            modes.clear_local(self.config_path)
        return result

    def start_if_enabled(self) -> bool:
        """At host start: run the model server when the local stack is the brain. Never raises."""
        try:
            raw = tomllib.loads(self.config_path.read_text(encoding="utf-8")) if self.config_path.exists() else {}
            local = raw.get("local_stack", {})
            if not local.get("enabled") or not self.installer.installed():
                return False
            paths = self.installer.paths(local.get("choice", "small"))
            self.llama.start(paths["server"], paths["model"])
            return True
        except Exception:
            return False
