#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$R"
fetch() {
  local name="$1" pin="$2"
  local directory="$R/research/$name"
  if [ ! -d "$directory/.git" ]; then
    git init "$directory"
    git -C "$directory" remote add origin "https://github.com/KhronosGroup/$name.git"
    git -C "$directory" fetch --depth 1 origin "$pin"
    git -C "$directory" checkout --detach FETCH_HEAD
  fi
  test "$(git -C "$directory" rev-parse HEAD)" = "$pin"
}
fetch Vulkan-Loader f703f919c30c5b67958d35d40a4297cb3823ed78
fetch Vulkan-Headers 9a0f3099c8a9607a7c0f3127d8abfdc19a93e8c5
OUT="$R/build/ci-output/opengl-loader"
cmake -S research/Vulkan-Headers -B "$OUT/headers" -G Ninja \
  -DCMAKE_INSTALL_PREFIX="$OUT/headers-install" -DVULKAN_HEADERS_ENABLE_TESTS=OFF
cmake --build "$OUT/headers" --target install
for target in native ios; do
  args=()
  if [ "$target" = ios ]; then
    args+=(-DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_ARCHITECTURES=arm64)
  fi
  cmake -S research/Vulkan-Loader -B "$OUT/$target" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_DEPLOYMENT_TARGET=26.0 \
    -DCMAKE_PREFIX_PATH="$OUT/headers-install" -DBUILD_TESTS=OFF "${args[@]}"
  cmake --build "$OUT/$target" --target vulkan -j4
  library="$OUT/$target/loader/libvulkan.1.dylib"
  test -s "$library"
  xcrun nm -gU "$library" > "$OUT/$target/exports.txt"
  xcrun otool -L "$library" > "$OUT/$target/dependencies.txt"
  xcrun vtool -show-build "$library" > "$OUT/$target/deployment.txt"
  grep -q '_vkGetInstanceProcAddr' "$OUT/$target/exports.txt"
  grep -q '_vkGetDeviceProcAddr' "$OUT/$target/exports.txt"
done
python3 build/opengl-ios/check-loader.py "$OUT/native/loader/libvulkan.1.dylib" \
  "$R/build/ci-output/opengl-ios/native/src/kosmickrisp/vulkan/libvulkan_kosmickrisp.dylib" \
  > "$OUT/loader-smoke.txt"
cat "$OUT/loader-smoke.txt"
