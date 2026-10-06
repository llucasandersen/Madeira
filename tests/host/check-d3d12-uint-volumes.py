#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile the actual LLVM lowering and exercise public synthetic DXIL containers."""
from pathlib import Path
import shlex
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
code = r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include "llvm/AsmParser/Parser.h"
#include "llvm/Bitcode/BitcodeReader.h"
#include "llvm/Bitcode/BitcodeWriter.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/SourceMgr.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"
using namespace llvm;
extern "C" int madeira_uint_volumes_rewrite(const void*,size_t,void**,size_t*,char*,size_t);
static uint32_t read32(const uint8_t*p) { uint32_t n; memcpy(&n,p,4); return n; }
static void write32(uint8_t*p,uint32_t n) { memcpy(p,&n,4); }
static std::vector<uint8_t> fixture(unsigned kind, bool mixed, bool bindless) {
    std::string ir=R"IR(
%dx.types.Handle = type { i8* }
%dx.types.ResRet.f32 = type { float, float, float, float, i32 }
%class.Texture = type { float }
declare %dx.types.Handle @dx.op.createHandle(i32, i8, i32, i32, i1)
declare %dx.types.ResRet.f32 @dx.op.textureLoad.f32(i32, %dx.types.Handle, i32, i32, i32, i32, i32, i32, i32)
define i32 @main(i32 %index) {
 %h = call %dx.types.Handle @dx.op.createHandle(i32 57, i8 0, i32 0, i32 %index, i1 true)
 %v = call %dx.types.ResRet.f32 @dx.op.textureLoad.f32(i32 66, %dx.types.Handle %h, i32 0, i32 1, i32 2, i32 3, i32 undef, i32 undef, i32 undef)
 %x = extractvalue %dx.types.ResRet.f32 %v, 0
 %raw = bitcast float %x to i32
 %status = extractvalue %dx.types.ResRet.f32 %v, 4
)IR";
    if (mixed) ir += " %math = fadd float %x, 1.0\n %bits = bitcast float %math to i32\n %result = add i32 %raw, %bits\n ret i32 %result\n";
    else ir += " %result = add i32 %raw, %status\n ret i32 %result\n";
    ir += "}\n!dx.resources = !{!0}\n!0 = !{!1, null, null, null}\n!1 = !{!2, !4}\n!2 = !{i32 0, ";
    ir += bindless ? "[131072 x %class.Texture]* undef" : "%class.Texture* undef";
    ir += ", !\"volume\", i32 0, i32 128, i32 "+std::to_string(bindless?131072:1)+", i32 "+std::to_string(kind)+", i32 0, !3}\n";
    // Shared extended properties: lowering must preserve the other 2D resource.
    ir += "!3 = !{i32 0, i32 9}\n!4 = !{i32 1, %class.Texture* undef, !\"float2d\", i32 0, i32 1, i32 1, i32 2, i32 0, !3}\n";
    if(bindless) ir.replace(ir.find("type { float }"),14,"type { <4 x float> }");
    LLVMContext ctx; ctx.setOpaquePointers(false); SMDiagnostic err;
    auto m=parseAssemblyString(ir,err,ctx);
    if (!m) { err.print("fixture",errs()); abort(); }
    assert(!verifyModule(*m));
    SmallVector<char,0> bc; { raw_svector_ostream stream(bc); WriteBitcodeToFile(*m,stream); }
    while(bc.size()%4) bc.push_back(0);
    std::vector<uint8_t> out(36+8+24+bc.size());
    memcpy(out.data(),"DXBC",4); write32(out.data()+20,1); write32(out.data()+24,out.size());
    write32(out.data()+28,1); write32(out.data()+32,36); memcpy(out.data()+36,"DXIL",4);
    write32(out.data()+40,24+bc.size()); write32(out.data()+48,(24+bc.size())/4);
    memcpy(out.data()+52,"DXIL",4); write32(out.data()+56,0x100); write32(out.data()+60,16); write32(out.data()+64,bc.size());
    memcpy(out.data()+68,bc.data(),bc.size()); return out;
}
static void check(const std::vector<uint8_t>&input, bool changed, bool bindless=false) {
    void *out=nullptr; size_t len=0; char note[160];
    int result=madeira_uint_volumes_rewrite(input.data(),input.size(),&out,&len,note,sizeof note);
    assert(result==(changed?1:0));
    if (!changed) { assert(!out && !len); return; }
    assert(out && len>=68 && strstr(note,"integer texture reads"));
    auto *p=static_cast<uint8_t*>(out); assert(read32(p+24)==len);
    auto off=read32(p+32); auto size=read32(p+off+28);
    LLVMContext ctx; ctx.setOpaquePointers(false);
    auto memory=MemoryBuffer::getMemBuffer(StringRef(reinterpret_cast<char*>(p+off+32),size),"test",false);
    auto parsed=parseBitcodeFile(memory->getMemBufferRef(),ctx); assert(bool(parsed));
    auto &m=**parsed; assert(!verifyModule(m));
    std::string text; { raw_string_ostream stream(text); m.print(stream,nullptr); }
    assert(text.find("call %dx.types.ResRet.i32 @dx.op.textureLoad.i32")!=std::string::npos);
    assert(text.find("call %dx.types.ResRet.f32 @dx.op.textureLoad.f32")==std::string::npos);
    assert(text.find("bitcast float")==std::string::npos);
    assert(text.find("extractvalue %dx.types.ResRet.i32")!=std::string::npos);
    auto *resources=cast<MDNode>(m.getNamedMetadata("dx.resources")->getOperand(0)->getOperand(0));
    auto *volume=cast<MDNode>(resources->getOperand(0)); auto *other=cast<MDNode>(resources->getOperand(1));
    auto component=[](MDNode *r) { return cast<ConstantInt>(cast<ConstantAsMetadata>(cast<MDNode>(r->getOperand(8))->getOperand(1))->getValue())->getZExtValue(); };
    assert(component(volume)==5 && component(other)==9);
    auto *type=cast<ConstantAsMetadata>(volume->getOperand(1))->getValue()->getType()->getPointerElementType();
    if(bindless) { assert(cast<ArrayType>(type)->getNumElements()==131072); type=cast<ArrayType>(type)->getElementType(); }
    auto *element=cast<StructType>(type)->getElementType(0);
    if(bindless) { assert(cast<FixedVectorType>(element)->getNumElements()==4); element=cast<FixedVectorType>(element)->getElementType(); }
    assert(element->isIntegerTy(32));
    // Idempotence prevents rewriting already integer declarations.
    void *again=nullptr; size_t n=0;
    assert(madeira_uint_volumes_rewrite(out,len,&again,&n,note,sizeof note)==0 && !again && !n);
    free(out);
}
int main() {
    check(fixture(4,false,false),true);
    check(fixture(4,false,true),true,true);
    check(fixture(4,true,false),false);
    check(fixture(2,false,false),false);
    auto valid=fixture(4,false,false);
    for(size_t n=0;n<valid.size();n++) {
        void *out=nullptr; size_t len=0; char note[8];
        assert(madeira_uint_volumes_rewrite(valid.data(),n,&out,&len,note,sizeof note)<=0 && !out && !len);
    }
    auto corrupt=valid; write32(corrupt.data()+32,UINT32_MAX); check(corrupt,false);
    puts("PASS: actual production LLVM pass, scalar/bindless UINT volumes, status, typed declarations, shared metadata, float/2D rejection, idempotence and every truncated input under ASan/UBSan");
}
'''
flags = shlex.split(subprocess.check_output(['llvm-config-15', '--cxxflags'], text=True))
libraries = shlex.split(subprocess.check_output(['llvm-config-15', '--ldflags', '--system-libs', '--libs', 'core', 'bitreader', 'bitwriter', 'asmparser'], text=True))
with tempfile.TemporaryDirectory(prefix='madeira-uint-volumes-') as folder:
    path = Path(folder)
    (path/'test.cpp').write_text(code)
    subprocess.run(['clang++-15', *flags, '-std=c++17', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(root/'madeira-d3d12/src/unix/madeira_uint_volumes.cpp'), str(path/'test.cpp'), *libraries, '-o', str(path/'test')], check=True)
    subprocess.run([str(path/'test')], check=True)
