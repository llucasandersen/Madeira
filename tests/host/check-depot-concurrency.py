#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Compile the production tuning policy and exercise throughput/load changes."""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'app/Madeira/SwiftSteam/Content/DepotDownloader.swift').read_text()
policy = 'struct ContentConcurrency {' + source.split('struct ContentConcurrency {', 1)[1].split('/// Chunk-request measurements', 1)[0]
fixture = r'''
import Foundation
func expect(_ value: Bool, _ message: String) {
    if !value { fatalError(message) }
}
func window(_ policy: inout ContentConcurrency, _ time: inout Double,
            duration: Double = 2, network: Double = 1, processing: Double = 0.1,
            retries: Int = 0) -> String? {
    let count = policy.limit
    var result: String?
    for _ in 0..<count {
        time += duration / Double(count)
        result = policy.observe(now: time, bytes: 1_000_000, network: network,
                                processing: processing, retries: retries) ?? result
    }
    return result
}
var time = 0.0
var p = ContentConcurrency(started: time)
expect(p.limit == 8, "initial batch")
// Roundoff-safe windows above two seconds. More tasks in the same wall time
// model a network that benefits from concurrency.
expect(window(&p, &time, duration: 2.1) == "probe" && p.limit == 10, "first probe")
expect(window(&p, &time, duration: 2.1) == "probe-gain" && p.limit == 10, "keep gain")
for _ in 0..<20 { _ = window(&p, &time, duration: 2.1) }
expect(p.limit == 16 && p.peak == 16, "upper bound")
expect(window(&p, &time, duration: 2.1, retries: 1) == "retries" && p.limit == 8, "retry backoff")
expect(window(&p, &time, duration: 2.1, processing: 2) == "processing" && p.limit == 6, "processing backoff")
for _ in 0..<20 { _ = window(&p, &time, duration: 2.1, retries: 1) }
expect(p.limit == 2, "lower bound")
// A plateau at identical useful bytes/second rolls back the probe.
time = 0; p = ContentConcurrency(started: time)
_ = window(&p, &time, duration: 2.1)
expect(window(&p, &time, duration: 2.625) == "probe-no-gain" && p.limit == 8, "plateau rollback")
expect(window(&p, &time, duration: 2.1) == nil && p.limit == 8, "cooldown first")
expect(window(&p, &time, duration: 2.1) == nil && p.limit == 8, "cooldown second")
expect(window(&p, &time, duration: 2.1) == "probe", "probe resumes")
// Cached/resumed chunks, invalid clocks and partial/fast batches cannot tune.
time = 0; p = ContentConcurrency(started: time)
for _ in 0..<100 {
    expect(p.observe(now: 100, bytes: 0, network: 0, processing: 0, retries: 0) == nil, "resume ignored")
}
expect(p.observe(now: .nan, bytes: 100, network: 1, processing: 0, retries: 0) == nil, "invalid clock")
expect(p.observe(now: -1, bytes: 100, network: 1, processing: 0, retries: 0) == nil, "backwards clock")
for i in 1...8 {
    expect(p.observe(now: Double(i) / 10, bytes: 100, network: 1, processing: 0, retries: 0) == nil, "short window")
}
expect(p.limit == 8, "no premature tuning")
print("check-depot-concurrency: bounded probes, gain/plateau, retries, processing, cooldown and resume passed")
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    path.joinpath('probe.swift').write_text('import Foundation\n' + policy + fixture)
    compiler = shutil.which('swiftc')
    if not compiler:
        raise SystemExit('Swift compiler required; run the host regression workflow.')
    subprocess.run([compiler, str(path / 'probe.swift'), '-o', str(path / 'probe')], check=True, timeout=120)
    subprocess.run([str(path / 'probe')], check=True, timeout=30)
