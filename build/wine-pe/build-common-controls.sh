#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Build the pinned Wine v6 controls required by AMD64 activation contexts.
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
TC="$R/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin"
export PATH="$(brew --prefix bison)/bin:$TC:$PATH"
W="$R/wine/build-dxmt-arm64ec"
OUT="$R/build/ci-output/common-controls"
test -f "$W/config.status" # configured by build/dxmt-ios/build-pe.sh
mkdir -p "$OUT/modules"
make -C "$W" -j2 dlls/comctl32_v6/arm64ec-windows/comctl32_v6.dll
"$TC/arm64ec-w64-mingw32-strip" --strip-debug \
    -o "$OUT/modules/comctl32_v6.dll" "$W/dlls/comctl32_v6/arm64ec-windows/comctl32_v6.dll"
git -C "$R" rev-parse HEAD > "$OUT/madeira-commit.txt"
git -C "$R/wine" rev-parse HEAD > "$OUT/wine-commit.txt"
(cd "$OUT/modules" && shasum -a 256 comctl32_v6.dll > ../module-sha256.txt)
python3 "$R/tools/inspect-pe-imports.py" "$OUT/modules/comctl32_v6.dll" > "$OUT/pe-metadata.jsonl"
