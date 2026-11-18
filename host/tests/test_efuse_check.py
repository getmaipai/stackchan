"""Owner decision 14 (2026-11-18): nothing burns an eFuse. scripts/efuse-check.py must pass on the repository and must catch each way to burn one."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("efuse_check", ROOT / "scripts" / "efuse-check.py")
check = importlib.util.module_from_spec(spec)
sys.modules["efuse_check"] = check
spec.loader.exec_module(check)


def test_the_repository_burns_no_efuse() -> None:
    assert check.scan_repo() == []


def test_a_config_that_burns_an_efuse_is_found() -> None:
    for line in ("CONFIG_SECURE_BOOT=y", "CONFIG_SECURE_FLASH_ENC_ENABLED=y", "CONFIG_NVS_ENCRYPTION=y", "CONFIG_NVS_SEC_KEY_PROTECT_USING_HMAC=y", "CONFIG_FLASH_ENCRYPTION_ENABLED=y"):
        assert check.scan_text("x", line, [(check.CONFIG, "c")]), line
    # capability flags of the chip are not a switch
    assert not check.scan_text("x", "CONFIG_SECURE_BOOT_V2_RSA_SUPPORTED=y\nCONFIG_SECURE_BOOT_V2_PREFERRED=y\n# CONFIG_SECURE_BOOT is not set", [(check.CONFIG, "c")])


def test_a_call_or_a_tool_that_burns_an_efuse_is_found() -> None:
    for line in ("+    esp_efuse_write_field_bit(ESP_EFUSE_X);", "+    esp_flash_encryption_enable();", "+  esp_secure_boot_permanently_enable();", "+ esp_efuse_batch_write_commit();"):
        assert check.scan_text("p", line, [(check.CALL, "c")], only_added=True), line
    for line in ("espefuse.py burn_key BLOCK_KEY0 key.bin", "python -m espefuse burn_efuse X", "espsecure.py generate_flash_encryption_key k.bin"):
        assert check.scan_text("s", line, [(check.TOOL, "t")]), line
    # a removed line of a patch is not an addition
    assert not check.scan_text("p", "-    esp_efuse_write_field_bit(X);", [(check.CALL, "c")], only_added=True)
