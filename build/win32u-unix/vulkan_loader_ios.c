/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Select the bundled Vulkan loader without relying on desktop search paths.
 * Wine's Vulkan implementation and generated dispatch remain unchanged.
 */
#include <dlfcn.h>
#include <string.h>

extern const char *madeira_vulkan_library_path(void) __attribute__((weak));

static void *madeira_vulkan_dlopen(const char *name, int flags)
{
    if (name && !strcmp(name, "madeira-vulkan-ios"))
    {
        const char *path = madeira_vulkan_library_path ? madeira_vulkan_library_path() : NULL;
        return path ? dlopen(path, flags) : NULL;
    }
    return dlopen(name, flags);
}

#include "ntstatus.h"
#include "ntgdi_private.h"
#include "vulkan_present_ios.h"
#define dlopen madeira_vulkan_dlopen
#include "../../wine/dlls/win32u/vulkan.c"
