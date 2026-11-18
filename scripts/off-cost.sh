#!/usr/bin/env bash
# Intent: prove an optional firmware feature that is switched off costs nothing in the plain image. Reads a built plain image (default: the newest
# ~/esp/stackchan-rebuild/*/firmware/build-plain) and, per feature, counts the symbols and bytes of its code and data and the strings of its tools in the ELF.
# A feature that is off must show 0 symbols and 0 strings (an inline stub leaves no symbol). Usage: bash scripts/off-cost.sh [BUILD_DIR] > docs/dev/off-cost.md
# Placement: host-side development tool; no firmware change. Upstream: none.
set -u
B="${1:-$(ls -dt "$HOME"/esp/stackchan-rebuild/*/firmware/build-plain 2>/dev/null | head -1)}"
ELF="$B/maipai-stackchan.elf"
[ -f "$ELF" ] || { echo "off-cost: no ELF at $ELF. Build one first: bash scripts/fw-build.sh TREE plain" >&2; exit 2; }
NM="$(ls -d "$HOME"/.espressif/tools/xtensa-esp-elf/*/xtensa-esp-elf/bin/xtensa-esp32s3-elf-nm | tail -1)"
SIZE="${NM%nm}size"
SYMS="$(mktemp)"; STR="$(mktemp)"; trap 'rm -f "$SYMS" "$STR"' EXIT
"$NM" -S --size-sort "$ELF" > "$SYMS"
strings -a "$ELF" > "$STR"
echo "# Cost of a switched-off feature in the plain image"
echo
echo "Image: \`$(basename "$(dirname "$(dirname "$B")")")/$(basename "$B")\`, $(stat -f %z "$B/maipai-stackchan.bin" 2>/dev/null || stat -c %s "$B/maipai-stackchan.bin") bytes. Static sizes (\`size\`): $("$SIZE" "$ELF" | tail -1 | awk '{print "text "$1", data "$2", bss "$3}')."
echo
echo "A feature that is off must show 0 symbols, 0 bytes and 0 strings. Made by \`scripts/off-cost.sh\`; re-run it after any change to a switch."
echo
echo "| Feature (switch) | Symbols | Bytes | Strings | Result |"
echo "|---|---|---|---|---|"
row() { # name, symbol regex, string regex
  local n b s r
  n=$(awk '{print $4}' "$SYMS" | grep -Ec "$2" || true)
  b=$(awk -v re="$2" '$4 ~ re {print $2}' "$SYMS" | while read -r h; do echo $((16#$h)); done | awk '{t+=$1} END{print t+0}')
  s=$(grep -Ec "$3" "$STR" || true)
  r="zero cost"; if [ "$n" != 0 ] || [ "$s" != 0 ]; then r="COSTS"; fi
  echo "| $1 | $n | $b | $s | $r |"
}
row "Talking over the robot (CONFIG_MAIPAI_TALK_OVER, microphone slot tools)" 'maipai_mic3|mic3_' 'self\.bench\.mic3|mic3_check'
row "Echo canceller and barge-in (CONFIG_MAIPAI_TALK_OVER_AEC)" 'maipai_barge|mbg_|maipai_aec_trace' 'MaipaiBarge|AEC mic='
row "Encrypted link and pairing (CONFIG_MAIPAI_LINK_PSK)" 'maipai_link_(new_keypair|agree|key|psk|secure)|maipai_linkpsk|maipai_linkpair|mly_|mpx_|maipai_pair' 'self\.link\.pair|mp_link|maipai-stackchan-link'
row "Bench and serial tools (CONFIG_MAIPAI_SERIAL_TOOLS)" 'maipai_bench|g_bench_clip|g_servo_anim|g_servo_update' 'self\.bench\.'
row "Heap trace (CONFIG_HEAP_TRACING_STANDALONE)" 'heap_trace' 'self\.bench\.heap_trace|heap_trace'
