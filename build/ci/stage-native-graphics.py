"""Keep the existing Metal converter SDK independent of the app UI SDK."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if sys.argv[1] == 'record':
    folder = root / 'build/ci-output/native-graphics'
    folder.mkdir(parents=True, exist_ok=True)
    lib = folder / 'libdxmt_combined.a'
    shutil.copyfile(root / 'app/Madeira/libdxmt_combined.a', lib)
    report = dict(source=git('rev-parse', 'HEAD'), dxmt=git('-C', 'dxmt', 'rev-parse', 'HEAD'),
                  run_id=os.environ['GITHUB_RUN_ID'], library_sha256=sha(lib),
                  sdk=subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-version'], text=True).strip())
    (folder / 'native-graphics.json').write_text(json.dumps(report, indent=2)+'\n')
elif sys.argv[1] == 'stage':
    folder = root / 'build/ci-artifacts/native-graphics'
    report = json.loads((folder / 'native-graphics.json').read_text())
    assert report['source'] == git('rev-parse', 'HEAD'), 'graphics source mismatch'
    assert report['dxmt'] == git('-C', 'dxmt', 'rev-parse', 'HEAD'), 'DXMT pin mismatch'
    assert str(report['run_id']) == os.environ['GITHUB_RUN_ID'], 'unexpected graphics artifact run'
    assert report['sdk'].startswith('26.6'), 'unexpected converter SDK'
    assert sha(folder / 'libdxmt_combined.a') == report['library_sha256'], 'graphics archive checksum mismatch'
    shutil.copyfile(folder / 'libdxmt_combined.a', root / 'app/Madeira/libdxmt_combined.a')
    (root / 'build/ci-output/native-graphics-staging.json').write_text(json.dumps(report,indent=2)+'\n')
else:
    raise SystemExit('usage: stage-native-graphics.py record|stage')
