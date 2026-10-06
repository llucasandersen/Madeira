#!/usr/bin/env python3
"""Exercise the production OpenGL launch counter and failed-present filter."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
wine = (root / 'wine/dlls/win32u/vulkan.c').read_text()
assert wine.count('client_surface_present( surface->client );') == 1
present = wine[wine.index('static VkResult win32u_vkQueuePresentKHR('):]
assert present.index('res = device->p_vkQueuePresentKHR(') < present.index('VkResult swapchain_res =') < present.index('client_surface_present( surface->client );')
loader = (root / 'build/win32u-unix/vulkan_loader_ios.c').read_text()
assert loader.index('#include "ntgdi_private.h"') < loader.index('#include "vulkan_present_ios.h"') < loader.index('#include "../../wine/dlls/win32u/vulkan.c"')
surface = (root / 'build/win32u-unix/vulkan_surface_ios.c').read_text()
assert re.search(r'static void surface_present[^}]+madeira_vulkan_note_present\(\);', surface)
assert '!madeira_vulkan_note_present' in surface
for name in ('ContentView.swift', 'Library.swift', 'MadeiraDock.swift', 'FPSOverlay.swift'):
    text = (root / 'app/Madeira' / name).read_text(encoding='utf-8')
    assert 'madeira_get_game_present_count()' in text
    assert 'madeira_get_present_count()' not in text

shim = (root / 'app/Madeira/IOSDisplayShim.m').read_text(encoding='utf-8')
counter = shim[shim.index('static uint64_t g_vulkan_present_count;'):shim.index('const char *madeira_vulkan_library_path(')]
harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <pthread.h>
static uint64_t d3d_presents = 7;
uint64_t madeira_get_present_count(void) { return d3d_presents; }
COUNTER
struct client_surface { int unused; };
static void client_surface_present(struct client_surface *client) {
    (void)client; madeira_vulkan_note_present();
}
#include "vulkan_present_ios.h"
static void submit(int swapchain_res) {
    struct client_surface client = {0};
    client_surface_present(&client);
}
static void *worker(void *unused) {
    (void)unused;
    for (int i = 0; i < 10000; ++i) submit(0);
    return NULL;
}
int main(void) {
    assert(madeira_get_game_present_count() == 7);
    submit(-1); submit(-1000001004); // failure and out-of-date
    assert(madeira_get_game_present_count() == 7);
    submit(0); submit(1000001003); // success and suboptimal
    assert(madeira_get_game_present_count() == 9);
    pthread_t threads[4];
    for (int i = 0; i < 4; ++i) assert(!pthread_create(&threads[i], NULL, worker, NULL));
    for (int i = 0; i < 4; ++i) assert(!pthread_join(threads[i], NULL));
    assert(madeira_get_game_present_count() == 40009);
    d3d_presents += 3;
    assert(madeira_get_game_present_count() == 40012);
    submit(-4); assert(madeira_get_game_present_count() == 40012);
    return 0;
}
'''.replace('COUNTER', counter)
compiler = os.environ.get('CC') or shutil.which('clang') or shutil.which('cc')
assert compiler, 'A host C compiler is required'
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    source = path / 'present.c'
    source.write_text(harness)
    binary = path / ('present.exe' if os.name == 'nt' else 'present')
    subprocess.run([compiler, '-std=c11', '-pthread', '-Wall', '-Wextra', '-Werror',
                    '-I', str(root / 'build/win32u-unix'), str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True, capture_output=True)
print('PASS: failed Vulkan presents cannot dismiss launch UI; concurrent GL and D3D counters combine without lost frames')
