#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Compile the production renderer adapter and exercise real file preservation."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
production = (root / 'app/Madeira/GameCompatibility.swift').read_text(encoding='utf-8')
fixture = r'''
func check(_ condition: @autoclosure () -> Bool) { precondition(condition()) }
func rejects(_ text: String, line: UInt = #line) {
    do { _ = try TeardownRendererSettings.selectingD3D12(Data(text.utf8)); preconditionFailure("accepted invalid XML fixture line \(line)") }
    catch { }
}
let source = """
<?xml version="1.0" encoding="UTF-8"?>
<registry version="2.1.0">
  <options><gfx><gfxapi value="0"/><d3d12support value='0'/><quality value="3"/></gfx>
  <audio><musicvolume value="93"/></audio><input><label value="船 &amp; é"/></input></options>
</registry>
""".replacingOccurrences(of: "\n", with: "\r\n")
let selected = source.replacingOccurrences(of: "gfxapi value=\"0\"", with: "gfxapi value=\"1\"")
    .replacingOccurrences(of: "d3d12support value='0'", with: "d3d12support value='1'")
let original = Data(source.utf8)
check(try! TeardownRendererSettings.selectingD3D12(original) == Data(selected.utf8))
check(try! TeardownRendererSettings.selectingD3D12(Data(selected.utf8)) == Data(selected.utf8))
check(GameCompatibilityProfile.resolve(appID: 3527290) == nil)
check(GameCompatibilityProfile.resolve(appID: 1167630, enabled: false) == nil)
let policy = GameCompatibilityProfile.resolve(appID: 1167630)!
check(policy.preferredRenderer == .d3d12 && policy.revision == 4)
check(GameCompatibilityProfile.resolve(appID: 1167630, openGLAvailable: true, openGLVersion: 21)!.preferredRenderer == .d3d12)
check(GameCompatibilityProfile.resolve(appID: 1167630, openGLAvailable: true, openGLVersion: 44)!.preferredRenderer == .d3d12)
check(GameCompatibilityProfile.resolve(appID: 1167630, openGLAvailable: false, openGLVersion: 45)!.preferredRenderer == .d3d12)
let openGLPolicy = GameCompatibilityProfile.resolve(appID: 1167630, openGLAvailable: true, openGLVersion: 45)!
check(openGLPolicy.preferredRenderer == .opengl && openGLPolicy.revision == 3)
check(GameCompatibilityProfile.resolve(appID: 1167630, enabled: false, openGLAvailable: true) == nil)
check(GameCompatibilityProfile.resolve(appID: 1174180, openGLAvailable: true)!.preferredRenderer == .d3d12)
check(openGLPolicy.runtimeConfig(user: nil, global: [:]) == "env.MADEIRA_OPENGL = 1\nenv.WINEDLLOVERRIDES = opengl32=n,b\n")
check(openGLPolicy.runtimeConfig(user: "pool=64", global: ["env.WINEDLLOVERRIDES": "foo=n"]) == "pool=64\nenv.MADEIRA_OPENGL = 1\nenv.WINEDLLOVERRIDES = foo=n;opengl32=n,b\n")
check(openGLPolicy.runtimeConfig(user: "env.WINEDLLOVERRIDES=bar=b", global: ["env.WINEDLLOVERRIDES": "foo=n"]) == "env.WINEDLLOVERRIDES=bar=b\nenv.MADEIRA_OPENGL = 1\nenv.WINEDLLOVERRIDES = bar=b;opengl32=n,b\n")
let dx12XML = try TeardownRendererSettings.selectingD3D12(Data(source.utf8))
let glXML = try TeardownRendererSettings.selectingOpenGL(dx12XML)
check(String(decoding: glXML, as: UTF8.self) == String(decoding: dx12XML, as: UTF8.self).replacingOccurrences(of: "<gfxapi value=\"1\"/>", with: "<gfxapi value=\"0\"/>"))
let glXMLAgain = try TeardownRendererSettings.selectingOpenGL(glXML)
check(glXMLAgain == glXML)
check(policy.runtimeConfig(user: nil, global: [:]) == "msc-uint-volume-loads = 1\n")
check(policy.runtimeConfig(user: "pool = 32", global: [:]) == "msc-uint-volume-loads = 1\npool = 32")
check(policy.runtimeConfig(user: "msc-uint-volume-loads = 0", global: [:]) == "msc-uint-volume-loads = 0")
check(policy.runtimeConfig(user: "  msc-uint-volume-loads=0\r\npool=64", global: [:]) == "  msc-uint-volume-loads=0\r\npool=64")
check(policy.runtimeConfig(user: nil, global: ["msc-uint-volume-loads": "0"]) == nil)
check(policy.runtimeConfig(user: "pool=64", global: ["msc-uint-volume-loads": "1"]) == "pool=64")
let rdrPolicy = GameCompatibilityProfile.resolve(appID: 1174180)!
let conservativeCPU = "env.FEX_MULTIBLOCK = 0\nenv.FEX_MAXINST = 1\n"
let memoryTier = "swap-mb = 4096\nenv.MADEIRA_SWAP_COVERAGE = broad\n"
let defaults = conservativeCPU + memoryTier
check(rdrPolicy.revision == 4)
check(rdrPolicy.runtimeConfig(user: nil, global: [:]) == defaults + "vram-mb = 2048\n")
check(rdrPolicy.runtimeConfig(user: nil, global: ["vram-mb": "0"]) == defaults + "vram-mb = 2048\n")
check(rdrPolicy.runtimeConfig(user: nil, global: ["vram-mb": "3072"]) == defaults)
check(rdrPolicy.runtimeConfig(user: "vram-mb=1536", global: [:]) == defaults + "vram-mb=1536")
check(rdrPolicy.runtimeConfig(user: "vram-mb=0", global: ["vram-mb": "3072"]) == defaults + "vram-mb=0\nvram-mb = 2048\n")
check(rdrPolicy.runtimeConfig(user: "vram-mb=0\nvram-mb=4096", global: [:]) == defaults + "vram-mb=0\nvram-mb=4096")
check(rdrPolicy.runtimeConfig(user: "vram-mb=invalid", global: [:]) == defaults + "vram-mb=invalid")
let explicitCPU = "  env.FEX_MULTIBLOCK=1\r\nenv.FEX_MAXINST=32\nswap-mb=0\nenv.MADEIRA_SWAP_COVERAGE=classic\nvram-mb=1536"
check(rdrPolicy.runtimeConfig(user: explicitCPU, global: [:]) == explicitCPU)
check(rdrPolicy.runtimeConfig(user: nil, global: ["env.FEX_MULTIBLOCK": "1", "env.FEX_MAXINST": "32", "vram-mb": "3072", "swap-mb": "0", "env.MADEIRA_SWAP_COVERAGE": "classic"]) == nil)
check(rdrPolicy.runtimeConfig(user: "env.FEX_MULTIBLOCK=0\nvram-mb=1536", global: [:]) == "env.FEX_MAXINST = 1\n" + memoryTier + "env.FEX_MULTIBLOCK=0\nvram-mb=1536")
check(rdrPolicy.runtimeConfig(user: "env.FEX_MAXINST=1\nvram-mb=1536", global: ["env.FEX_MULTIBLOCK": "0"]) == memoryTier + "env.FEX_MAXINST=1\nvram-mb=1536")
check(rdrPolicy.runtimeConfig(user: "swap-mb=0\nvram-mb=1536", global: ["env.MADEIRA_SWAP_COVERAGE": "classic"]) == conservativeCPU + "swap-mb=0\nvram-mb=1536")
check(rdrPolicy.runtimeConfig(user: "swap-mb=2048\nenv.MADEIRA_SWAP_COVERAGE=blocks\nvram-mb=1536", global: [:]) == conservativeCPU + "swap-mb=2048\nenv.MADEIRA_SWAP_COVERAGE=blocks\nvram-mb=1536")
check(rdrPolicy.runtimeConfig(user: "swap-mb=0\nswap-mb=3072\nvram-mb=1536", global: [:]) == conservativeCPU + "env.MADEIRA_SWAP_COVERAGE = broad\nswap-mb=0\nswap-mb=3072\nvram-mb=1536")
rejects(source.replacingOccurrences(of: "2.1.0", with: "99.0"))
rejects(source.replacingOccurrences(of: "<gfxapi value=\"0\"/>", with: ""))
rejects(source.replacingOccurrences(of: "<gfxapi value=\"0\"/>", with: "<gfxapi value=\"0\"/><gfxapi value=\"1\"/>"))
rejects(source.replacingOccurrences(of: "<gfxapi value=\"0\"/>", with: "<gfxapi value=\"2\"/>"))
rejects(source.replacingOccurrences(of: "<gfxapi value=\"0\"/>", with: "<gfxapi value=\"0\" evil=\"yes\"/>"))
rejects(source.replacingOccurrences(of: "</options>", with: "<other><gfxapi value=\"0\"/></other></options>"))
rejects(source.replacingOccurrences(of: "<gfxapi value=\"0\"/>", with: "<!-- <gfxapi value=\"0\"/> --><gfxapi value=\"0\"></gfxapi>"))
rejects(source + "<!-- <gfxapi value=\"0\"/> -->")
rejects(source.replacingOccurrences(of: "<gfxapi value=\"0\"/>", with: "<?hint <gfxapi value=\"0\"/> ?><gfxapi value=\"0\"></gfxapi>"))
rejects("<!DOCTYPE registry [<!ENTITY x SYSTEM 'file:///private/file'>]>" + source)
rejects(source.replacingOccurrences(of: "<quality value=\"3\"/>", with: "<![CDATA[<gfxapi value=\"0\"/>]]>"))
rejects(source.replacingOccurrences(of: "</registry>", with: ""))
rejects(String(repeating: "x", count: 1_048_577))
let fm = FileManager.default
let directory = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString).resolvingSymlinksInPath()
try fm.createDirectory(at: directory, withIntermediateDirectories: true)
defer { try? fm.removeItem(at: directory) }
let file = directory.appendingPathComponent("options.xml")
check(try! policy.prepare(options: file) == false && !fm.fileExists(atPath: file.path))
try original.write(to: file)
check(try! policy.prepare(options: file))
let backup = directory.appendingPathComponent("options.xml.madeira-renderer-backup")
check(try! Data(contentsOf: backup) == original)
check(try! Data(contentsOf: file) == Data(selected.utf8))
check(try! policy.prepare(options: file) == false)
try original.write(to: file)
check(try! policy.prepare(options: file))
check(try! Data(contentsOf: backup) == original)
let unsupported = Data(source.replacingOccurrences(of: "2.1.0", with: "3.0").utf8)
try unsupported.write(to: file)
do { _ = try policy.prepare(options: file); preconditionFailure() } catch { }
check(try! Data(contentsOf: file) == unsupported)
try fm.removeItem(at: file)
let target = directory.appendingPathComponent("other.xml")
try original.write(to: target)
try fm.createSymbolicLink(at: file, withDestinationURL: target)
do { _ = try policy.prepare(options: file); preconditionFailure() } catch { }
check(try! Data(contentsOf: target) == original)
let rdr = "<rage__fwuiSystemSettingsCollection><version value=\"37\"/><advancedGraphics><API>kSettingAPI_Vulkan</API><asyncComputeEnabled value=\"true\"/></advancedGraphics><audio><volume value=\"7\"/></audio></rage__fwuiSystemSettingsCollection>"
check(RDR2RendererSettings.initialArguments("") == "-dx12")
check(RDR2RendererSettings.initialArguments("-windowed") == "-windowed -dx12")
check(RDR2RendererSettings.initialArguments("-DX12") == "-DX12")
check(RDR2RendererSettings.initialArguments("-vulkan") == "-vulkan")
check(RDR2RendererSettings.initialArguments("\"-dx11\"") == "\"-dx11\"")
check(RDR2RendererSettings.requestsD3D12("-DX12"))
check(!RDR2RendererSettings.requestsD3D12("-vulkan"))
check(RDR2RendererSettings.requestsD3D12("-windowed \"-DX12\""))
check(!RDR2RendererSettings.requestsD3D12("-dx12 -vulkan"))
check(!RDR2RendererSettings.requestsD3D12("-dx11 -dx12"))
let rdrSelected = rdr.replacingOccurrences(of: "kSettingAPI_Vulkan", with: "kSettingAPI_DX12")
check(try! RDR2RendererSettings.selectingD3D12(Data(rdr.utf8)) == Data(rdrSelected.utf8))
check(try! RDR2RendererSettings.selectingD3D12(Data(rdrSelected.utf8)) == Data(rdrSelected.utf8))
check(GameCompatibilityProfile.resolve(appID: 1174180)?.settingsAdapter == .rdr2System)
for invalid in [rdr.replacingOccurrences(of: "</advancedGraphics>", with: "<API>kSettingAPI_DX12</API></advancedGraphics>"),
                rdr.replacingOccurrences(of: "advancedGraphics", with: "other"),
                rdr.replacingOccurrences(of: "kSettingAPI_Vulkan", with: "unknown"),
                "<!DOCTYPE x>" + rdr] {
    do { _ = try RDR2RendererSettings.selectingD3D12(Data(invalid.utf8)); preconditionFailure() } catch { }
}
let rdrFile = directory.appendingPathComponent("system.xml")
check(try! RDR2RendererSettings.prepare(file: rdrFile) == false)
try Data(rdr.utf8).write(to: rdrFile)
check(try! RDR2RendererSettings.prepare(file: rdrFile))
check(try! Data(contentsOf: directory.appendingPathComponent("system.xml.madeira-renderer-backup")) == Data(rdr.utf8))
check(try! RDR2RendererSettings.prepare(file: rdrFile) == false)
let rdrExe = directory.appendingPathComponent("RDR2.exe")
check(!RDR2RendererSettings.isGame(executable: rdrExe))
for name in ["common_0.rpf", "shaders_x64.rpf", "bink2w64.dll"] { try Data().write(to: directory.appendingPathComponent(name)) }
check(RDR2RendererSettings.isGame(executable: rdrExe))
check(!RDR2RendererSettings.isGame(executable: directory.appendingPathComponent("other.exe")))
print("PASS: Teardown and RDR2 actual profile adapters; exact edits, backups, preservation, malformed XML, symlink refusal, direct executable identity, generic and disabled profiles")
'''
content = (root / 'app/Madeira/ContentView.swift').read_text(encoding='utf-8')
start = content[content.index('private func startDock('):]
assert start.index('cloudClear(') < start.index('compatibility.prepare(options:') < start.index('runWineFullSequence(profile:')
assert start.index('wine_process_is_running() == 0', start.index('await SteamOwnedLibrary.shared.prepareDock()')) < start.index('compatibility.prepare(options:')
assert 'enabled: profile?.automaticCompatibility != false' in start
assert 'runWineFullSequence(profile: profile, compatibilityAppID: game.id)' in start
run = content[content.index('private func runWineFullSequence('):content.index('private func startDock(')]
assert run.index('MadeiraConfig.applyGame(nil)') < run.index('compatibilityAppID,') < run.index('StikJITHelper.allocatePool(')
assert 'runtimeConfig(user: profile?.config, global: MadeiraConfig.all())' in run
project = (root / 'app/Madeira.xcodeproj/project.pbxproj').read_text()
assert project.count('A1F0FF01 /* GameCompatibility.swift in Sources */') == 2
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)
    (path / 'main.swift').write_text(production + '\n' + fixture, encoding='utf-8')
    subprocess.run(['swiftc', str(path / 'main.swift'), '-o', str(path / 'check')], check=True)
    subprocess.run([str(path / 'check')], check=True)
    debug_fixture = r'''
let profile = GameCompatibilityProfile.resolve(appID: 1174180)!
let conservativeCPU = "env.FEX_MULTIBLOCK = 0\nenv.FEX_MAXINST = 1\nswap-mb = 4096\nenv.MADEIRA_SWAP_COVERAGE = broad\n"
precondition(profile.runtimeConfig(user: nil, global: [:]) == conservativeCPU + "vram-mb = 2048\n")
precondition(profile.runtimeConfig(user: "vram-mb=1536", global: [:]) == conservativeCPU + "vram-mb=1536")
precondition(profile.runtimeConfig(user: "env.MADEIRA_JIT_DUMP_AFTER_SECONDS=120\nvram-mb=1536", global: [:]) == conservativeCPU + "env.MADEIRA_JIT_DUMP_AFTER_SECONDS=120\nvram-mb=1536")
precondition(profile.runtimeConfig(user: nil, global: ["env.MADEIRA_JIT_DUMP_AFTER_SECONDS": "0", "vram-mb": "3072"]) == conservativeCPU)
precondition(GameCompatibilityProfile.resolve(appID: 1167630)!.runtimeConfig(user: nil, global: [:]) == "msc-uint-volume-loads = 1\n")
'''
    (path / 'main.swift').write_text(production + '\n' + debug_fixture, encoding='utf-8')
    subprocess.run(['swiftc', '-D', 'DEBUG', str(path / 'main.swift'), '-o', str(path / 'debug-check')], check=True)
    subprocess.run([str(path / 'debug-check')], check=True)
print('PASS: production renderer policies, settings preservation, conservative RDR2 CPU defaults and opt-in late capture')
