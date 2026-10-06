#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$R"
bash build/ci/fetch-mingw.sh
export PATH="$(brew --prefix bison)/bin:$R/toolchains/llvm-mingw-20260421-ucrt-macos-universal/bin:$PATH"
export CC="$(xcrun --find clang)"
mkdir -p wine/build-macos
(cd wine/build-macos && ../configure --enable-archs=aarch64 --without-x --disable-tests)
make -C wine/build-macos -j4 include/all
OUT="$R/build/ci-output/opengl-wine-bridge"
mkdir -p "$OUT"
FLAGS=(-arch arm64 -isysroot "$(xcrun --sdk iphoneos --show-sdk-path)"
  -miphoneos-version-min=17.0 -O2 -fPIC -fvisibility=hidden
  -fno-stack-protector -fno-strict-aliasing -D__WINESRC__ -DWINE_UNIX_LIB -DWINE_IOS=1
  -D_ACRTIMP= -DWINBASEAPI=
  -I"$R/wine/build-macos/include" -I"$R/wine/include")
for name in vulkan vulkan_thunks; do
  xcrun -sdk iphoneos clang "${FLAGS[@]}" -include "$R/wine/build-macos/include/config.h" \
    -D__wine_unix_call_funcs=winevulkan_unix_call_funcs \
    -D__wine_unix_call_wow64_funcs=winevulkan_unix_call_wow64_funcs \
    -c "wine/dlls/winevulkan/$name.c" -o "$OUT/winevulkan_$name.o"
done
for name in vulkan_loader_ios vulkan_surface_ios driver_ios; do
  xcrun -sdk iphoneos clang "${FLAGS[@]}" -include "$R/build/win32u-unix/config_ios.h" \
    -I"$R/build/ntdll-unix/shims" -I"$R/build/win32u-unix" \
    -I"$R/wine/dlls/win32u" -I"$R/wine/build-macos/dlls/win32u" \
    -DSYSTEMDLLPATH=\"\" \
    -c "build/win32u-unix/$name.c" -o "$OUT/$name.o"
done
xcrun -sdk iphoneos clang -arch arm64 -isysroot "$(xcrun --sdk iphoneos --show-sdk-path)" \
  -miphoneos-version-min=17.0 -fobjc-arc -O2 \
  -c app/Madeira/IOSDisplayShim.m -o "$OUT/IOSDisplayShim.o"
xcrun nm -g "$OUT"/*.o > "$OUT/symbols.txt"
grep -q 'winevulkan_unix_call_funcs' "$OUT/symbols.txt"
grep -q 'winevulkan_unix_call_wow64_funcs' "$OUT/symbols.txt"
grep -q 'winios_VulkanInit' "$OUT/symbols.txt"
echo 'PASS: actual Wine Vulkan thunks, native loader, iOS surfaces and display bridge compile for iPhone'
