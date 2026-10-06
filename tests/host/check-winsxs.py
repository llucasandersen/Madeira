#!/usr/bin/env python3
"""Run the production assembly seeder against real temporary prefix folders."""
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
source = (root / 'app/Madeira/WineProcessBridge.m').read_text()
start = source.index('static void madeira_seed_winsxs(')
end = source.index('\nstatic void madeira_seed_winsxs_x86(', start)
code = '#import <Foundation/Foundation.h>\n#include <stdio.h>\n' + source[start:end] + r'''
int main(int argc, char **argv) {
    @autoreleasepool {
        NSFileManager *fm = [NSFileManager defaultManager];
        NSString *prefix = [NSString stringWithUTF8String:argv[1]];
        NSString *bundle = [NSString stringWithUTF8String:argv[2]];
        madeira_seed_winsxs(fm, prefix, bundle, @"x86", @"i386-windows");
        madeira_seed_winsxs(fm, prefix, bundle, @"amd64", @"arm64ec-windows");
    }
    return 0;
}
'''
namespace = {'a': 'urn:schemas-microsoft-com:asm.v1'}
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    file = tmp / 'check.m'; file.write_text(code)
    exe = tmp / 'check'
    subprocess.run(['clang', '-fobjc-arc', '-framework', 'Foundation', str(file), '-o', str(exe)], check=True)
    prefix = tmp / 'prefix'
    for version in ['bundle-old', 'bundle-new']:
        bundle = tmp / version
        for farm in ['i386-windows', 'arm64ec-windows']:
            folder = bundle / farm; folder.mkdir(parents=True)
            (folder / 'comctl32_v6.dll').write_bytes(version.encode())
        subprocess.run([str(exe), str(prefix), str(bundle)], check=True)
        store = prefix / 'drive_c/windows/winsxs'
        manifests = sorted((store / 'manifests').glob('*.manifest'))
        assert len(manifests) == 2, 'missing DLLs must not receive assembly manifests'
        for architecture, farm in [('x86', 'i386-windows'), ('amd64', 'arm64ec-windows')]:
            manifest = next(p for p in manifests if p.name.startswith(architecture + '_'))
            tree = ET.fromstring(manifest.read_bytes())
            identity = tree.find('a:assemblyIdentity', namespace)
            assert identity.attrib['processorArchitecture'] == architecture
            assert identity.attrib['name'] == 'Microsoft.Windows.Common-Controls'
            assert identity.attrib['version'] == '6.0.2600.2982'
            dlls = tree.findall('a:file', namespace)
            assert [p.attrib['name'] for p in dlls] == ['comctl32.dll']
            link = store / manifest.stem / 'comctl32.dll'
            assert link.is_symlink() and link.resolve() == (bundle / farm / 'comctl32_v6.dll').resolve()
            assert link.read_bytes() == version.encode(), 'reinstall must refresh the bundle target'
            assert dlls[0].findall('a:windowClass', namespace), 'preserve controls class redirects'
print('PASS: production WinSxS seeder: x86/amd64 identity and farm separation, missing DLL refusal, and reinstall link refresh')
