#!/usr/bin/env python3
"""Run the production GL farm seeder for native Steam roots and EC roots."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'app/Madeira/WineProcessBridge.m').read_text(encoding='utf-8')
start = source.index('static void madeira_clear_opengl_links(')
end = source.index('\nstatic void madeira_link_syswow64_wbem(', start)
body = source[start:end]
call = source.index('madeira_link_opengl(fm, prefix, bundlePath, use_arm64ec && !is_i386_target);')
assert source.index('[WineProc] Farm %s:') < call, 'ordinary farms must not overwrite the GL links'
assert 'if (openGL && !strcmp(openGL, "1"))' in source[call - 95:call]
assert source.index('madeira_clear_opengl_links(fm, prefix, bundlePath);') < call
harness = '#import <Foundation/Foundation.h>\n#include <stdio.h>\n' + body + r'''
int main(int argc, char **argv) {
    @autoreleasepool {
        NSFileManager *fm = [NSFileManager defaultManager];
        NSString *prefix = [NSString stringWithUTF8String:argv[1]];
        madeira_clear_opengl_links(fm, prefix, [NSString stringWithUTF8String:argv[2]]);
        if (atoi(argv[4])) madeira_link_opengl(fm, prefix,
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
    components = ['opengl32.dll', 'libgallium_wgl.dll', 'vulkan-1.dll', 'winevulkan.dll']
    for root_ec, app_name in [(False, 'Madeira.app'), (True, 'Madeira.app'), (False, 'App.app'), (True, 'App.app'), (True, 'Resigned.app')]:
        prefix = tmp / (app_name + ('-ec-root' if root_ec else '-steam-native-root'))
        windows = prefix / 'drive_c/windows'
        for farm in ['system32', 'sysx64', 'sysaa64', 'syswow64']:
            folder = windows / farm; folder.mkdir(parents=True)
            for name in components:
                (folder / name).write_bytes((farm + '-original').encode())
        for version in ['old-install', 'new-install']:
            bundle = tmp / app_name / version / app_name
            folder = bundle / 'x86_64-opengl'; folder.mkdir(parents=True, exist_ok=True)
            for name in components:
                (folder / name).write_bytes((version + '/' + name).encode())
            # On reinstall the old bundle UUID no longer resolves.
            if version == 'new-install' and root_ec is False:
                for name in components: (tmp / app_name / 'old-install' / app_name / 'x86_64-opengl' / name).unlink()
            subprocess.run([str(binary), str(prefix), str(bundle), str(int(root_ec)), '1'], check=True)
            for farm in ['system32', 'sysx64', 'sysaa64', 'syswow64']:
                for name in components:
                    link = windows / farm / name
                    if farm == 'sysx64' or (root_ec and farm == 'system32'):
                        assert link.is_symlink() and link.resolve() == (folder / name).resolve()
                        assert link.read_bytes() == (version + '/' + name).encode()
                    else:
                        assert not link.is_symlink() and link.read_bytes() == (farm + '-original').encode()
            assert (windows / 'sysx64/opengl32.dll').resolve().parent == (windows / 'sysx64/libgallium_wgl.dll').resolve().parent
        # A subsequent D3D12 session removes bundle-owned GL/Vulkan links.
        subprocess.run([str(binary), str(prefix), str(bundle), str(int(root_ec)), '0'], check=True)
        for farm in ['sysx64'] + (['system32'] if root_ec else []):
            for name in components:
                path = windows / farm / name
                assert not path.exists() and not path.is_symlink()
        # Upgrade cleanup also recognizes test 6's old globally linked Vulkan
        # DLLs, including dangling targets. User files/other DLL links remain.
        for name in ['vulkan-1.dll', 'winevulkan.dll']:
            path = windows / 'sysx64' / name
            path.symlink_to(tmp / 'removed-install/App.app/arm64ec-windows' / name)
        user = windows / 'system32/vulkan-1.dll'
        if not user.exists(): user.write_bytes(b'user file')
        subprocess.run([str(binary), str(prefix), str(bundle), str(int(root_ec)), '0'], check=True)
        assert user.is_file() and not user.is_symlink()
        for name in ['vulkan-1.dll', 'winevulkan.dll']:
            assert not (windows / 'sysx64' / name).is_symlink()
        # Unrelated application links and ordinary files belong to the user.
        unrelated = windows / 'sysx64' / 'vulkan-1.dll'
        unrelated.symlink_to(tmp / 'Other.app/x86_64-opengl/vulkan-1.dll')
        subprocess.run([str(binary), str(prefix), str(bundle), str(int(root_ec)), '0'], check=True)
        assert unrelated.is_symlink()
print('PASS: native/EC farms, original and renamed bundles, dangling reinstall links, D3D12 cleanup and unrelated user files/links preserved')
