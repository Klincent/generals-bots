#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! grep -q 'muster_threshold_' main.cpp; then
  python3 apply_picker_v9.py
fi
python3 apply_picker_v9_priority.py
g++ -O2 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic -o agent main.cpp
