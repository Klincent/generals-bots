#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_core.cpp -o test_core
./test_core

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_agent.cpp -o test_agent
./test_agent

g++ -O2 -std=c++17 -Wall -Wextra -Wpedantic test_search_refactor.cpp -o test_search_refactor
./test_search_refactor
