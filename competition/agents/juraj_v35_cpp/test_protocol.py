#!/usr/bin/env python3
"""Exercise one real protocol observation/action exchange with the built agent."""

import subprocess
from pathlib import Path


root = Path(__file__).resolve().parent
size = 21
cells = size * size
general = 10 * size + 10

types = [1] * cells
owners = [0] * cells
armies = [0] * cells
types[general] = 4
owners[general] = 1
armies[general] = 20

observation = "\n".join(
    [
        f"0 {size} {size}",
        "0 1 20 0 0",
        " ".join(map(str, types)),
        " ".join(map(str, owners)),
        " ".join(map(str, armies)),
        "",
    ]
)
result = subprocess.run(
    [str(root / "agent")],
    input=observation,
    text=True,
    capture_output=True,
    timeout=10,
    check=False,
)
assert result.returncode == 0, result.stderr
lines = result.stdout.splitlines()
assert len(lines) == 1, result.stdout
action = [int(value) for value in lines[0].split()]
assert len(action) == 5, lines[0]
assert action[0] in (0, 1, 2), lines[0]
print("v36 real protocol observation/action cycle passed")
