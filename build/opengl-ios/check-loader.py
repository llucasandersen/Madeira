#!/usr/bin/env python3
"""Check real loader/ICD dispatch and Metal surface availability on the Mac host.

This is not an iPhone GPU or desktop OpenGL conformance test.
"""
import ctypes as c
import json
import os
from pathlib import Path
import sys

loader_path, driver_path = map(lambda value: Path(value).resolve(), sys.argv[1:])
manifest = loader_path.parent / 'madeira-test-icd.json'
manifest.write_text(json.dumps({'file_format_version': '1.0.0', 'ICD': {
    'library_path': str(driver_path), 'api_version': '1.3.328'}}))
os.environ['VK_DRIVER_FILES'] = str(manifest)
loader = c.CDLL(str(loader_path))

class Extension(c.Structure):
    _fields_ = [('name', c.c_char * 256), ('version', c.c_uint32)]

enumerate_extensions = loader.vkEnumerateInstanceExtensionProperties
enumerate_extensions.argtypes = [c.c_char_p, c.POINTER(c.c_uint32), c.POINTER(Extension)]
enumerate_extensions.restype = c.c_int32
count = c.c_uint32()
assert enumerate_extensions(None, c.byref(count), None) == 0
entries = (Extension * count.value)()
assert enumerate_extensions(None, c.byref(count), entries) == 0
names = sorted(entry.name.decode() for entry in entries[:count.value])
assert 'VK_EXT_metal_surface' in names, names
assert 'VK_KHR_surface' in names, names
print(json.dumps({'loader': str(loader_path), 'icd': str(driver_path),
                  'instance_extensions': names,
                  'scope': 'Mac host loader dispatch; iPhone gameplay remains untested'}, indent=2))
print('PASS: pinned ICD loads through Khronos loader and advertises real Metal surfaces')
