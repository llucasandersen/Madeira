#!/usr/bin/env python3
"""Exercise production upload backing selection, alignment and failure fallback."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()
helpers = source[source.index('static int mad_upload_swap_on('):source.index('static int mad_pso_lazy_on(')]
at = source.index('if (!r->buffer && mad_upload_swap_eligible(')
end = source.index('{', at)
depth = 1
cursor = end + 1
while depth:
    depth += (source[cursor] == '{') - (source[cursor] == '}')
    cursor += 1
allocation = source[at:cursor]
prelude = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned UINT; typedef uint64_t UINT64; typedef int64_t LONG64;
typedef int32_t LONG; typedef size_t SIZE_T;
enum { D3D12_HEAP_TYPE_DEFAULT=1, D3D12_HEAP_TYPE_UPLOAD=2, D3D12_HEAP_TYPE_READBACK=3 };
#define MEM_COMMIT 1
#define MEM_RESERVE 2
#define MEM_RELEASE 4
#define PAGE_READWRITE 1
static LONG64 threshold; static int enabled, va_fail, metal_fail, va_calls, metal_calls, frees;
static volatile LONG64 g_upload_swap_bytes; static volatile LONG g_upload_swap_n;
static LONG64 mad_cfg_int_pe(const char *key, LONG64 def) {
    return !strcmp(key,"upload-swap") ? enabled : threshold == -999 ? def : threshold;
}
static void d3d12_log(const char *fmt, ...) { (void)fmt; }
static void *VirtualAlloc(void *p, SIZE_T n, int flags, int prot) {
    (void)p; (void)flags; (void)prot; va_calls++; assert(n && !(n & 0xffff));
    return va_fail ? NULL : (void *)(uintptr_t)0x10000;
}
static void VirtualFree(void *p, SIZE_T n, int flags) { (void)n; (void)flags; assert(p); frees++; }
static void InterlockedExchangeAdd64(volatile LONG64 *p, LONG64 n) { *p += n; }
static LONG InterlockedIncrement(volatile LONG *p) { return ++*p; }
struct fixture_info { UINT64 length, gpu_address; struct { void *ptr; } memory; };
static uintptr_t MTLDevice_newBuffer(uintptr_t dev, struct fixture_info *info) {
    (void)dev; metal_calls++; assert(info->memory.ptr && !(info->length & 0xffff));
    info->gpu_address=0x50000; return metal_fail ? 0 : 123;
}
'''
fixture = r'''
int main(int argc, char **argv) {
    assert(argc==8); threshold=atoll(argv[1]); enabled=atoi(argv[2]);
    struct fixture_info info={.length=strtoull(argv[3],NULL,10)};
    UINT heap_type=atoi(argv[4]); va_fail=atoi(argv[5]); metal_fail=atoi(argv[6]);
    struct { uintptr_t buffer; void *own_mem; } resource={.buffer=atoi(argv[7])}, *r=&resource;
    struct { uintptr_t mtl_device; } device={0}, *d=&device;
    ALLOCATION
    printf("%d %d %d %llu %llu %d %d\n",va_calls,metal_calls,frees,
           (unsigned long long)info.length,(unsigned long long)info.gpu_address,
           r->own_mem!=NULL,(int)g_upload_swap_n);
    return 0;
}
'''.replace('ALLOCATION', allocation)
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / 'backing.c'; exe = Path(tmp) / 'backing'
    c.write_text(prelude + helpers + fixture)
    subprocess.run(['cc', '-O1', '-Wall', '-Werror', str(c), '-o', str(exe)], check=True)
    def case(floor, on, length, heap=2, va_fail=0, metal_fail=0, existing=0, eligible=False):
        values = [floor, on, length, heap, va_fail, metal_fail, existing]
        result = list(map(int, subprocess.check_output([str(exe)] + list(map(str, values)), text=True).split()))
        va = int(eligible and not existing); metal = int(va and not va_fail)
        success = bool(metal and not metal_fail)
        expected = [va, metal, int(metal and metal_fail),
                    ((length + 65535) & ~65535) if success else length,
                    0x50000 if success else 0, int(success), int(success)]
        assert result == expected, (values, result, expected)
    case(-999, 1, 8*1024*1024, eligible=True)
    case(-999, 1, 8*1024*1024-1)
    case(256, 1, 256*1024, eligible=True)
    case(256, 1, 256*1024-1)
    case(256, 1, 256*1024+1, heap=3, eligible=True)
    case(256, 1, 256*1024, heap=1)
    case(256, 0, 8*1024*1024)
    case(256, 1, 256*1024, va_fail=1, eligible=True)
    case(256, 1, 256*1024+1, metal_fail=1, eligible=True)
    case(256, 1, 256*1024, existing=123, eligible=True)
    for invalid in (0, -1, 63, 1048577):
        case(invalid, 1, 256*1024)
    case(64, 1, 64*1024, eligible=True)
print('PASS: production CPU-visible backing floor, heap selection, opt-out, alignment and allocation failures')
