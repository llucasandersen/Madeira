#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT="$ROOT/build/bcd-duo-compat"
mkdir -p "$OUT"
SDK=$(xcrun --sdk iphoneos --show-sdk-version)
python3 - "$SDK" <<'PY'
import sys
assert tuple(map(int,sys.argv[1].split('.'))) >= (27,1)
PY
xcrun --sdk iphoneos clang -arch arm64 -miphoneos-version-min=18.0 \
  -fobjc-arc -fblocks -O2 -Wall -Wextra -Wno-unused-parameter \
  -dynamiclib "$ROOT/tools/bcd-duo/BCDDuo.m" \
  -install_name @executable_path/Frameworks/BCDDuo.dylib \
  -framework UIKit -framework QuartzCore -framework AVFAudio -o "$OUT/BCDDuo.dylib"
codesign --force --sign - "$OUT/BCDDuo.dylib"
codesign --verify --strict "$OUT/BCDDuo.dylib"
otool -l "$OUT/BCDDuo.dylib" > "$OUT/load-commands.txt"
python3 - "$OUT" "$SDK" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1])
(out/'build.json').write_text(json.dumps(dict(sdk=sys.argv[2],
 commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 library_sha256=hashlib.sha256((out/'BCDDuo.dylib').read_bytes()).hexdigest(),
 source_bcd_tag='v0.1.623',kind='unofficial binary compatibility layer, not BCD source rebuild'),indent=2)+'\n')
PY

# Build a small real UIKit host to exercise the concrete layout integration.
SIMSDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
APP="$OUT/DisplayFixture.app"
mkdir -p "$APP"
xcrun clang -target arm64-apple-ios18.0-simulator -isysroot "$SIMSDK" \
  -fobjc-arc -fblocks -O1 -DBCD_DUO_TESTING \
  "$ROOT/tools/bcd-duo/BCDDuo.m" "$ROOT/tools/bcd-duo/DisplayHarness.m" \
  -framework UIKit -framework QuartzCore -framework AVFAudio -framework Metal -o "$APP/DisplayFixture"
python3 - "$APP" <<'PY'
import plistlib,sys
from pathlib import Path
p=Path(sys.argv[1])/'Info.plist'
p.write_bytes(plistlib.dumps(dict(CFBundleIdentifier='local.bcd.duo.fixture',CFBundleExecutable='DisplayFixture',
 CFBundleName='DisplayFixture',CFBundleVersion='1',CFBundlePackageType='APPL',MinimumOSVersion='18.0',
 UIDeviceFamily=[1,2],UILaunchScreen={},UIApplicationSceneManifest=dict(UIApplicationSupportsMultipleScenes=False))))
PY
codesign --force --sign - "$APP"
xcrun simctl list devices available -j > "$OUT/simulators.json"
DEVICE=$(python3 - "$OUT/simulators.json" <<'PY'
import json,sys
devices=[d for r,ds in json.load(open(sys.argv[1]))['devices'].items() if 'iOS-27' in r for d in ds if d.get('isAvailable')]
assert devices, 'No iOS 27 simulator available'
devices.sort(key=lambda d: ('Duo' not in d['name'], 'iPhone' not in d['name']))
print(devices[0]['udid'])
PY
)
xcrun simctl boot "$DEVICE" || true
xcrun simctl bootstatus "$DEVICE" -b
xcrun simctl install "$DEVICE" "$APP"
xcrun simctl launch --terminate-running-process "$DEVICE" local.bcd.duo.fixture
CONTAINER=$(xcrun simctl get_app_container "$DEVICE" local.bcd.duo.fixture data)
for i in $(seq 1 45); do
  if [ -f "$CONTAINER/Documents/duo-fixture.json" ]; then break; fi
  sleep 1
done
cp "$CONTAINER/Documents/duo-fixture.json" "$OUT/duo-fixture.json"
python3 - "$OUT/duo-fixture.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print(json.dumps(r,indent=2));assert r['passed'],r
PY
