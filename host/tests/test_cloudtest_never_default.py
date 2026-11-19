"""The cloud brain test image is never the default and never in a release: no default config turns it on, the release script does not build it, and no other kind carries the vendor address."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENDOR = "tenclass"


def test_only_the_cloudtest_overlay_enables_it():
    for path in (ROOT / "firmware" / "configs").glob("sdkconfig.*.defaults"):
        text = path.read_text()
        if path.name == "sdkconfig.cloudtest.defaults":
            assert "CONFIG_MAIPAI_CLOUDTEST=y" in text and "CONFIG_STACKCHAN_OTA_CHECK=y" in text
        else:
            assert "MAIPAI_CLOUDTEST=y" not in text and VENDOR not in text and "STACKCHAN_OTA_CHECK=y" not in text, path.name


def test_the_release_script_never_builds_it():
    for name in ("release.sh", "build-stackchan-firmware-asset.sh"):
        assert "cloudtest" not in (ROOT / "scripts" / name).read_text(), name


def test_the_kconfig_default_is_off():
    patch = (ROOT / "firmware" / "patches" / "SF96-cloud-brain-test-image-kind.patch").read_text()
    block = patch.split("config MAIPAI_CLOUDTEST", 1)[1].split("config STACKCHAN_OTA_CHECK", 1)[0]
    assert "default n" in block


def test_the_vendor_address_is_only_in_the_cloudtest_overlay():
    # patch 155 names it where it removed the default; no patch may ADD it
    for p in (ROOT / "firmware" / "patches").glob("*.patch"):
        added = [l for l in p.read_text(errors="ignore").splitlines() if l.startswith("+") and not l.startswith("+++") and VENDOR in l]
        assert not added, p.name
    hits = [p for p in (ROOT / "firmware").rglob("*") if p.is_file() and p.suffix in {".defaults", ".h", ".cc", ".cpp"} and VENDOR in p.read_text(errors="ignore")]
    assert {p.name for p in hits} <= {"sdkconfig.cloudtest.defaults"}, hits


def test_no_kind_sets_a_stackchan_server_url():
    """The avatar WebSocket, the app list and the account calls have no address in any image kind (the raw-IP address exists only in the official image)."""
    for path in (ROOT / "firmware" / "configs").glob("sdkconfig.*.defaults"):
        assert "STACKCHAN_SERVER_URL" not in path.read_text(), path.name
    for p in (ROOT / "firmware" / "patches").glob("*.patch"):
        added = [l for l in p.read_text(errors="ignore").splitlines() if l.startswith("+") and not l.startswith("+++") and "47.113" in l]
        assert not added, p.name
