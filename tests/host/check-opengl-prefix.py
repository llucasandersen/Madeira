#!/usr/bin/env python3
"""Run the production GL farm seeder for native Steam roots and EC roots."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'app/Madeira/WineProcessBridge.m').read_text(encoding='utf-8')
start = source.index('static void madeira_link_opengl(')
end = source.index('\nstatic void madeira_link_syswow64_wbem(', start)
body = source[start:end]
call = source.index('madeira_link_opengl(fm, prefix, bundlePath, use_arm64ec && !is_i386_target);')
assert source.index('[WineProc] Farm %s:') < call, 'ordinary farms must not overwrite the GL links'
assert 'if (openGL && !strcmp(openGL, "1"))' in source[call - 95:call]
harness = '#import <Foundation/Foundation.h>\n#include <stdio.h>\n' + body + r'''
int main(int argc, char **argv) {
    @autoreleasepool {
        madeira_link_opengl([NSFileManager defaultManager],
            [NSString stringWithUTF8String:argv[1]],
            [NSString stringWithUTF8String:argv[2]], atoi(argv[3]) != 0);
    }
    return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    file = tmp / 'prefix.m'; file.write_text(harness)
    binary = tmp / 'prefix'
    subprocess.run(['clang', '-fobjc-arc', '-framework', 'Foundation', str(file), '-o', str(binary)], check=True)
    components = ['opengl32.dll', 'libgallium_wgl.dll']
    for root_ec in [False, True]:
        prefix = tmp / ('ec-root' if root_ec else 'steam-native-root')
        windows = prefix / 'drive_c/windows'
        for farm in ['system32', 'sysx64', 'sysaa64', 'syswow64']:
            folder = windows / farm; folder.mkdir(parents=True)
            for name in components:
                (folder / name).write_bytes((farm + '-original').encode())
        for version in ['old-install', 'new-install']:
            bundle = tmp / version
            folder = bundle / 'x86_64-opengl'; folder.mkdir(parents=True, exist_ok=True)
            for name in components:
                (folder / name).write_bytes((version + '/' + name).encode())
            # On reinstall the old bundle UUID no longer resolves.
            if version == 'new-install' and root_ec is False:
                for name in components: (tmp / 'old-install/x86_64-opengl' / name).unlink()
            subprocess.run([str(binary), str(prefix), str(bundle), str(int(root_ec))], check=True)
            for farm in ['system32', 'sysx64', 'sysaa64', 'syswow64']:
                for name in components:
                    link = windows / farm / name
                    if farm == 'sysx64' or (root_ec and farm == 'system32'):
                        assert link.is_symlink() and link.resolve() == (folder / name).resolve()
                        assert link.read_bytes() == (version + '/' + name).encode()
                    else:
                        assert not link.is_symlink() and link.read_bytes() == (farm + '-original').encode()
            assert (windows / 'sysx64/opengl32.dll').resolve().parent == (windows / 'sysx64/libgallium_wgl.dll').resolve().parent
print('PASS: native Steam roots link both Zink DLLs into sysx64; EC roots also update system32; reinstall refresh and other architectures preserved')
