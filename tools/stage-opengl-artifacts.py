#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Stage pinned source-built desktop GL components; no device acceptance claim."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def command(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()

def retrieve(run_id, artifact, owned):
    run = json.loads(command('gh', 'api', f'repos/{ARGS.repository}/actions/runs/{run_id}'))
    assert run['status'] == 'completed' and run['conclusion'] == 'success', run
    commit = run['head_sha']
    subprocess.run(['git', 'fetch', '--depth', '1', 'origin', commit], cwd=ROOT, check=True)
    assert not command('git', 'diff', '--name-only', commit, 'HEAD', '--', *owned), 'component source changed'
    current_wine = command('git', 'ls-tree', 'HEAD', 'wine').split()[2]
    assert command('git', 'ls-tree', commit, 'wine').split()[2] == current_wine, 'Wine source pin changed'
    out = ROOT / 'build/ci-artifacts' / f'opengl-stage-{run_id}'
    assert not out.exists(), 'artifact staging directory already exists'
    subprocess.run(['gh', 'run', 'download', run_id, '-R', ARGS.repository,
                    '-n', artifact, '-D', str(out)], cwd=ROOT, check=True)
    return out, {'run': run_id, 'source': commit, 'wine_pin': current_wine}

def unique(root, name, contains=None):
    paths = [p for p in root.rglob(name) if contains is None or contains in p.parts]
    assert len(paths) == 1, paths
    return paths[0]

def copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == expected
    hashes[str(destination.relative_to(ROOT))] = expected

parser = argparse.ArgumentParser()
parser.add_argument('--native-run', required=True)
parser.add_argument('--windows-run', required=True)
parser.add_argument('--repository', default='llucasandersen/Madeira')
ARGS = parser.parse_args()
native, native_info = retrieve(ARGS.native_run, 'opengl-ios-backend-results', [
    'build/opengl-ios/fetch-mesa.py', 'build/opengl-ios/patch-device.py',
    'build/opengl-ios/build-backend.sh', 'build/opengl-ios/build-loader.sh',
    'build/opengl-ios/check-loader.py'])
windows, windows_info = retrieve(ARGS.windows_run, 'opengl-windows-results', [
    'build/opengl-ios/fetch-mesa.py', 'build/opengl-ios/build-windows.sh',
    'build/opengl-ios/patch-wgl-diagnostics.py'])
hashes = {}
for name in ['vulkan-1.dll', 'winevulkan.dll', 'opengl32.dll', 'libgallium_wgl.dll']:
    copy(unique(windows, name), ROOT / 'build/ci-output/opengl-package/x86_64-opengl' / name)
for name in ['libvulkan.1.dylib', 'libvulkan_kosmickrisp.dylib']:
    copy(unique(native, name, 'ios'), ROOT / 'build/ci-output/opengl-package/Frameworks' / name)
manifest = ROOT / 'build/ci-output/opengl-package/Frameworks/madeira-vulkan.json'
manifest.write_text(json.dumps({'file_format_version': '1.0.0', 'ICD': {
    'library_path': './libvulkan_kosmickrisp.dylib', 'api_version': '1.3.0'}}, indent=2) + '\n')
hashes[str(manifest.relative_to(ROOT))] = hashlib.sha256(manifest.read_bytes()).hexdigest()
legal = ROOT / 'build/ci-output/opengl-package/legal'
legal.mkdir(parents=True, exist_ok=True)
mesa = Path(command(sys.executable, 'build/opengl-ios/fetch-mesa.py'))
for source in (mesa / 'licenses').rglob('*'):
    if source.is_file():
        copy(source, legal / ('Mesa-' + '-'.join(source.relative_to(mesa / 'licenses').parts) + '.txt'))
copy(mesa / 'docs/license.rst', legal / 'Mesa-license.rst')
for repository, commit, name in [
    ('Vulkan-Loader', 'f703f919c30c5b67958d35d40a4297cb3823ed78', 'LICENSE.txt'),
    ('Vulkan-Headers', '9a0f3099c8a9607a7c0f3127d8abfdc19a93e8c5', 'LICENSE.md')]:
    url = f'https://raw.githubusercontent.com/KhronosGroup/{repository}/{commit}/{name}'
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    destination = legal / (repository + '-LICENSE.txt')
    destination.write_bytes(data)
    hashes[str(destination.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
report = {'native': native_info, 'windows': windows_info,
          'mesa_version': '26.2.4',
          'mesa_archive_sha256': 'bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9',
          'vulkan_loader_commit': 'f703f919c30c5b67958d35d40a4297cb3823ed78',
          'vulkan_headers_commit': '9a0f3099c8a9607a7c0f3127d8abfdc19a93e8c5',
          'staged_sha256': hashes,
          'acceptance': 'source/build/package checks only; iPhone OpenGL features and gameplay pending'}
(ROOT / 'build/ci-output/opengl-staging.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
