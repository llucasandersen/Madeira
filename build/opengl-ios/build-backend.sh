#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$R"
SOURCE="$(python3 build/opengl-ios/fetch-mesa.py)"
python3 build/opengl-ios/patch-device.py "$SOURCE"
OUT="$R/build/ci-output/opengl-ios"
mkdir -p "$OUT"
export PATH="$(brew --prefix llvm)/bin:$(brew --prefix bison)/bin:$PATH"
export PKG_CONFIG_PATH="$(brew --prefix llvm)/lib/pkgconfig:$(brew --prefix spirv-llvm-translator)/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
MAC_SDK="$(xcrun --sdk macosx --show-sdk-path)"
IOS_SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
export CC="$(xcrun --find clang)" CXX="$(xcrun --find clang++)" OBJC="$(xcrun --find clang)"
export SDKROOT="$MAC_SDK"
# Build Mesa's native shader generation tools first; iOS cannot execute them.
meson setup "$OUT/native" "$SOURCE" --buildtype=release \
  -Dplatforms= -Dgallium-drivers= -Dvulkan-drivers=kosmickrisp \
  -Dopengl=false -Dgles1=disabled -Dgles2=disabled -Degl=disabled -Dglx=disabled \
  -Dbuild-tests=false -Dtools= -Dinstall-mesa-clc=true -Dinstall-precomp-compiler=true \
  -Dmesa-clc=enabled -Dprecomp-compiler=enabled \
  -Dc_args="-isysroot $MAC_SDK -mmacosx-version-min=26.0" \
  -Dcpp_args="-isysroot $MAC_SDK -mmacosx-version-min=26.0" \
  -Dobjc_args="-isysroot $MAC_SDK -mmacosx-version-min=26.0"
ninja -C "$OUT/native" -j4
mkdir -p "$OUT/host-tools"
for tool in mesa_clc vtn_bindgen2 kk_clc; do
  path="$(find "$OUT/native" -type f -name "$tool" | head -1)"
  test -n "$path"
  cp "$path" "$OUT/host-tools/$tool"
done
export PATH="$OUT/host-tools:$PATH"
cat > "$OUT/ios-cross.ini" <<EOF
[binaries]
c = ['$CC', '-target', 'arm64-apple-ios26.0', '-isysroot', '$IOS_SDK']
cpp = ['$CXX', '-target', 'arm64-apple-ios26.0', '-isysroot', '$IOS_SDK']
objc = ['$OBJC', '-target', 'arm64-apple-ios26.0', '-isysroot', '$IOS_SDK']
ar = '$(xcrun --find ar)'
strip = '$(xcrun --find strip)'
pkg-config = 'false'
[host_machine]
system = 'darwin'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'
[properties]
needs_exe_wrapper = true
EOF
export SDKROOT="$IOS_SDK"
meson setup "$OUT/ios" "$SOURCE" --cross-file "$OUT/ios-cross.ini" --buildtype=release \
  -Dplatforms= -Dgallium-drivers= -Dvulkan-drivers=kosmickrisp \
  -Dopengl=false -Dgles1=disabled -Dgles2=disabled -Degl=disabled -Dglx=disabled \
  -Dbuild-tests=false -Dtools= -Dllvm=disabled -Dmesa-clc=system -Dprecomp-compiler=system
ninja -C "$OUT/ios" -j4
find "$OUT/ios" -name '*kosmickrisp*.dylib' -print
