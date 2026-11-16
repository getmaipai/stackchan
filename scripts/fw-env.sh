#!/usr/bin/env bash
# Intent: one place that sets up ESP-IDF 6.1 for firmware builds. Usage: `source scripts/fw-env.sh`, then `idf.py ...`.
export IDF_TOOLS_PATH="${IDF_TOOLS_PATH:-$HOME/.espressif}"
export IDF_PATH="${IDF_PATH:-$HOME/esp/esp-idf-6.1.1}"
# shellcheck disable=SC1091
. "$IDF_PATH/export.sh" >/dev/null 2>&1 || { echo "ESP-IDF not found at $IDF_PATH; run ./install.sh esp32s3 there." >&2; return 1; }
# The firmware build refuses an image that contains a key (patch 156); this is the checker it runs.
MAIPAI_KEY_CHECK="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/check-no-keys.py"
export MAIPAI_KEY_CHECK
# Travel with the private network (patch TN01): the downloaded client, when bash scripts/fw-tailnet.sh has run.
if [ -z "${MAIPAI_MICROLINK_DIR:-}" ] && [ -d "${MAIPAI_DEPS:-$HOME/esp/maipai-deps}/microlink/components" ]; then
    export MAIPAI_MICROLINK_DIR="${MAIPAI_DEPS:-$HOME/esp/maipai-deps}/microlink"
fi
# Offline phrases (patch V02): the sixteen spoken clips the build embeds in the app image.
if [ -z "${MAIPAI_PHRASES_DIR:-}" ]; then
    _maipai_repo="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
    if [ -f "$_maipai_repo/host/maipai_body/bodies/stackchan/firmware/assets/phrases/ph_no_wifi_1.ogg" ]; then
        export MAIPAI_PHRASES_DIR="$_maipai_repo/host/maipai_body/bodies/stackchan/firmware/assets/phrases"
    fi
    unset _maipai_repo
fi
