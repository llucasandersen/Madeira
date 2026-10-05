#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 125hz
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Run actual Mach paired-store decoding and native STP on an ARM/LSE2 Mac."""
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
assert platform.system() == 'Darwin' and platform.machine() == 'arm64', 'ARM Mac required; use the Apple host workflow'
assert subprocess.check_output(['sysctl', '-n', 'hw.optional.arm.FEAT_LSE2'], text=True).strip() == '1', 'LSE2 ARM Mac required for pair atomicity verification'
source = (root / 'build/ntdll-unix/signal_arm64_ios.c').read_text(encoding='utf-8')
start = source.index('static int ios_mach_emulate_stp_alias(')
production = source[start:source.index('\n}', start) + 2]
assert 'emulated = ios_mach_emulate_stp_alias(insn, fault_addr, rw_addr, rx, sz, in_jit, &state);' in source
code = r'''
#include <assert.h>
#include <mach/arm/thread_status.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
static uintptr_t guest, host;
static size_t extent;
uintptr_t ios_jit_anon_alias_lookup(uintptr_t address) {
    return address >= guest && address - guest < extent ? host + (address - guest) : 0;
}
'''
code += production
code += r'''
static uint32_t instruction(unsigned width, unsigned mode, int units, unsigned rt, unsigned rt2, unsigned rn) {
    return 0x28000000u | (width == 8 ? 0x80000000u : 0) | (mode << 23) |
           (((uint32_t)units & 127) << 15) | (rt2 << 10) | (rn << 5) | rt;
}
static uint64_t get(arm_thread_state64_t *s, unsigned n) {
    return n < 29 ? s->__x[n] : n == 29 ? s->__fp : n == 30 ? s->__lr : 0;
}
static void put(arm_thread_state64_t *s, unsigned n, uint64_t value) {
    if (n < 29) s->__x[n] = value; else if (n == 29) s->__fp = value; else if (n == 30) s->__lr = value;
}
static atomic_uint writers;
static void *pair_writer(void *lane) {
    arm_thread_state64_t s = {0}; s.__x[0] = guest;
    for (uint64_t i = 1; i <= 50000; ++i) {
        uint64_t value = ((uintptr_t)lane << 60) | i;
        s.__x[2] = s.__x[3] = value;
        assert(ios_mach_emulate_stp_alias(instruction(8, 2, 0, 2, 3, 0), guest, host, guest, 16, 1, &s));
    }
    atomic_fetch_sub_explicit(&writers, 1, memory_order_release);
    return NULL;
}
int main(void) {
    _Alignas(16) unsigned char memory[2048];
    guest = 0x70000000; host = (uintptr_t)memory; extent = sizeof(memory);
    const int offsets[] = {-64, -1, 0, 1, 63};
    for (unsigned width = 4; width <= 8; width += 4) for (unsigned mode = 0; mode < 4; mode++)
    for (unsigned oi = 0; oi < 5; oi++) for (unsigned half = 0; half < 2; half++) for (int pool = 0; pool < 2; pool++) {
        int units = offsets[oi], offset = units * (int)width;
        uintptr_t base = guest + 768, address = mode == 1 ? base : base + offset;
        uintptr_t far = address + half * width;
        arm_thread_state64_t s = {0}; s.__x[10] = base;
        s.__x[9] = 0x123456789abcdef0ULL; s.__x[8] = 0xfedcba9876543210ULL;
        s.__sp = 0xfeed; s.__pc = 0x1234; s.__cpsr = 0x9876;
        memset(memory, 0x5a, sizeof(memory));
        uint32_t insn = instruction(width, mode, units, 9, 8, 10);
        assert(ios_mach_emulate_stp_alias(insn, far, host + far - guest, guest, extent, pool, &s));
        uint64_t first = 0, second = 0;
        memcpy(&first, memory + (address - guest), width); memcpy(&second, memory + (address - guest) + width, width);
        uint64_t mask = width == 8 ? UINT64_MAX : UINT32_MAX;
        assert(first == (s.__x[9] & mask) && second == (s.__x[8] & mask));
        assert(s.__x[10] == (mode == 1 || mode == 3 ? base + offset : base));
        assert(s.__sp == 0xfeed && s.__pc == 0x1234 && s.__cpsr == 0x9876);
        for (unsigned k = 0; k < sizeof(memory); ++k) if (k < address - guest || k >= address - guest + 2 * width) assert(memory[k] == 0x5a);
    }
    assert(instruction(8, 3, 16, 9, 8, 10) == 0xa9882149); // reported CoreCLR opcode
    for (unsigned rt = 0; rt < 32; rt++) for (unsigned rt2 = 0; rt2 < 32; rt2++) {
        arm_thread_state64_t s = {0}; put(&s, rt, 0x12); put(&s, rt2, 0x34); s.__sp = guest;
        uint64_t a = get(&s, rt), b = get(&s, rt2);
        assert(ios_mach_emulate_stp_alias(instruction(8, 1, 1, rt, rt2, 31), guest, host, guest, extent, 1, &s));
        uint64_t actual[2]; memcpy(actual, memory, 16);
        assert(actual[0] == a && actual[1] == b && s.__sp == guest + 8);
    }
    // Writeback overlap takes the architecturally permitted pre-writeback source.
    arm_thread_state64_t s = {0}; s.__x[10] = guest; s.__x[8] = 7;
    assert(ios_mach_emulate_stp_alias(instruction(8, 3, 1, 10, 8, 10), guest + 8, host + 8, guest, extent, 1, &s));
    uint64_t overlap; memcpy(&overlap, memory + 8, 8); assert(overlap == guest && s.__x[10] == guest + 8);
    // Unaligned pairs are executed by the same native instruction, not C typed dereferences.
    s.__x[10] = guest + 3;
    assert(ios_mach_emulate_stp_alias(instruction(8, 2, 0, 9, 8, 10), guest + 3, host + 3, guest, extent, 1, &s));
    // Refusal cannot write the first half or apply writeback before validating the second.
    unsigned char saved[2048]; memcpy(saved, memory, sizeof(memory));
    s = (arm_thread_state64_t){0}; s.__x[10] = guest;
    arm_thread_state64_t before; memcpy(&before, &s, sizeof(s));
    uint32_t insn = instruction(8, 1, 1, 9, 8, 10);
    extent = 8;
    assert(!ios_mach_emulate_stp_alias(insn, guest, host, 0, 0, 0, &s));
    assert(!ios_mach_emulate_stp_alias(insn, guest + 8, host + 8, guest, extent, 1, &s));
    extent = sizeof(memory);
    for (uint32_t bad = 0; bad < 3; bad++) {
        uint32_t other = bad == 0 ? insn | 0x00400000 : bad == 1 ? insn | 0x04000000 : insn | 0x40000000;
        assert(!ios_mach_emulate_stp_alias(other, guest, host, guest, extent, 1, &s)); // LDP, SIMD pair, reserved opc
    }
    assert(!ios_mach_emulate_stp_alias(insn, guest + 16, host + 16, guest, extent, 1, &s));
    assert(!ios_mach_emulate_stp_alias(insn, guest, 0, guest, extent, 1, &s));
    assert(!memcmp(saved, memory, sizeof(memory)) && !memcmp(&before, &s, sizeof(s)));
    // A real inaccessible page catches a missed span check even though sanitizers cannot instrument inline asm.
    size_t page = (size_t)sysconf(_SC_PAGESIZE);
    unsigned char *guard = mmap(NULL, page * 2, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANON, -1, 0);
    assert(guard != MAP_FAILED && !mprotect(guard + page, page, PROT_NONE));
    memset(guard + page - 8, 0x5a, 8); s.__x[10] = guest + page - 8;
    assert(!ios_mach_emulate_stp_alias(instruction(8, 2, 0, 9, 8, 10), guest + page - 8, (uintptr_t)(guard + page - 8), guest, page, 1, &s));
    for (unsigned i = 0; i < 8; i++) assert(guard[page - 8 + i] == 0x5a);
    munmap(guard, page * 2);
    // Exercise actual LSE2 single-copy pair behavior with competing native writers/readers.
    memset(memory, 0, 16); atomic_store(&writers, 2); pthread_t peers[2];
    assert(!pthread_create(&peers[0], NULL, pair_writer, (void *)1));
    assert(!pthread_create(&peers[1], NULL, pair_writer, (void *)2));
    unsigned reads = 0;
    do {
        uint64_t a, b;
        __asm__ volatile("ldp %x[a], %x[b], [%x[p]]" : [a] "=&r"(a), [b] "=&r"(b) : [p] "r"(host) : "memory");
        assert(a == b); ++reads;
    } while (atomic_load_explicit(&writers, memory_order_acquire));
    pthread_join(peers[0], NULL); pthread_join(peers[1], NULL);
    assert(reads);
    puts("PASS: actual ARM STP, reported CoreCLR opcode, 32/64-bit offset/pre/post/STNP, either-half faults, registers/writeback/overlap, guard-page refusal and 100000 single-copy paired writes");
}
'''
compiler = shutil.which('clang')
assert compiler, 'Apple clang required'
with tempfile.TemporaryDirectory(prefix='madeira-mach-stp-') as directory:
    path = Path(directory)
    (path / 'probe.c').write_text(code, encoding='utf-8')
    for sanitizer in ['address,undefined', 'thread']:
        exe = path / sanitizer.replace(',', '-')
        subprocess.run([compiler, '-std=gnu11', '-O1', '-Wall', '-Wextra', '-Werror', '-pthread',
                        '-fsanitize=' + sanitizer, '-fno-sanitize-recover=all', str(path / 'probe.c'), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, timeout=60)
