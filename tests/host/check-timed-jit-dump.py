#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Execute the production diagnostic delay parser with malformed settings."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/server_ios.c').read_text()
start = source.index('static unsigned ios_jit_dump_delay(')
policy = source[start:source.index('\nstatic void ios_thread_sampler_main(', start)]
probe = '#include <assert.h>\n#include <stdlib.h>\n' + policy + r'''
int main(void) {
    assert(ios_jit_dump_delay(NULL) == 0);
    const char *invalid[] = {"", "0", "-1", "+120", " 120", "120x", "120 ", "3601",
                            "9999999999999999999999999999999999999999999999"};
    for (unsigned i=0; i<sizeof invalid/sizeof invalid[0]; i++)
        assert(ios_jit_dump_delay(invalid[i]) == 0);
    assert(ios_jit_dump_delay("1") == 1);
    assert(ios_jit_dump_delay("120") == 120);
    assert(ios_jit_dump_delay("3600") == 3600);
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='madeira-timed-dump-') as directory:
    path = Path(directory)
    (path / 'probe.c').write_text(probe)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(path / 'probe.c'), '-o', str(path / 'probe')], check=True)
    subprocess.run([str(path / 'probe')], check=True, timeout=15)
print('PASS: timed JIT capture is opt-in and rejects malformed or unbounded delays')
