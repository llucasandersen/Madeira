#!/bin/bash
set -euo pipefail
# Keep the runtime component builds on their pinned toolchain; only the app
# needs the new SDK's resizable-phone behavior. Never silently ship a 26 SDK IPA.
for candidate in /Applications/Xcode_27*.app; do
    developer="$candidate/Contents/Developer"
    [ -d "$developer" ] || continue
    sdk=$(DEVELOPER_DIR="$developer" xcrun --sdk iphoneos --show-sdk-version)
    if python3 - "$sdk" <<'PY'
import sys
parts = tuple(int(p) for p in sys.argv[1].split('.'))
raise SystemExit(0 if parts >= (27, 1) else 1)
PY
    then
        printf 'DEVELOPER_DIR=%s\n' "$developer" >> "$GITHUB_ENV"
        printf 'Duo app toolchain: %s; iOS SDK %s\n' "$developer" "$sdk"
        exit 0
    fi
done
echo 'An iOS 27.1 or later SDK is required for the Duo app package.' >&2
exit 1
