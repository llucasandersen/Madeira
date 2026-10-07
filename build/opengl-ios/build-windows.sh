#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$R"
bash build/ci/fetch-mingw.sh
TC="$R/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin"
export PATH="$(brew --prefix bison)/bin:$TC:$PATH"
SOURCE="$(python3 build/opengl-ios/fetch-mesa.py)"
python3 build/opengl-ios/patch-wgl-diagnostics.py "$SOURCE"
OUT="$R/build/ci-output/opengl-windows"
mkdir -p "$OUT"
cat > "$OUT/windows-cross.ini" <<EOF
[binaries]
c = '$TC/x86_64-w64-mingw32-clang'
cpp = '$TC/x86_64-w64-mingw32-clang++'
ar = '$TC/llvm-ar'
strip = '$TC/x86_64-w64-mingw32-strip'
windres = '$TC/x86_64-w64-mingw32-windres'
pkg-config = 'false'
[host_machine]
system = 'windows'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
[properties]
needs_exe_wrapper = true
EOF
# Only the real Vulkan-backed desktop GL driver is built. No software fallback
# or version override is used to satisfy Teardown's required feature level.
meson setup "$OUT/zink" "$SOURCE" --cross-file "$OUT/windows-cross.ini" --buildtype=release \
  -Dplatforms=windows -Dgallium-drivers=zink -Dvulkan-drivers= \
  -Dopengl=true -Dgles1=disabled -Dgles2=disabled -Degl=disabled -Dglx=disabled \
  -Dllvm=disabled -Dzlib=disabled -Dzstd=disabled -Dxmlconfig=disabled \
  -Dshared-glapi=disabled -Dbuild-tests=false -Dtools=
ninja -C "$OUT/zink" -j4
find "$OUT/zink" -name '*.dll' -print
test -s "$OUT/zink/src/gallium/targets/libgl-gdi/opengl32.dll"
# Build the Windows-facing Vulkan loader and ICD from the tracked Wine source.
export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
export CC="$(xcrun --find clang)"
mkdir -p wine/build-arm64ec
(cd wine/build-arm64ec && ../configure --enable-archs=arm64ec --without-x --disable-tests)
DEST="$OUT/wine" bash build/wine-pe/build-modules.sh vulkan-1 winevulkan
for library in "$OUT/wine"/*.dll "$OUT/zink/src/gallium/targets/libgl-gdi/opengl32.dll"; do
  "$TC/llvm-readobj" --file-headers --coff-imports "$library"
done > "$OUT/pe-dependencies.txt"
