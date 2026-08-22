#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
g++ -O2 -DNDEBUG -std=c++17 -Wall -Wextra -Wpedantic -o agent main.cpp
