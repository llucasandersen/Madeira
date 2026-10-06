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
