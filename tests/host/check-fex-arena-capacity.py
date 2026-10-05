#!/usr/bin/env python3
# Copyright (C) 2026 125hz
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Exercise the production arena reservation with a bounded Mach map fixture.

The fixture models the phone's 63GB ceiling and CoreAnimation range. It checks
actual reservation, relocation, registration and publication, including smaller
maps, explicit caps and failures. It does not emulate game or FEX execution.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text(encoding='utf-8')
start = source.index('void ios_reserve_fex_arena(void)\n{')
production = source[start:source.index('\n}', start) + 2]
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
typedef uintptr_t ULONG_PTR;
typedef size_t SIZE_T;
typedef int NTSTATUS, kern_return_t, task_t;
typedef int *task_info_t;
typedef unsigned mach_msg_type_number_t;
typedef uint64_t mach_vm_address_t, mach_vm_size_t;
typedef struct { uint64_t max_address; } task_vm_info_data_t;
typedef struct { void *LowestStartingAddress, *HighestEndingAddress; size_t Alignment; } MEM_ADDRESS_REQUIREMENTS;
typedef struct { unsigned Type; void *Pointer; } MEM_EXTENDED_PARAMETER;
#define KERN_SUCCESS 0
#define KERN_FAILURE 1
#define TASK_VM_INFO 22
#define TASK_VM_INFO_COUNT 1
#define VM_FLAGS_ANYWHERE 1
#define VM_FLAGS_FIXED 0
#define MEMORY_OBJECT_NULL 0
#define VM_PROT_ALL 7
#define VM_INHERIT_COPY 1
#define MEM_RESERVE 0x2000
#define MEM_RESERVE_PLACEHOLDER 0x40000
#define PAGE_NOACCESS 1
#define MemExtendedParameterAddressRequirements 1
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define ERR(...) fprintf(stderr, __VA_ARGS__)
static unsigned long long ios_layerkit_lo = 0x12c400000ull, ios_layerkit_hi = 0xb30000000ull;
static uint64_t ceiling = 0xfc0000000ull, capacity = 12ull << 30;
static ULONG_PTR ios_fex_arena_base_unix, ios_fex_arena_end_unix;
static uint64_t held_base, held_size;
static long long cap_mb;
static int registration_fails, successful_maps, releases, registrations;
static task_t mach_task_self(void) { return 1; }
static kern_return_t task_info(task_t t, int f, task_info_t out, mach_msg_type_number_t *n)
{ (void)t; (void)f; (void)n; ((task_vm_info_data_t *)out)->max_address = ceiling; return 0; }
static long long madeira_cfg_int(const char *key, long long fallback)
{ assert(!strcmp(key, "arena-mb")); (void)fallback; return cap_mb; }
static void *NtCurrentProcess(void) { return (void *)(uintptr_t)-1; }
static NTSTATUS NtAllocateVirtualMemoryEx(void *p, void **b, SIZE_T *s,
    unsigned t, unsigned prot, MEM_EXTENDED_PARAMETER *a, unsigned n)
{ (void)p; (void)b; (void)s; (void)t; (void)prot; (void)a; (void)n; return 1; }
static kern_return_t mach_vm_map(task_t t, mach_vm_address_t *addr, mach_vm_size_t size,
    uint64_t mask, int flags, int object, uint64_t offset, int copy, int prot, int maxprot, int inherit)
{
    (void)t; (void)object; (void)offset; (void)copy; (void)maxprot; (void)inherit;
    assert(mask == 0xffff && prot == PROT_NONE && !held_size);
    if (size > capacity) return KERN_FAILURE;
    if (flags == VM_FLAGS_ANYWHERE) {
        if (*addr >= ceiling) return KERN_FAILURE;
        *addr = 0x800000000ull; /* kernel returns a real mapping inside LayerKit's range */
    }
    if (*addr > ceiling || size > ceiling - *addr) return KERN_FAILURE;
    held_base = *addr; held_size = size; ++successful_maps;
    return KERN_SUCCESS;
}
static kern_return_t mach_vm_deallocate(task_t t, mach_vm_address_t addr, mach_vm_size_t size)
{ (void)t; assert(addr == held_base && size == held_size); held_size = 0; ++releases; return 0; }
static int mmap_add_fex_reserved_area(void *base, SIZE_T size)
{ assert((uintptr_t)base == held_base && size == held_size); ++registrations; return !registration_fails; }
''' + production + r'''
int main(int argc, char **argv)
{
    assert(argc == 2);
    if (!strcmp(argv[1], "fallback")) capacity = 8ull << 30;
    else if (!strcmp(argv[1], "cap")) cap_mb = 4096;
    else if (!strcmp(argv[1], "failure")) registration_fails = 1;
    else if (!strcmp(argv[1], "small")) { ceiling = 0xa00000000ull; capacity = 4ull << 30; }
    else if (!strcmp(argv[1], "hardware")) ceiling = 0x8000000000ull, capacity = 16ull << 30;
    else assert(!strcmp(argv[1], "phone") || !strcmp(argv[1], "disabled"));
    ios_reserve_fex_arena();
    if (registration_fails || !strcmp(argv[1], "disabled")) {
        assert(!held_size && !ios_fex_arena_base_unix && !ios_fex_arena_end_unix);
        assert(successful_maps == releases);
    } else {
        uint64_t expected = !strcmp(argv[1], "cap") || !strcmp(argv[1], "small") ? 4ull << 30 : capacity;
        assert(held_size == expected && held_base + held_size <= ceiling);
        assert(ios_fex_arena_base_unix == held_base && ios_fex_arena_end_unix == held_base + held_size);
        assert(successful_maps == releases + 1 && registrations == 1);
        assert(!strcmp(getenv("WINE_IOS_FEX_ARENA_VERSION"), "1"));
        if (!strcmp(argv[1], "phone")) {
            assert(held_base == ios_layerkit_hi);
            /* Keep the same per-thread reservations; capacity covers a 128-thread
             * startup fleet with 80MB each, where the old 8GB arena cannot. */
            assert(128ull * (80ull << 20) <= held_size);
            assert(128ull * (80ull << 20) > (8ull << 30));
            assert(ceiling - (held_base + held_size) >= (6ull << 30));
        }
    }
    int before = successful_maps;
    ios_reserve_fex_arena(); assert(successful_maps == before); /* once per task */
    printf("PASS: production arena reservation %s\n", argv[1]);
}
'''
with tempfile.TemporaryDirectory(prefix='madeira-arena-') as directory:
    path = Path(directory)
    (path / 'probe.c').write_text(code, encoding='utf-8')
    exe = path / 'probe'
    subprocess.run(['cc', '-std=gnu11', '-O1', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(path / 'probe.c'), '-o', str(exe)], check=True)
    print('Production reservation compiled with AddressSanitizer/UBSan', flush=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('MADEIRA_', 'WINE_IOS_FEX_ARENA_'))}
    for scenario in ['phone', 'fallback', 'cap', 'failure', 'small', 'hardware', 'disabled']:
        run_env = dict(env)
        if scenario == 'disabled':
            run_env['MADEIRA_FEX_ARENA'] = '0'
        subprocess.run([str(exe), scenario], env=run_env, check=True, timeout=30)
