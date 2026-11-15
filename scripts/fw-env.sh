#!/usr/bin/env bash
# Intent: one place that sets up ESP-IDF 6.1 for firmware builds. Usage: `source scripts/fw-env.sh`, then `idf.py ...`.
export IDF_TOOLS_PATH="${IDF_TOOLS_PATH:-$HOME/.espressif}"
export IDF_PATH="${IDF_PATH:-$HOME/esp/esp-idf-6.1.1}"
# shellcheck disable=SC1091
. "$IDF_PATH/export.sh" >/dev/null 2>&1 || { echo "ESP-IDF not found at $IDF_PATH; run ./install.sh esp32s3 there." >&2; return 1; }
