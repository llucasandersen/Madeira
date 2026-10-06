#!/usr/bin/env python3
"""Exercise the actual Wine argument parser and RDR2 handoff helper under ASan/UBSan."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/process_ios.c').read_text(encoding='utf-8')
def function(signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2]

create = function('NTSTATUS WINAPI NtCreateUserProcess(')
assert create.index('ios_rdr2_renderer_command( params') < create.index('create_startup_info(')
assert create.index('params = &renderer_params') < create.index('spawn_process(')
assert 'free( renderer_command );' in create[create.index('done:'):]
library = (root / 'app/Madeira/Library.swift').read_text(encoding='utf-8')
launch = library[library.index('func configureLaunch()'):library.index('final class LibraryModel')]
assert launch.index('unsetenv("MADEIRA_RDR2_DX12")') < launch.index('if steamAppID != nil')
assert 'automaticCompatibility != false' in launch and 'RDR2RendererSettings.isGame(executable: executable)' in launch

code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
typedef uint16_t WCHAR;
typedef uint32_t NTSTATUS;
typedef struct { uint16_t Length, MaximumLength; WCHAR *Buffer; } UNICODE_STRING;
typedef struct { UNICODE_STRING ImagePathName, CommandLine; } RTL_USER_PROCESS_PARAMETERS;
#define FALSE 0
#define STATUS_SUCCESS 0
#define STATUS_NO_MEMORY 0xc0000017u
#define STATUS_INVALID_PARAMETER 0xc000000du
static int calls, fail_at;
static void *probe_malloc(size_t size) { if (++calls == fail_at) return NULL; return malloc(size); }
#define malloc probe_malloc
/* The production parser handles quoting. This stub only transcodes ASCII test fixtures. */
static int ntdll_wcstoumbs(const WCHAR *src, int len, char *dst, int capacity, int strict)
{ (void)strict; assert(capacity >= len); for(int i=0;i<len;i++) { assert(src[i]<128); dst[i]=(char)src[i]; } return len; }
''' + function('static char **build_argv(') + '\n' + function('static NTSTATUS ios_rdr2_renderer_command(') + r'''
#undef malloc
static UNICODE_STRING wide(const char *text)
{
    size_t len=strlen(text); assert(len <= 32766);
    WCHAR *data=calloc(len+1,sizeof(*data)); assert(data);
    for(size_t i=0;i<len;i++) data[i]=(unsigned char)text[i];
    return (UNICODE_STRING){len*2,(len+1)*2,data};
}
static void check(const char *image,const char *command,const char *flag,const char *expected)
{
    if(flag) setenv("MADEIRA_RDR2_DX12",flag,1); else unsetenv("MADEIRA_RDR2_DX12");
    RTL_USER_PROCESS_PARAMETERS p={wide(image),wide(command)}, saved=p;
    WCHAR *out=(void*)1; calls=0; fail_at=0;
    assert(ios_rdr2_renderer_command(&p,&out)==STATUS_SUCCESS);
    assert(!memcmp(&p,&saved,sizeof(p)));
    if(expected) { UNICODE_STRING wanted=wide(expected); assert(out && !memcmp(out,wanted.Buffer,wanted.MaximumLength)); free(wanted.Buffer); }
    else assert(!out);
    free(out); free(p.ImagePathName.Buffer); free(p.CommandLine.Buffer);
}
int main(void)
{
    check("C:\\Games\\RDR2.exe","\"C:\\Games\\RDR2.exe\" -windowed","1","\"C:\\Games\\RDR2.exe\" -windowed -dx12");
    check("rDr2.ExE","RDR2.exe","1","RDR2.exe -dx12");
    check("RDR2.exe","RDR2.exe \"-DX12\"","1",NULL);
    check("RDR2.exe","RDR2.exe \"-VULKAN\"","1",NULL);
    check("RDR2.exe","RDR2.exe -dx11","1",NULL);
    check("RDR2.exe","RDR2.exe -dx10","1",NULL);
    check("RDR2.exe","RDR2.exe -dx9","1",NULL);
    check("RDR2.exe","RDR2.exe -config \"folder -vulkan\"","1","RDR2.exe -config \"folder -vulkan\" -dx12");
    check("RDR2.exe","RDR2.exe -config \"a\\\"b\"","1","RDR2.exe -config \"a\\\"b\" -dx12");
    check("Launcher.exe","Launcher.exe","1",NULL);
    check("NotRDR2.exe","NotRDR2.exe","1",NULL);
    check("RDR2.exe","RDR2.exe",NULL,NULL);
    check("RDR2.exe","RDR2.exe","0",NULL);
    check("RDR2.exe","RDR2.exe","yes",NULL);
    setenv("MADEIRA_RDR2_DX12","1",1);
    RTL_USER_PROCESS_PARAMETERS p={wide("RDR2.exe"),wide("RDR2.exe")}; WCHAR *out;
    for(int fault=1;fault<=3;fault++) { calls=0;fail_at=fault;assert(ios_rdr2_renderer_command(&p,&out)==STATUS_NO_MEMORY && !out); }
    fail_at=0;p.CommandLine.Length=1;assert(ios_rdr2_renderer_command(&p,&out)==STATUS_INVALID_PARAMETER && !out);
    free(p.CommandLine.Buffer);
    p.CommandLine.Buffer=calloc(32768,sizeof(WCHAR));assert(p.CommandLine.Buffer);
    for(int i=0;i<32767;i++) p.CommandLine.Buffer[i]='x';
    p.CommandLine.Length=65534;
    assert(ios_rdr2_renderer_command(&p,&out)==STATUS_INVALID_PARAMETER && !out);
    free(p.ImagePathName.Buffer);free(p.CommandLine.Buffer);
    puts("PASS: production RDR2 handoff, quoted renderer overrides, game isolation, opt-out, caller preservation, length bounds and allocation failures");
}
'''
compiler = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang')
if not compiler:
    raise SystemExit('Host C compiler required; run the runtime lifecycle workflow.')
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)
    (path / 'probe.c').write_text(code)
    subprocess.run([compiler, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-fno-sanitize-recover=all', str(path / 'probe.c'), '-o', str(path / 'probe')], check=True, timeout=60)
    subprocess.run([str(path / 'probe')], check=True, timeout=30,
                   env=dict(os.environ, ASAN_OPTIONS='detect_leaks=' + ('0' if sys.platform == 'darwin' else '1')))
