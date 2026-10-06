#!/usr/bin/env python3
"""Fetch the pinned Mesa source for the desktop OpenGL/Metal backend."""
from pathlib import Path
import hashlib
import tarfile
import urllib.request

VERSION = '26.2.4'
SHA256 = 'bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9'
root = Path(__file__).resolve().parents[2]
base = root / 'research' / 'opengl-ios'
base.mkdir(parents=True, exist_ok=True)
archive = base / f'mesa-{VERSION}.tar.xz'
if not archive.exists():
    urllib.request.urlretrieve(f'https://archive.mesa3d.org/mesa-{VERSION}.tar.xz', archive)
assert hashlib.sha256(archive.read_bytes()).hexdigest() == SHA256, 'Mesa source checksum mismatch'
source = base / f'mesa-{VERSION}'
if not source.exists():
    with tarfile.open(archive) as tar:
        tar.extractall(base, filter='data')
print(source)
