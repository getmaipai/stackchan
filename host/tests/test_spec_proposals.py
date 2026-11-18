"""The shared-spec proposals (docs/plan/spec-proposals): fixtures behave, and the host's own code passes them."""

import json
import re
from pathlib import Path

import pytest

from tests.schema_mini import errors

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "docs" / "plan" / "spec-proposals"
NAMES = ("movement-limiter-state", "memory-admission", "brain-capabilities", "indicator-row", "memory-governor", "robot-description")


def _schema(name):
    return json.loads((DIR / f"{name}.schema.json").read_text())


@pytest.mark.parametrize("name", NAMES)
def test_valid_fixtures_pass_and_invalid_fixtures_fail(name):
    schema = _schema(name)
    valid = sorted((DIR / "fixtures").glob(f"{name}.valid.*.json"))
    invalid = sorted((DIR / "fixtures").glob(f"{name}.invalid.*.json"))
    assert valid and invalid
    for path in valid:
        assert errors(schema, json.loads(path.read_text())) == [], path.name
    for path in invalid:
        assert errors(schema, json.loads(path.read_text())) != [], path.name


def test_the_hosts_movement_limiter_states_are_the_enum():
    from maipai_body.bodies.stackchan import motion_limit

    assert set(motion_limit.STATE_WORDS_EN) == set(_schema("movement-limiter-state")["properties"]["state"]["enum"])
    for state, words in motion_limit.STATE_WORDS_EN.items():
        record = {"state": state, "usb": state == "usb_limited", "battery_percent": None, "reason": words}
        assert errors(_schema("movement-limiter-state"), record) == [], state


def test_the_memory_admission_record_matches_the_notes_package():
    from maipai_packages.memory_notes import AdmissionError, check_note
    from maipai_packages.memory_notes import admission

    record = json.loads((DIR / "fixtures" / "memory-admission.valid.example.json").read_text())
    assert record["max_note_chars"] == admission.MAX_NOTE_CHARS
    assert record["max_notes_per_person"] == admission.MAX_NOTES_PER_PERSON
    for text in record["accepted_examples"]:
        check_note(text)
    for text in record["refused_examples"]:
        with pytest.raises(AdmissionError):
            check_note(text)


def test_the_own_llm_brain_capabilities_validate():
    from maipai_body.brain.interface import BrainFeature
    from maipai_body.brain.own_llm import OwnLLMBrain
    from maipai_body.config import LlmConfig

    brain = OwnLLMBrain(LlmConfig(url="http://192.0.2.5:8080", model="m", stt_url="http://192.0.2.5:8001"))
    record = {"features": sorted(f.value for f in brain.capabilities())}
    assert errors(_schema("brain-capabilities"), record) == []
    assert set(_schema("brain-capabilities")["properties"]["features"]["items"]["enum"]) == {f.value for f in BrainFeature}


def test_the_approved_ring_table_validates_and_matches_the_hosts_keys():
    from maipai_body.indicator.looks import LookKey

    text = (ROOT / "host" / "spec-vendor" / "indicator-standard.md").read_text()
    rows = re.findall(r"^\| `(\w+)` \| ([^|]+) \| (\w+) \| (\w+) \| ([\d.]+)s \| ([\d.]+) \|", text, re.M)
    assert rows
    for key, meaning, color, style, period, brightness in rows:
        record = {"key": key, "meaning": meaning.strip(), "color": color, "style": style, "period_s": float(period), "brightness": float(brightness)}
        assert errors(_schema("indicator-row"), record) == [], key
    assert {r[0] for r in rows} == {k.value for k in LookKey}


def test_the_memory_governor_floors_equal_the_gate_scripts():
    import importlib.util

    record = json.loads((DIR / "fixtures" / "memory-governor.valid.example.json").read_text())
    spec = importlib.util.spec_from_file_location("fw_stress", ROOT / "scripts" / "fw-stress.py")
    stress = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stress)
    ram = record["budgets"]["internal_ram"]
    assert ram["free_median_min_bytes"] == stress.FLOORS["internal_free_steady"]
    assert ram["free_lowest_min_bytes"] == stress.FLOORS["internal_min"]
    assert ram["largest_block_median_min_bytes"] == stress.FLOORS["int_big_steady"]
    assert ram["largest_block_lowest_min_bytes"] == stress.FLOORS["int_big_min"]
    assert ram["stack_margin_min_bytes"] == stress.FLOORS["stack_margin"]
    spec = importlib.util.spec_from_file_location("release_report", ROOT / "scripts" / "release-report.py")
    report = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(report)
    assert record["budgets"]["flash_slot"]["free_min_percent"] == round(report.FREE_RULE * 100)
    assert (DIR / "memory-governor.md").read_text().count("40,000") >= 1


def test_the_stackchan_robot_description_validates_and_marks_every_parameter():
    desc = json.loads((ROOT / "scripts" / "virtual-unit" / "physics" / "robots" / "stackchan.robot.json").read_text())
    assert errors(_schema("robot-description"), desc) == []
    assert all(entry["src"] in ("measured", "assumed") and entry["note"] for entry in desc["params"].values())
