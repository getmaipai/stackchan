#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
printf '%s\n' "$ROOT/host/spec-vendor/spec"
