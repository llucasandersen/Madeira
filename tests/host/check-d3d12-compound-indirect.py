#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run production indirect recording/replay against a delayed GPU fixture."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text(encoding='utf-8')
def function(start, end):
    at = source.index(start)
    return source[at:source.index(end, at)]

code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
typedef unsigned UINT; typedef uint64_t UINT64; typedef int32_t INT;
typedef int LONG;
static LONG InterlockedIncrement(LONG *n) { return ++*n; }
#define STDMETHODCALLTYPE
#define MAD_ROOT_PARAM_MAX 32
#define MAD_CMDSIG_ARGS_MAX 16
enum { D3D12_INDIRECT_ARGUMENT_TYPE_DRAW, D3D12_INDIRECT_ARGUMENT_TYPE_DRAW_INDEXED,
 D3D12_INDIRECT_ARGUMENT_TYPE_DISPATCH, D3D12_INDIRECT_ARGUMENT_TYPE_VERTEX_BUFFER_VIEW,
 D3D12_INDIRECT_ARGUMENT_TYPE_INDEX_BUFFER_VIEW, D3D12_INDIRECT_ARGUMENT_TYPE_CONSTANT,
 D3D12_INDIRECT_ARGUMENT_TYPE_CONSTANT_BUFFER_VIEW, D3D12_INDIRECT_ARGUMENT_TYPE_SHADER_RESOURCE_VIEW,
 D3D12_INDIRECT_ARGUMENT_TYPE_UNORDERED_ACCESS_VIEW };
typedef struct { UINT Type; union { struct { UINT Slot; } VertexBuffer;
 struct { UINT RootParameterIndex, DestOffsetIn32BitValues, Num32BitValuesToSet; } Constant;
 struct { UINT RootParameterIndex; } ConstantBufferView; }; } D3D12_INDIRECT_ARGUMENT_DESC;
typedef struct { UINT64 BufferLocation; UINT SizeInBytes, StrideInBytes; } D3D12_VERTEX_BUFFER_VIEW;
typedef struct { UINT64 BufferLocation; UINT SizeInBytes, Format; } D3D12_INDEX_BUFFER_VIEW;
enum { WMTResourceStorageModeShared, WMTBlitCommandCopyFromBufferToBuffer,
 WMTCommandBufferStatusError, WMTIndexTypeUInt16, WMTIndexTypeUInt32, DXGI_FORMAT_R16_UINT=57 };
enum mad_ck { MC_DRAW, MC_DRAW_INDEXED, MC_DISPATCH, MC_DRAW_INDIRECT, MC_DRAW_INDEXED_INDIRECT, MC_DISPATCH_INDIRECT };
struct buffer { unsigned char *mem; size_t size; int error; };
typedef struct buffer *obj_handle_t;
struct WMTBufferInfo { UINT64 length; UINT options; struct { void *ptr; } memory; };
struct wmtcmd_base { int type; };
struct wmtcmd_blit_copy_from_buffer_to_buffer { int type; obj_handle_t src, dst; UINT64 src_offset, dst_offset, copy_length; };
struct mad_resource { obj_handle_t buffer; UINT64 size; };
struct mad_cmd { enum mad_ck kind; union {
 struct { struct mad_resource *args; UINT64 off; UINT count, stride; struct mad_resource *cnt; UINT64 cnt_off;
 UINT ndesc; D3D12_INDIRECT_ARGUMENT_DESC desc[16]; } ind;
 struct { UINT vcount, icount, vstart, istart; } draw;
 struct { UINT icount, inst, start; INT base; UINT istart; } drawi;
 struct { UINT x,y,z; } dispatch;
 } u; };
struct mad_device { obj_handle_t mtl_device, mtl_queue; };
struct mad_vis_batch { int active; };
struct mad_queue { struct mad_device *device; obj_handle_t open_cb; UINT64 batches; struct mad_vis_batch *vis; };
struct mad_list { UINT64 ring_batch; };
struct mad_exec { struct mad_queue *q; struct mad_list *l; obj_handle_t cb;
 void *pso;
 UINT skipped, nroot; int fence_needed, f6_sync_needed, f6_list_start;
 UINT64 root[32], croot[32]; UINT consts[32][64], cconsts[32][64];
 struct { struct mad_resource *res; UINT64 off; UINT stride; } vb[16];
 struct mad_resource *ib; UINT64 ib_off; UINT ib_type; };
struct mad_cmdsig { struct { UINT NumArgumentDescs, ByteStride; } desc; D3D12_INDIRECT_ARGUMENT_DESC args[16]; };
typedef struct mad_list ID3D12GraphicsCommandList;
typedef struct mad_resource ID3D12Resource;
typedef struct mad_cmdsig ID3D12CommandSignature;
static struct buffer *allocated[100]; static UINT nalloc, waits, draws, dispatches, ncopies;
static struct wmtcmd_blit_copy_from_buffer_to_buffer copies[10];
static UINT64 seen_root[10]; static UINT seen_vertices[10]; static struct mad_cmd recorded;
static obj_handle_t buffer_new(size_t size) { struct buffer *b=calloc(1,sizeof *b);
 b->mem=calloc(1,size?size:1); b->size=size; allocated[nalloc++]=b; return b; }
static obj_handle_t MTLDevice_newBuffer(obj_handle_t d, struct WMTBufferInfo *bi) {
 (void)d; obj_handle_t b=buffer_new(bi->length); bi->memory.ptr=b->mem; return b; }
static obj_handle_t MTLCommandQueue_commandBuffer(obj_handle_t q) { (void)q; return buffer_new(0); }
static void NSObject_retain(obj_handle_t b) { assert(b); }
static void NSObject_release(obj_handle_t b) { assert(b); }
static obj_handle_t exec_begin_blit(struct mad_exec *e) { return e->cb; }
static void MTLBlitCommandEncoder_encodeCommands(obj_handle_t e, const struct wmtcmd_base *p) {
 assert(e); copies[ncopies++]=*(const struct wmtcmd_blit_copy_from_buffer_to_buffer *)p; }
static void exec_end(struct mad_exec *e) { (void)e; }
static void mad_queue_flush(struct mad_queue *q) { assert(!q->vis); q->open_cb=NULL; q->batches++; }
static void MTLCommandBuffer_waitUntilCompleted(obj_handle_t cb) {
 assert(cb); waits++; for(UINT i=0;i<ncopies;i++) { struct wmtcmd_blit_copy_from_buffer_to_buffer *c=&copies[i];
 assert(c->src_offset+c->copy_length<=c->src->size); assert(c->dst_offset+c->copy_length<=c->dst->size);
 memcpy(c->dst->mem+c->dst_offset,c->src->mem+c->src_offset,c->copy_length); } ncopies=0; }
static UINT MTLCommandBuffer_status(obj_handle_t cb) { return cb->error ? WMTCommandBufferStatusError : 99; }
static struct mad_resource addressed;
static struct mad_resource *mad_resolve_address(struct mad_device *d, UINT64 addr, UINT64 *off) {
 (void)d; *off=addr&255; return addr ? &addressed : NULL; }
static void mad_list_note_used(struct mad_list *l, struct mad_resource *r) { (void)l; (void)r; }
static UINT packed_instances[10], packed_vertex_start[10], packed_instance_start[10];
static void exec_draw(struct mad_exec *e, const struct mad_cmd *c) {
 if(c->kind==MC_DRAW_INDEXED) assert(e->vb[1].res==&addressed && e->vb[1].stride==16 && e->ib==&addressed && e->ib_type==WMTIndexTypeUInt16);
 assert(draws<10); seen_root[draws]=e->root[2];
 if(c->kind==MC_DRAW) { packed_instances[draws]=c->u.draw.icount;
 packed_vertex_start[draws]=c->u.draw.vstart; packed_instance_start[draws]=c->u.draw.istart; }
 seen_vertices[draws++]=c->kind==MC_DRAW ? c->u.draw.vcount : c->kind==MC_DRAW_INDEXED ? c->u.drawi.icount : 999; }
static void exec_dispatch(struct mad_exec *e, const struct mad_cmd *c) { assert(e->croot[2]==123 && c->u.dispatch.x==4); dispatches++; }
static struct mad_cmd *mad_list_push(struct mad_list *l, enum mad_ck kind) { (void)l; memset(&recorded,0,sizeof recorded); recorded.kind=kind; return &recorded; }
static unsigned g_list_seq, logged_live, logged_empty;
static void d3d12_log(const char *format, ...) {
 if(strncmp(format,"[indirect-input]",16)) return;
 va_list args; va_start(args,format);
 (void)va_arg(args,unsigned); (void)va_arg(args,void*);
 unsigned count=va_arg(args,unsigned); (void)va_arg(args,unsigned);
 logged_live=va_arg(args,unsigned); logged_empty=va_arg(args,unsigned);
 assert(logged_live+logged_empty==count);
 va_end(args);
}
''' + function('static UINT mad_indirect_size(', '\n#define MADEIRA_D3D12_BUILD') + function('static void exec_indirect(', '\nstatic void mad_exec_list') + function('static void STDMETHODCALLTYPE list_ExecuteIndirect(', '\nstatic void STDMETHODCALLTYPE list_CopyBufferRegion') + r'''
int main(void) {
 struct mad_vis_batch visibility={1};
 struct mad_device dev={0}; struct mad_queue q={.device=&dev,.vis=&visibility}; struct mad_list l={0};
 q.open_cb=buffer_new(0); struct mad_exec e={.q=&q,.l=&l,.cb=q.open_cb};
 struct mad_resource args={buffer_new(96),96}, cnt={buffer_new(8),8};
 struct mad_cmdsig sig={.desc={2,32},.args={{.Type=6,.ConstantBufferView={2}},{.Type=0}}};
 UINT actual=2; memcpy(cnt.buffer->mem+4,&actual,4);
 for(UINT i=0;i<3;i++) { UINT64 root=100+i; UINT draw[4]={10+i,1,0,0};
 memcpy(args.buffer->mem+32*i,&root,8); memcpy(args.buffer->mem+32*i+8,draw,16); }
 list_ExecuteIndirect(&l,&sig,3,&args,0,&cnt,4); assert(recorded.u.ind.ndesc==2);
 sig.args[0].ConstantBufferView.RootParameterIndex=9; /* recording owns its layout */
 exec_indirect(&e,&recorded);
 assert(waits==1 && draws==2 && seen_root[0]==100 && seen_root[1]==101);
 assert(seen_vertices[0]==10 && seen_vertices[1]==11 && e.root[2]==0 && e.root[9]==0);
 assert(q.batches==1 && l.ring_batch==2 && e.cb==q.open_cb);
 assert(q.vis==&visibility && q.vis->active==1); /* occlusion query survives internal commit */
 actual=0; memcpy(cnt.buffer->mem+4,&actual,4); e.root[2]=777; exec_indirect(&e,&recorded);
 assert(draws==2 && e.root[2]==0 && waits==2);
 actual=99; memcpy(cnt.buffer->mem+4,&actual,4); exec_indirect(&e,&recorded); assert(draws==5);
 /* Bounds failures record no command, including integer-overflow offsets. */
 recorded.u.ind.ndesc=0; list_ExecuteIndirect(&l,&sig,4,&args,0,&cnt,4); assert(!recorded.u.ind.ndesc);
 list_ExecuteIndirect(&l,&sig,1,&args,UINT64_MAX-3,&cnt,4); assert(!recorded.u.ind.ndesc);
 list_ExecuteIndirect(&l,&sig,1,&args,0,&cnt,6); assert(!recorded.u.ind.ndesc);
 sig.desc.ByteStride=20; list_ExecuteIndirect(&l,&sig,1,&args,0,NULL,0); assert(!recorded.u.ind.ndesc);
 /* Four-argument indexed signature binds CBV, VBV and IBV before drawing. */
 sig=(struct mad_cmdsig){.desc={4,64},.args={{.Type=6,.ConstantBufferView={2}},
 {.Type=3,.VertexBuffer={1}},{.Type=4},{.Type=1}}};
 UINT64 addr=123; D3D12_VERTEX_BUFFER_VIEW vb={512,128,16}; D3D12_INDEX_BUFFER_VIEW ib={1024,64,57};
 UINT indexed[5]={18,1,0,0,0};
 memcpy(args.buffer->mem,&addr,8); memcpy(args.buffer->mem+8,&vb,16);
 memcpy(args.buffer->mem+24,&ib,16); memcpy(args.buffer->mem+40,indexed,20);
 list_ExecuteIndirect(&l,&sig,1,&args,0,NULL,0); exec_indirect(&e,&recorded);
 assert(draws==6 && seen_root[5]==123 && seen_vertices[5]==18 && !e.ib && !e.vb[1].res);
 /* Compute uses its own root state. */
 sig=(struct mad_cmdsig){.desc={2,24},.args={{.Type=6,.ConstantBufferView={2}},{.Type=2}}};
 UINT dispatch[3]={4,2,1}; memcpy(args.buffer->mem+8,dispatch,12); e.root[2]=999;
 list_ExecuteIndirect(&l,&sig,1,&args,0,NULL,0); exec_indirect(&e,&recorded);
 assert(dispatches==1 && e.croot[2]==0 && e.root[2]==999);
 /* Single GPU draw has no CPU wait. */
 sig=(struct mad_cmdsig){.desc={1,16},.args={{.Type=0}}}; UINT before=waits;
 list_ExecuteIndirect(&l,&sig,1,&args,0,NULL,0); exec_indirect(&e,&recorded); assert(waits==before);
 /* Packed CBV + DRAW records: no stride padding, full 64-bit addresses,
  * and a zero instance count preserved between two nonempty records. */
 UINT packed_first=draws;
 sig=(struct mad_cmdsig){.desc={2,24},.args={{.Type=6,.ConstantBufferView={2}},{.Type=0}}};
 for(UINT i=0;i<3;i++) { UINT64 address=0x1000177c000ull+256*i;
 UINT draw[4]={12,i==1?0:i+1,9*i,17+i};
 memcpy(args.buffer->mem+24*i,&address,8); memcpy(args.buffer->mem+24*i+8,draw,16); }
 list_ExecuteIndirect(&l,&sig,3,&args,0,NULL,0); exec_indirect(&e,&recorded);
 assert(draws==packed_first+3 && waits==before+1 && e.root[2]==0);
 assert(logged_live==2 && logged_empty==1);
 for(UINT i=0;i<3;i++) {
 assert(seen_root[packed_first+i]==0x1000177c000ull+256*i && seen_vertices[packed_first+i]==12);
 assert(packed_instances[packed_first+i]==(i==1?0:i+1));
 assert(packed_vertex_start[packed_first+i]==9*i && packed_instance_start[packed_first+i]==17+i); }
 for(UINT i=0;i<nalloc;i++) { free(allocated[i]->mem); free(allocated[i]); }
 puts("PASS: production compound indirect bindings, count, reset, bounds, GPU wait and recording lifetime");
}
'''
with tempfile.TemporaryDirectory(prefix='madeira-indirect-') as directory:
    path = Path(directory)
    (path / 'probe.c').write_text(code, encoding='utf-8')
    subprocess.run(['cc', '-std=gnu11', '-O1', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    str(path / 'probe.c'), '-o', str(path / 'probe')], check=True)
    subprocess.run([str(path / 'probe')], check=True, timeout=30)
