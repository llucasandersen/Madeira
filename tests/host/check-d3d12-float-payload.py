#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise production converter flags and its actual content cache keys."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
src = (root / 'madeira-d3d12/src/unix/madeira_ir_unix.mm').read_text(encoding='utf-8')
start = src.index('static uint32_t mad_ir_compat_flags(void) {')
flags = src[start:src.index('\nextern "C" int madeira_ir_convert_impl', start)]
header = (root / 'madeira-d3d12/third_party/metal-shader-converter/include/metal_irconverter/metal_irconverter.h').read_text()
at = header.index('typedef enum IRCompatibilityFlags')
enums = header[at:header.index('} IRCompatibilityFlags;', at) + len('} IRCompatibilityFlags;')]
code = r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "unix/madeira_dxil_cache.h"
#define IR_VERSION_MAJOR 4
#define IR_VERSION_MINOR 0
#define IR_VERSION_PATCH 1
static int override_sample = -1;
static int madeira_cfg_int(const char *key, int fallback) {
    return !strcmp(key, "msc-sample-nan-zero") && override_sample >= 0 ? override_sample : fallback;
}
'''+enums+'\n'+flags+r'''
int main(int argc, char **argv) {
    if (argc == 2) override_sample = atoi(argv[1]);
    uint32_t f = mad_ir_compat_flags();
    assert(bool(f & IRCompatibilityFlagSampleNanToZero) == (override_sample == 1));
    assert(f & IRCompatibilityFlagDisableNanInfOptimization);
    assert(f & IRCompatibilityFlagBoundsCheck);
    assert(f & IRCompatibilityFlagPositionInvariance);
    assert(f & IRCompatibilityFlagForceTextureArray);
    assert(mad_ir_compat_flags() == f);
    madeira_ir_convert_args a = {};
    mad_dxc_env current = {}; current.compat_flags = f;
    mad_dxc_env changed = current; changed.compat_flags ^= IRCompatibilityFlagSampleNanToZero;
    uint64_t key, check, different_key, different_check;
    mad_dxc_key(&a, &current, &key, &check);
    mad_dxc_key(&a, &changed, &different_key, &different_check);
    assert(key != different_key && check != different_check);
    puts("production flags preserve float payloads by default; explicit workaround and cache separation checked");
}
'''
with tempfile.TemporaryDirectory(prefix='madeira-float-payload-') as temp:
    temp = Path(temp)
    (temp/'test.cpp').write_text(code)
    subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-I', str(root/'madeira-d3d12/src'), str(temp/'test.cpp'), '-o', str(temp/'test')], check=True)
    for args in ([], ['0'], ['1']):
        subprocess.run([str(temp/'test'), *args], check=True)
    subprocess.run(['cc', '-std=c11', '-D_DEFAULT_SOURCE', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-I', str(root/'madeira-d3d12/src'),
                    str(root/'madeira-d3d12/tests/native/dxil_cache_test.c'), '-o', str(temp/'cache')], check=True)
    subprocess.run([str(temp/'cache')], check=True)
print('PASS: host policy and cache tests; actual MSC/phone texture reads require device evidence')
