#!/usr/bin/env python3
"""Report real WGL context capabilities without changing version selection."""
from pathlib import Path
import sys

source = Path(sys.argv[1])
file = source / 'src/gallium/frontends/wgl/stw_context.c'
text = file.read_text()
marker = '/* Madeira: report actual context capabilities when MESA_DEBUG is enabled. */'
helper = r'''
/* Madeira: report actual context capabilities when MESA_DEBUG is enabled. */
static void
madeira_report_context(struct gl_context *gl, int major, int minor, int profile)
{
   if (!getenv("MESA_DEBUG"))
      return;
   char message[1024];
   snprintf(message, sizeof(message),
            "[madeira-gl-context] requested=%d.%d profile=%d actual=%d api=%d glsl=%d version=%s\n",
            major, minor, profile, gl->Version, gl->API, gl->Const.GLSLVersion,
            gl->VersionString ? gl->VersionString : "(unset)");
   OutputDebugStringA(message);
   if (gl->Version >= 30)
      return;

   /* Mirror Mesa's OpenGL 3.0 gates; report failures, never enable them. */
   size_t used = 0;
   used += snprintf(message, sizeof(message), "[madeira-gl-context] missing-gl30:");
#define MADEIRA_GATE(name, supported) do { \
   if (!(supported) && used < sizeof(message) - 2) \
      used += snprintf(message + used, sizeof(message) - used, " %s", name); \
} while (0)
   MADEIRA_GATE("GLSL130", gl->Const.GLSLVersion >= 130);
   MADEIRA_GATE("color-attachments4", gl->Const.MaxColorAttachments >= 4);
   MADEIRA_GATE("samples4", gl->Const.MaxSamples >= 4 || gl->Const.FakeSWMSAA);
   MADEIRA_GATE("ARB_color_buffer_float", gl->API == API_OPENGL_CORE || gl->Extensions.ARB_color_buffer_float);
#define MADEIRA_EXTENSION(name) MADEIRA_GATE(#name, gl->Extensions.name)
   MADEIRA_EXTENSION(ARB_shadow);
   MADEIRA_EXTENSION(ARB_vertex_shader);
   MADEIRA_EXTENSION(ARB_fragment_shader);
   MADEIRA_EXTENSION(ARB_texture_non_power_of_two);
   MADEIRA_EXTENSION(EXT_blend_equation_separate);
   MADEIRA_EXTENSION(EXT_stencil_two_side);
   MADEIRA_EXTENSION(EXT_texture_sRGB);
   MADEIRA_EXTENSION(ARB_depth_buffer_float);
   MADEIRA_EXTENSION(ARB_half_float_vertex);
   MADEIRA_EXTENSION(ARB_map_buffer_range);
   MADEIRA_EXTENSION(ARB_shader_texture_lod);
   MADEIRA_EXTENSION(ARB_texture_float);
   MADEIRA_EXTENSION(ARB_texture_rg);
   MADEIRA_EXTENSION(ARB_texture_compression_rgtc);
   MADEIRA_EXTENSION(EXT_draw_buffers2);
   MADEIRA_EXTENSION(ARB_framebuffer_object);
   MADEIRA_EXTENSION(EXT_framebuffer_sRGB);
   MADEIRA_EXTENSION(EXT_packed_float);
   MADEIRA_EXTENSION(EXT_texture_array);
   MADEIRA_EXTENSION(EXT_texture_integer);
   MADEIRA_EXTENSION(EXT_texture_shared_exponent);
   MADEIRA_EXTENSION(EXT_transform_feedback);
   MADEIRA_EXTENSION(NV_conditional_render);
#undef MADEIRA_EXTENSION
#undef MADEIRA_GATE
   message[sizeof(message) - 1] = 0;
   OutputDebugStringA(message);
   OutputDebugStringA("\n");
}
'''
if marker not in text:
    anchor = 'struct stw_context *\nstw_current_context(void)'
    assert text.count(anchor) == 1, 'Mesa WGL context entry changed'
    text = text.replace(anchor, '#include <stdio.h>\n#include <stdlib.h>\n' + helper + '\n' + anchor, 1)
    anchor = '   ctx->st->frontend_context = (void *) ctx;'
    assert text.count(anchor) == 1, 'Mesa WGL context creation changed'
    text = text.replace(anchor, anchor + '\n   madeira_report_context(ctx->st->ctx, majorVersion, minorVersion, profileMask);', 1)
    anchor = '   if (ctx->st == NULL)\n      goto no_st_ctx;'
    replacement = '''   if (ctx->st == NULL) {
      if (getenv("MESA_DEBUG")) {
         char message[160];
         snprintf(message, sizeof(message), "[madeira-gl-context] creation-failed requested=%d.%d profile=%d error=%d\\n",
                  majorVersion, minorVersion, profileMask, ctx_err);
         OutputDebugStringA(message);
      }
      goto no_st_ctx;
   }'''
    assert text.count(anchor) == 1, 'Mesa context failure branch changed'
    file.write_text(text.replace(anchor, replacement, 1))
print('Patched WGL capability diagnostics; context selection and feature flags unchanged')
