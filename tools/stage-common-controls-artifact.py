#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stage pinned Wine v6 controls from the authenticated graphics workflow."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
artifact = Path(sys.argv[1])
run = json.loads((root / 'build/ci-artifacts/dxmt-run.json').read_text())
assert run['status'] == 'completed' and run['conclusion'] == 'success'
assert (artifact / 'madeira-commit.txt').read_text().strip() == run['head_sha']
wine = subprocess.check_output(['git', '-C', str(root / 'wine'), 'rev-parse', 'HEAD'], text=True).strip()
assert (artifact / 'wine-commit.txt').read_text().strip() == wine
digest, name = (artifact / 'module-sha256.txt').read_text().strip().split()
assert name == 'comctl32_v6.dll'
source = artifact / 'modules' / name
assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
metadata = json.loads((artifact / 'pe-metadata.jsonl').read_text())
assert metadata['machine'] == '0xa641' and metadata['sha256'] == digest
shutil.copyfile(source, root / 'app/Madeira/arm64ec-windows' / name)
report = {'run_id': run['id'], 'madeira_commit': run['head_sha'], 'wine_commit': wine,
          'staged_sha256': {name: digest}}
(root / 'build/ci-output').mkdir(exist_ok=True)
(root / 'build/ci-output/common-controls-staging.json').write_text(json.dumps(report, indent=2) + '\n')
print('Verified and staged ARM64EC common controls', run['id'])
