"""Patch the user's BCD 623 IPA, preserving its exact bundled game runtime.

This is a binary compatibility candidate, not a source rebuild of BCD. The
main executable's SDK declaration opts into Duo layout; its original machine
code is retained. Only the separately built compatibility dylib uses SDK 27.1.
"""
from pathlib import Path
import argparse
import hashlib
import json
import plistlib
import struct
import zipfile

SOURCE_SHA256 = '570b6e35dc3c87d5971900a7201d69e2e07d7c070b4b3d2e86686d8a392b8140'
DYLIB = '@executable_path/Frameworks/BCDDuo.dylib'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def patch_macho(binary):
    b = bytearray(binary)
    assert struct.unpack_from('<I', b)[0] == 0xfeedfacf
    assert struct.unpack_from('<I', b, 4)[0] == 0x100000c, 'expected arm64'
    count, size = struct.unpack_from('<II', b, 16)
    off, commands, first_data = 32, [], len(b)
    original_sdk, signatures = None, []
    for _ in range(count):
        cmd, length = struct.unpack_from('<II', b, off)
        assert length >= 8 and off + length <= 32 + size
        command = bytearray(b[off:off+length])
        if cmd == 0x19:
            sections = struct.unpack_from('<I', command, 64)[0]
            for i in range(sections):
                section = 72 + i * 80
                offset = struct.unpack_from('<I', command, section + 48)[0]
                if offset: first_data = min(first_data, offset)
        if cmd == 0x2c:
            assert struct.unpack_from('<I', command, 16)[0] == 0, 'encrypted binary'
        if cmd == 0x32:
            assert struct.unpack_from('<I', command, 8)[0] == 2
            original_sdk = struct.unpack_from('<I', command, 16)[0]
            assert original_sdk == (26 << 16 | 2 << 8), 'not the inspected BCD 623 binary'
            struct.pack_into('<I', command, 16, 27 << 16 | 1 << 8)
        if cmd == 0x1d:
            start, length_sig = struct.unpack_from('<II', command, 8)
            signatures.append((start,length_sig))
        commands.append(bytes(command))
        off += length
    assert off == 32 + size and original_sdk is not None
    path = DYLIB.encode() + b'\0'
    length = (24 + len(path) + 7) & ~7
    load = struct.pack('<IIIIII', 0xc, length, 24, 0, 0x10000, 0x10000) + path
    commands.append(load.ljust(length, b'\0'))
    blob = b''.join(commands)
    assert 32 + len(blob) <= first_data, 'no load-command padding'
    assert not any(b[32+size:32+len(blob)]), 'nonzero header padding'
    b[32:32+max(size,len(blob))] = blob.ljust(max(size,len(blob)), b'\0')
    struct.pack_into('<II', b, 16, len(commands), len(blob))
    # Keep the old signature blob as entitlement input for the sideload signer.
    # It is stale after changing load commands and MUST be re-signed to install.
    # In particular, stripping it would lose the existing memory/JIT rights.
    assert len(b) == len(binary)
    # Every byte outside load commands and the old signature remains intact.
    allowed = [(16,24),(32,32+max(size,len(blob)))]
    cursor = 0
    for start,end in sorted(allowed):
        assert b[cursor:start] == binary[cursor:start]
        cursor = max(cursor,end)
    assert b[cursor:] == binary[cursor:]
    return bytes(b), original_sdk

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source',type=Path)
    ap.add_argument('dylib',type=Path)
    ap.add_argument('output',type=Path)
    args = ap.parse_args()
    original = args.source.read_bytes()
    assert sha(original) == SOURCE_SHA256, 'input IPA changed'
    companion = args.dylib.read_bytes()
    assert b'[bcd-duo-display]' in companion
    assert not args.output.exists(), 'refusing to overwrite an existing candidate'
    changes, retained, oldsdk = [], {}, None
    root = 'Payload/Madeira.app/'
    main_binary = root + 'Madeira'
    with zipfile.ZipFile(args.source) as src, zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for item in src.infolist():
            name = item.filename
            if name.startswith(root+'_CodeSignature/') or name == root+'embedded.mobileprovision':
                continue
            data = src.read(item)
            if name == main_binary:
                data, oldsdk = patch_macho(data)
                changes.append(name)
            elif name == root+'Info.plist':
                info = plistlib.loads(data)
                assert info['CFBundleVersion'] == '623'
                # Keep truthful original compiler fields; record the opt-in separately.
                info['CFBundleDisplayName'] = 'BCD Duo (Unofficial)'
                info['UIRequiresFullScreen'] = False
                info['UISupportedInterfaceOrientations'] = ['UIInterfaceOrientationPortrait','UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']
                info['BCDDuoCompatibilityPatch'] = dict(version=1, originalSDK='26.2', layoutSDKDeclaration='27.1', sourceRebuild=False, deviceAcceptance='pending')
                data = plistlib.dumps(info,fmt=plistlib.FMT_BINARY)
                changes.append(name)
            else:
                if not item.is_dir(): retained[name] = sha(data)
            out.writestr(item,data)
        assert oldsdk is not None
        out.writestr(root+'Frameworks/BCDDuo.dylib',companion)
        notice = ('Unofficial BCD 623 Duo compatibility patch, modified 2026-10-30.\n'
                  'Based on BCD by thebcd69: https://github.com/thebcd69/bcd-games\n'
                  'The original app remains SDK 26.2 code; its SDK load-command declaration\n'
                  'is changed to opt into Duo layout. The display companion is built with SDK 27.1.\n'
                  'This is not an official BCD release or a full SDK 27.1 source rebuild.\n'
                  'Requires re-signing and physical-device gameplay/fold/AirPlay testing.\n')
        out.writestr(root+'BCDDuo-NOTICE.txt',notice)
    with zipfile.ZipFile(args.output) as z:
        assert z.testzip() is None
        for name,digest in retained.items(): assert sha(z.read(name)) == digest, name
        assert DYLIB.encode() in z.read(main_binary)
    digest = sha(args.output.read_bytes())
    args.output.with_suffix('.ipa.sha256').write_text(digest+'  '+args.output.name+'\n')
    report = dict(input_sha256=SOURCE_SHA256, output_sha256=digest, output=args.output.name,
                  original_bcd_version='0.1.623', modified_files=changes,
                  original_sdk='26.2', main_sdk_declaration='27.1', source_rebuild=False,
                  retained_files=len(retained), companion_sha256=sha(companion),
                  game_runtime_and_data='all bundled files preserved byte-for-byte; executable code preserved',
                  requires_resigning=True, physical_device_acceptance='pending')
    args.output.with_suffix('.report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__': main()
