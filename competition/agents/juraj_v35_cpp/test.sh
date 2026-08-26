#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Legacy v3.5 source needs the picker patches. The Evolution4 Turbo template is
# already structurally transformed and must not receive those patches twice.
if grep -q '\[e4_structural\]' main.cpp; then
  echo 'structural runtime detected; skipping legacy picker re-apply'
else
  if ! grep -q 'muster_threshold_' main.cpp; then
    python3 apply_picker_v9.py
  fi
  python3 apply_picker_v9_priority.py
fi

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_core.cpp -o test_core
./test_core

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_agent.cpp -o test_agent
./test_agent

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_picker.cpp -o test_picker
./test_picker

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_picker_economics.cpp -o test_picker_economics
./test_picker_economics

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_muster.cpp -o test_muster
./test_muster

bash build.sh
python3 test_protocol.py
