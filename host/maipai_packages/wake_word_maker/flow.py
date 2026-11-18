"""Train, check and install: the steps the settings page walks through, run in the background so the page can show progress."""

from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path

from maipai_packages.wake_word_maker.engine import eval_kws, make_dataset, train_kws
from maipai_packages.wake_word_maker.store import MIN_CLIPS, ClipError, WakeStore


class WakeWordMaker:
    def __init__(self, store: WakeStore, *, background: bool = True, clock=time.time) -> None:
        self.store, self._background, self._clock = store, background, clock
        self._lock = threading.Lock()
        self._status: dict = {"state": "idle", "step": "", "message": "", "result": None}

    # ---- state the page shows ----------------------------------------------------------------------------
    def state(self, word: str = "") -> dict:
        with self._lock:
            status = dict(self._status)
        counts = self.store.counts(word) if word else {"positive": 0, "negative": 0}
        installed = self.installed()
        return {"enabled": True, "need": MIN_CLIPS, "counts": counts, "status": status, "installed": installed, "words": self.store.words()}

    def installed(self) -> dict | None:
        try:
            return json.loads((self.store.folder / "installed.json").read_text())
        except (OSError, ValueError):
            return None

    # ---- train and check ---------------------------------------------------------------------------------
    def train(self, word: str) -> dict:
        counts = self.store.counts(word)
        if counts["positive"] < MIN_CLIPS or counts["negative"] < MIN_CLIPS:
            raise ClipError(f"Record at least {MIN_CLIPS} clips of the word and {MIN_CLIPS} clips of other speech first.")
        with self._lock:
            if self._status["state"] == "running":
                raise ClipError("Training is already running. Wait for it to finish.")
            self._status = {"state": "running", "step": "preparing", "message": "Preparing the recordings.", "result": None}
        if self._background:
            threading.Thread(target=self._run, args=(word,), name="wake-word-train", daemon=True).start()
        else:
            self._run(word)
        return self.state(word)

    def _set(self, **changes) -> None:
        with self._lock:
            self._status.update(changes)

    def _run(self, word: str) -> None:
        try:
            base = self.store.word_dir(word)
            positives, negatives = base / "positive", base / "negative"
            data, model, result = base / "data.npz", base / "model.npz", base / "result.json"
            make_dataset.build(positives, data, negatives, seed=3)
            self._set(step="training", message="Training. This takes a minute.")
            train_kws.train(data, model, export_c=base / "model.h", seed=3)
            self._set(step="checking", message="Checking the model.")
            checked = eval_kws.evaluate(model, negatives, positives)
            result.write_text(json.dumps(checked, sort_keys=True) + "\n")
            self._set(state="done", step="done", message="Done. Look at the numbers, then install it or record more.", result=self._plain(checked))
        except Exception as error:  # the page shows a plain message; the cause stays in the log
            self._set(state="error", step="error", message=f"Training stopped: {error}")

    @staticmethod
    def _plain(checked: dict) -> dict:
        """The check result as plain JSON values (numbers, text and lists of them)."""
        return json.loads(json.dumps(checked, default=float))

    # ---- install -------------------------------------------------------------------------------------------
    def install(self, word: str) -> dict:
        base = self.store.word_dir(word)
        model, result = base / "model.npz", base / "result.json"
        if not model.is_file() or not result.is_file():
            raise ClipError("Train and check the model before you install it.")
        target = self.store.folder / "installed"
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(model, target / f"{word}.npz")
        if (base / "model.h").is_file():
            shutil.copyfile(base / "model.h", target / f"{word}.h")
        record = {"word": word, "installed_at": int(self._clock()), "check": self._plain(json.loads(result.read_text())), "used_by_robot": False}
        (self.store.folder / "installed.json").write_text(json.dumps(record, sort_keys=True) + "\n")
        return record
