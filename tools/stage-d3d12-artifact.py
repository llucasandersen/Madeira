#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stage matching source-built native D3D12 DLLs from an authenticated CI run."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
artifact = Path(sys.argv[1])
run = json.loads((root / 'build/ci-artifacts/dxmt-run.json').read_text())
assert (artifact / 'madeira-commit.txt').read_text().strip() == run['head_sha']
assert run['conclusion'] == 'success'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
source_hash, source_path = (artifact / 'source-sha256.txt').read_text().strip().split(maxsplit=1)
assert source_path == 'madeira-d3d12/src/pe/madeira_d3d12.c'
assert sha(root / source_path) == source_hash, 'D3D12 artifact uses different renderer source'
hashes = dict((name.lstrip('*'), digest) for digest, name in
              (line.split(maxsplit=1) for line in (artifact / 'module-sha256.txt').read_text().splitlines()))
names = ('madeira_d3d12.dll', 'd3d12.dll', 'd3d12core.dll')
for name in names:
    assert sha(artifact / 'modules' / name) == hashes[name], name
assert hashes['madeira_d3d12.dll'] == hashes['d3d12.dll']
for name in names:
    shutil.copyfile(artifact / 'modules' / name, root / 'app/Madeira/arm64ec-windows' / name)
report = {'run_id': run['id'], 'madeira_commit': run['head_sha'],
          'source_sha256': source_hash, 'staged_sha256': {n: hashes[n] for n in names}}
(root / 'build/ci-output').mkdir(exist_ok=True)
(root / 'build/ci-output/d3d12-staging.json').write_text(json.dumps(report, indent=2) + '\n')
print('Verified and staged D3D12 source build', run['id'])
