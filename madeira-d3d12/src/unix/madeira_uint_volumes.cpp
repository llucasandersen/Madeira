// SPDX-License-Identifier: GPL-3.0-or-later
// Opt-in integer volume payload lowering. No game bytecode or names are used.
// Some D3D shaders declare Texture3D<float>, bind a UINT volume, and immediately
// asuint every load. Metal needs an integer texture declaration for that view.
// Reject a resource if ANY handle use performs floating point work or sampling.
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <vector>
#include "llvm/Bitcode/BitcodeReader.h"
#include "llvm/Bitcode/BitcodeWriter.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/Metadata.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/Error.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/Support/raw_ostream.h"
using namespace llvm;
namespace {
uint32_t rd(const uint8_t *p) { uint32_t v; memcpy(&v,p,4); return v; }
void wr(uint8_t *p,uint32_t v) { memcpy(p,&v,4); }
uint64_t number(Value *v) { auto *c=dyn_cast<ConstantInt>(v); return c ? c->getZExtValue() : UINT64_MAX; }
uint64_t mdnumber(Metadata *m) { auto *v=dyn_cast_or_null<ConstantAsMetadata>(m); return v ? number(v->getValue()) : UINT64_MAX; }
bool op(CallInst *c,unsigned n) {
    auto *f=c->getCalledFunction();
    return f && f->getName().startswith("dx.op.") && c->arg_size() && number(c->getArgOperand(0))==n;
}
bool raw_load(CallInst *c) {
    if (!op(c,66) || !c->getCalledFunction()->getName().endswith(".f32")) return false;
    for (auto *u:c->users()) {
        auto *x=dyn_cast<ExtractValueInst>(u);
        if (!x || x->getNumIndices()!=1 || *x->idx_begin()>4) return false;
        if (*x->idx_begin()==4) continue; // residency status is already integer
        for (auto *v:x->users()) {
            auto *b=dyn_cast<BitCastInst>(v);
            if (!b || !b->getType()->isIntegerTy(32)) return false;
        }
    }
    return true;
}
unsigned lower(Module &m) {
    auto *named=m.getNamedMetadata("dx.resources");
    if (!named || named->getNumOperands()!=1) return 0;
    auto *all=named->getOperand(0);
    if (all->getNumOperands()!=4) return 0;
    auto *srvs=dyn_cast_or_null<MDNode>(all->getOperand(0));
    if (!srvs) return 0;
    unsigned total=0;
    for (unsigned r=0;r<srvs->getNumOperands();r++) {
        auto *resource=dyn_cast_or_null<MDNode>(srvs->getOperand(r));
        if (!resource || resource->getNumOperands()!=9 || mdnumber(resource->getOperand(6))!=4) continue; // Texture3D
        auto *props=dyn_cast_or_null<MDNode>(resource->getOperand(8));
        if (!props || props->getNumOperands()%2) continue;
        int component=-1;
        for (unsigned p=0;p<props->getNumOperands();p+=2)
            if (mdnumber(props->getOperand(p))==0 && mdnumber(props->getOperand(p+1))==9) component=p+1; // F32
        if (component<0) continue;
        uint64_t id=mdnumber(resource->getOperand(0));
        std::vector<CallInst*> handles,loads;
        bool valid=true;
        for (auto &f:m) for (auto &b:f) for (auto &i:b) {
            auto *c=dyn_cast<CallInst>(&i);
            if (c && op(c,57) && c->arg_size()==5 && number(c->getArgOperand(1))==0 && number(c->getArgOperand(2))==id) handles.push_back(c);
        }
        for (auto *h:handles) for (auto *u:h->users()) {
            auto *c=dyn_cast<CallInst>(u);
            if (!c || c->arg_size()<2 || c->getArgOperand(1)!=h) { valid=false; break; }
            if (op(c,72)) continue; // GetDimensions, independent of component type
            if (!raw_load(c)) { valid=false; break; }
            loads.push_back(c);
        }
        if (!valid || loads.empty()) continue;
        auto &ctx=m.getContext();
        auto *i32=Type::getInt32Ty(ctx);
        auto *ret=StructType::getTypeByName(ctx,"dx.types.ResRet.i32");
        if (!ret) ret=StructType::create(ctx,{i32,i32,i32,i32,i32},"dx.types.ResRet.i32");
        for (auto *old:loads) {
            auto *fn=old->getCalledFunction();
            SmallVector<Type*,9> types;
            SmallVector<Value*,9> args;
            for (auto &a:old->args()) { types.push_back(a->getType()); args.push_back(a); }
            auto callee=m.getOrInsertFunction("dx.op.textureLoad.i32",FunctionType::get(ret,types,false));
            if (auto *nf=dyn_cast<Function>(callee.getCallee())) nf->setAttributes(fn->getAttributes());
            IRBuilder<> builder(old);
            auto *replacement=builder.CreateCall(callee,args);
            SmallVector<ExtractValueInst*,8> extracts;
            for (auto *u:old->users()) extracts.push_back(cast<ExtractValueInst>(u));
            for (auto *x:extracts) {
                auto *value=builder.CreateExtractValue(replacement,*x->idx_begin());
                if (*x->idx_begin()==4) x->replaceAllUsesWith(value);
                else {
                    SmallVector<BitCastInst*,8> casts;
                    for (auto *u:x->users()) casts.push_back(cast<BitCastInst>(u));
                    for (auto *b:casts) { b->replaceAllUsesWith(value); b->eraseFromParent(); }
                }
                x->eraseFromParent();
            }
            old->eraseFromParent(); total++;
        }
        // Never mutate a shared component node: a 2D float texture may use it.
        SmallVector<Metadata*,8> properties;
        for (auto &p:props->operands()) properties.push_back(p.get());
        properties[component]=ConstantAsMetadata::get(ConstantInt::get(i32,5)); // U32
        resource->replaceOperandWith(8,MDNode::get(ctx,properties));
        // Keep DXIL's typed resource declaration consistent with its component
        // metadata, including the array wrapper used for bindless resources.
        auto *symbol=dyn_cast_or_null<ConstantAsMetadata>(resource->getOperand(1));
        if (symbol && isa<UndefValue>(symbol->getValue())) {
            auto *pointer=dyn_cast<PointerType>(symbol->getValue()->getType());
            if (pointer && !pointer->isOpaque()) {
                Type *shape=pointer->getNonOpaquePointerElementType();
                auto *array=dyn_cast<ArrayType>(shape);
                auto *texture=dyn_cast<StructType>(array ? array->getElementType() : shape);
                if (texture && !texture->isOpaque() && texture->getNumElements()==1) {
                    auto *vector=dyn_cast<FixedVectorType>(texture->getElementType(0));
                    Type *element=vector ? static_cast<Type*>(FixedVectorType::get(i32,vector->getNumElements())) : i32;
                    auto *typed=StructType::create(ctx,{element},"class.Texture3D<uint.payload>");
                    shape=array ? static_cast<Type*>(ArrayType::get(typed,array->getNumElements())) : typed;
                    resource->replaceOperandWith(1,ConstantAsMetadata::get(UndefValue::get(PointerType::get(shape,pointer->getAddressSpace()))));
                }
            }
        }
    }
    return total;
}
}
extern "C" int madeira_uint_volumes_rewrite(const void *bytes,size_t len,void **out,size_t *out_len,char *note,size_t cap) {
    *out=nullptr; *out_len=0; if (cap) note[0]=0;
    auto *data=static_cast<const uint8_t*>(bytes);
    if (len<32 || memcmp(data,"DXBC",4)) return 0;
    uint32_t count=rd(data+28);
    if (32+4ull*count>len) return 0;
    const uint8_t *part=nullptr; uint32_t size=0;
    for (unsigned i=0;i<count;i++) {
        uint64_t off=rd(data+32+4*i);
        if (off+8>len) return 0;
        uint32_t n=rd(data+off+4);
        if (off+8ull+n>len) return 0;
        if (!memcmp(data+off,"DXIL",4)) { part=data+off+8; size=n; }
    }
    if (!part || size<24) return 0;
    uint32_t offset=rd(part+16),length=rd(part+20);
    if (offset<16 || 8ull+offset+length>size) return 0;
    LLVMContext context; context.setOpaquePointers(false);
    auto buffer=MemoryBuffer::getMemBuffer(StringRef(reinterpret_cast<const char*>(part+8+offset),length),"volume",false);
    auto module=parseBitcodeFile(buffer->getMemBufferRef(),context);
    if (!module) { consumeError(module.takeError()); return -1; }
    unsigned n=lower(**module);
    if (!n) return 0;
    if (verifyModule(**module)) return -1;
    SmallVector<char,0> bitcode;
    { raw_svector_ostream stream(bitcode); WriteBitcodeToFile(**module,stream); }
    while (bitcode.size()%4) bitcode.push_back(0);
    std::vector<std::vector<uint8_t>> parts;
    for (unsigned i=0;i<count;i++) {
        uint32_t off=rd(data+32+4*i),sz=rd(data+off+4);
        if (!memcmp(data+off,"HASH",4) || !memcmp(data+off,"ILDB",4) || !memcmp(data+off,"STAT",4)) continue;
        parts.emplace_back(data+off,data+off+8+sz);
        if (!memcmp(data+off,"DXIL",4)) {
            auto &p=parts.back(); p.resize(8+24+bitcode.size());
            wr(p.data()+4,p.size()-8); wr(p.data()+12,(p.size()-8)/4);
            wr(p.data()+24,16); wr(p.data()+28,bitcode.size());
            memcpy(p.data()+32,bitcode.data(),bitcode.size());
        }
    }
    size_t total=32+4*parts.size(); for (auto &p:parts) total+=p.size();
    auto *result=static_cast<uint8_t*>(malloc(total)); if (!result) return -1;
    memcpy(result,data,24); memset(result+4,0,16); wr(result+24,total); wr(result+28,parts.size());
    size_t cursor=32+4*parts.size();
    for (unsigned i=0;i<parts.size();i++) { wr(result+32+4*i,cursor); memcpy(result+cursor,parts[i].data(),parts[i].size()); cursor+=parts[i].size(); }
    *out=result; *out_len=total;
    if (cap) snprintf(note,cap,"lowered %u raw volume load(s) to integer texture reads",n);
    return 1;
}
