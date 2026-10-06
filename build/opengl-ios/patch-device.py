#!/usr/bin/env python3
"""Port Mesa's Metal device enumeration to iOS without changing capabilities."""
from pathlib import Path
import sys

source = Path(sys.argv[1])
file = source / 'src/kosmickrisp/bridge/mtl_device.m'
text = file.read_text()
old = '      NSArray<id<MTLDevice>> *devs = [MTLCopyAllDevices() autorelease];'
new = '''#if TARGET_OS_IPHONE
      id<MTLDevice> ios_device = [MTLCreateSystemDefaultDevice() autorelease];
      NSArray<id<MTLDevice>> *devs = ios_device ? @[ios_device] : @[];
#else
      NSArray<id<MTLDevice>> *devs = [MTLCopyAllDevices() autorelease];
#endif'''
if new not in text:
    assert text.count(old) == 1, 'Mesa device enumeration changed'
    text = text.replace('#include "mtl_device.h"', '#include "mtl_device.h"\n#include <TargetConditionals.h>', 1)
    file.write_text(text.replace(old, new))
print('Patched iOS device enumeration; Metal4 capability checks retained')

# Mesa's macos platform also selects the generic CAMetalLayer WSI sources.
# iOS supports FIFO presentation, but cannot disable display synchronization.
file = source / 'src/vulkan/wsi/wsi_common_metal.c'
text = file.read_text()
old = '   VK_PRESENT_MODE_IMMEDIATE_KHR,\n'
new = '#if !TARGET_OS_IPHONE\n   VK_PRESENT_MODE_IMMEDIATE_KHR,\n#endif\n'
if new not in text:
    assert text.count(old) == 1, 'Mesa present-mode table changed'
    text = text.replace('#include <assert.h>', '#include <assert.h>\n#include <TargetConditionals.h>', 1)
    file.write_text(text.replace(old, new))

file = source / 'src/vulkan/wsi/wsi_common_metal_layer.m'
text = file.read_text()
if '#include <TargetConditionals.h>' not in text:
    text = text.replace('#import <Metal/Metal.h>', '#import <Metal/Metal.h>\n#include <TargetConditionals.h>', 1)
    assert text.count('metal_layer.displaySyncEnabled = !enable_immediate;') == 2
    text = text.replace('metal_layer.displaySyncEnabled = !enable_immediate;',
                        '#if !TARGET_OS_IPHONE\n   metal_layer.displaySyncEnabled = !enable_immediate;\n#endif')
    old = '      if (metal_layer.device == nil)\n         metal_layer.device = metal_layer.preferredDevice;'
    new = '''      if (metal_layer.device == nil) {
#if TARGET_OS_IPHONE
         metal_layer.device = [MTLCreateSystemDefaultDevice() autorelease];
#else
         metal_layer.device = metal_layer.preferredDevice;
#endif
      }'''
    assert text.count(old) == 1, 'Mesa Metal layer device selection changed'
    file.write_text(text.replace(old, new))
print('Patched iOS Metal WSI: actual surface support, FIFO presentation')
