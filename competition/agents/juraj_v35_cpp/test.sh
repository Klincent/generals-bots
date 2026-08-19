#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! grep -q 'muster_threshold_' main.cpp; then
  python3 apply_picker_v9.py
fi
python3 apply_picker_v9_priority.py

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_core.cpp -o test_core
./test_core

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_agent.cpp -o test_agent
./test_agent

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_picker.cpp -o test_picker
./test_picker

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_picker_economics.cpp -o test_picker_economics
./test_picker_economics

bash build.sh
python3 test_protocol.py
