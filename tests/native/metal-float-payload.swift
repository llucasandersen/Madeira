// SPDX-License-Identifier: GPL-3.0-or-later
// Probe integer payloads transported through R32Float texture loads.
import Foundation
import Metal

guard let device = MTLCreateSystemDefaultDevice(), let queue = device.makeCommandQueue() else {
    print("METAL_PAYLOAD_PROBE_UNAVAILABLE: no Metal device/queue")
    exit(77)
}
let payloads: [UInt32] = [0, 1, 2, 255, 4095, 0x007fffff, 0x00800000, 0x3f800000, 0x7fc00001, 0xffc00001]
let code = """
#include <metal_stdlib>
using namespace metal;
kernel void probe(texture3d<float, access::read> floats [[texture(0)]],
                  texture3d<uint, access::read> integers [[texture(1)]],
                  device uint2 *out [[buffer(0)]], uint i [[thread_position_in_grid]]) {
    out[i] = uint2(as_type<uint>(floats.read(uint3(i,0,0)).x), integers.read(uint3(i,0,0)).x);
}
"""
let opts = MTLCompileOptions()
opts.fastMathEnabled = false
let lib = try device.makeLibrary(source: code, options: opts)
let pipeline = try device.makeComputePipelineState(function: lib.makeFunction(name: "probe")!)
func texture(_ format: MTLPixelFormat) -> MTLTexture {
    let desc = MTLTextureDescriptor()
    desc.textureType = .type3D
    desc.pixelFormat = format
    desc.width = payloads.count
    desc.height = 1
    desc.depth = 1
    desc.storageMode = device.hasUnifiedMemory ? .shared : .managed
    desc.usage = .shaderRead
    let texture = device.makeTexture(descriptor: desc)!
    payloads.withUnsafeBytes { ptr in
        texture.replace(region: MTLRegionMake3D(0, 0, 0, payloads.count, 1, 1), mipmapLevel: 0,
                        slice: 0, withBytes: ptr.baseAddress!, bytesPerRow: payloads.count * 4,
                        bytesPerImage: payloads.count * 4)
    }
    return texture
}
let floats = texture(.r32Float), integers = texture(.r32Uint)
let output = device.makeBuffer(length: payloads.count * 8, options: .storageModeShared)!
let cb = queue.makeCommandBuffer()!, enc = cb.makeComputeCommandEncoder()!
enc.setComputePipelineState(pipeline)
enc.setTexture(floats, index: 0); enc.setTexture(integers, index: 1)
enc.setBuffer(output, offset: 0, index: 0)
enc.dispatchThreads(MTLSize(width: payloads.count, height: 1, depth: 1),
                    threadsPerThreadgroup: MTLSize(width: payloads.count, height: 1, depth: 1))
enc.endEncoding(); cb.commit(); cb.waitUntilCompleted()
guard cb.status == .completed else { fatalError("Metal probe failed: \(String(describing: cb.error))") }
let words = output.contents().bindMemory(to: UInt32.self, capacity: payloads.count * 2)
print("METAL_PAYLOAD_PROBE device=\(device.name) fastMath=false native MSL (not MSC)")
for i in payloads.indices {
    print(String(format: "input=%08x float-load=%08x uint-load=%08x", payloads[i], words[i*2], words[i*2+1]))
    guard words[i*2+1] == payloads[i] else { fatalError("Integer texture control lost data") }
}
