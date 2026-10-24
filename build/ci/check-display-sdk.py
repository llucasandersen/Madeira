"""Compile the actual display/context adapters using UIKit, not mocked UIKit."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]

def block(text, header):
    start = text.index(header)
    pos = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[pos] == '{') - (text[pos] == '}')
        pos += 1
    return text[start:pos]

display = (root / 'app/Madeira/GuestDisplay.swift').read_text()
fps = block((root / 'app/Madeira/FPSOverlay.swift').read_text(), 'final class ProMotionIntent')
host = block((root / 'app/Madeira/ContentView.swift').read_text(), 'final class MetalHostView')
stubs = '''
import Foundation
import UIKit
import QuartzCore
import Metal
enum MadeiraConfig { static func flag(_ name: String, fallback: Bool = true) -> Bool { fallback } }
func winios_display_mode_changed(_ w: Int32, _ h: Int32) {}
func madeira_set_display_max_fps(_ panel: Int32, _ intent: Int32) {}
func madeira_dxmt_has_display_pacing() -> Int32 { 1 }
enum GamepadEventClaim { static func install(on view: UIView) {} }
final class LogStore { static let shared = LogStore(); func log(_ text: String) {} }
'''
with tempfile.TemporaryDirectory() as temp:
    path = Path(temp) / 'DisplayAdapters.swift'
    path.write_text('\n'.join((stubs, display, fps, host)))
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], text=True).strip()
    subprocess.run(['xcrun', 'swiftc', '-typecheck', '-swift-version', '5', '-sdk', sdk,
                    '-target', 'arm64-apple-ios17.0-simulator', str(path)], check=True)
print('PASS: actual Duo/mirroring window, Metal host and display-link adapters compile with UIKit')
