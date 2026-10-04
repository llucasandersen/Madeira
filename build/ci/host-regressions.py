#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Run the existing host checks independently and retain every result."""
from pathlib import Path
import json
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
out = root / "build/ci-output/host-tests"
out.mkdir(parents=True, exist_ok=True)
results = []
for test in sorted((root / "tests/host").glob("check-*.py")):
    started = time.monotonic()
    log = out / f"{test.stem}.log"
    with log.open("w") as stream:
        try:
            result = subprocess.run([sys.executable, str(test)], cwd=root,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=600)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
            stream.write("\nHost check exceeded 600 seconds.\n")
    elapsed = round(time.monotonic() - started, 2)
    results.append({"test": test.name, "exit_code": code, "seconds": elapsed})
    print(f"{'PASS' if code == 0 else 'FAIL'} {test.name} ({elapsed}s)", flush=True)
    if code:
        print("\n".join(log.read_text(errors="replace").splitlines()[-25:]), flush=True)
(out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
sys.exit(0 if results and all(result["exit_code"] == 0 for result in results) else 1)
