/* iOS Vulkan Metal surface integration.
 * Based on Wine's winemac.drv/vulkan.c:
 * Copyright 2017 Roderick Colenbrander
 * Copyright 2018 Andrew Eikum for CodeWeavers
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */
#include "ntstatus.h"
#include "ntgdi_private.h"
#include "wine/vulkan_driver.h"

extern void *madeira_vulkan_layer_acquire(void *hwnd) __attribute__((weak));
extern void madeira_vulkan_layer_release(void *layer) __attribute__((weak));

struct ios_vulkan_surface
{
    struct client_surface client;
    void *layer;
};

static void surface_destroy(struct client_surface *client)
{
    struct ios_vulkan_surface *surface = (struct ios_vulkan_surface *)client;
    if (surface->layer) madeira_vulkan_layer_release(surface->layer);
}

/* UIKit/compositor owns placement and visibility. The layer is retained until
 * Vulkan surface destruction, including after its HWND has been detached. */
static void surface_noop(struct client_surface *client) {}
static void surface_present(struct client_surface *client, HDC hdc) {}
static const struct client_surface_funcs surface_funcs =
{
    .destroy = surface_destroy,
    .detach = surface_noop,
    .update = surface_noop,
    .present = surface_present,
};

static VkResult surface_create(HWND hwnd, const struct vulkan_instance *instance,
                              VkSurfaceKHR *handle, struct client_surface **client)
{
    struct ios_vulkan_surface *surface;
    VkResult result;
    *client = NULL;
    *handle = VK_NULL_HANDLE;
    if (!instance->p_vkCreateMetalSurfaceEXT || !madeira_vulkan_layer_acquire ||
        !madeira_vulkan_layer_release) return VK_ERROR_INCOMPATIBLE_DRIVER;
    if (!(surface = client_surface_create(sizeof(*surface), &surface_funcs, hwnd)))
        return VK_ERROR_OUT_OF_HOST_MEMORY;
    if (!(surface->layer = madeira_vulkan_layer_acquire(hwnd)))
    {
        client_surface_release(&surface->client);
        return VK_ERROR_SURFACE_LOST_KHR;
    }
    VkMetalSurfaceCreateInfoEXT info = {
        .sType = VK_STRUCTURE_TYPE_METAL_SURFACE_CREATE_INFO_EXT,
        .pLayer = surface->layer,
    };
    result = instance->p_vkCreateMetalSurfaceEXT(instance->host.instance, &info, NULL, handle);
    if (result != VK_SUCCESS)
    {
        client_surface_release(&surface->client);
        return result;
    }
    *client = &surface->client;
    return VK_SUCCESS;
}

static VkBool32 presentation_support(struct vulkan_physical_device *device, uint32_t index)
{
    uint32_t count = 0;
    VkQueueFamilyProperties *queues;
    VkBool32 supported = VK_FALSE;
    device->instance->p_vkGetPhysicalDeviceQueueFamilyProperties(device->host.physical_device, &count, NULL);
    if (index >= count || !(queues = calloc(count, sizeof(*queues)))) return VK_FALSE;
    device->instance->p_vkGetPhysicalDeviceQueueFamilyProperties(device->host.physical_device, &count, queues);
    if (index < count) supported = !!(queues[index].queueFlags & VK_QUEUE_GRAPHICS_BIT);
    free(queues);
    return supported;
}

static void map_instance_extensions(struct vulkan_instance_extensions *extensions)
{
    if (extensions->has_VK_KHR_win32_surface) extensions->has_VK_EXT_metal_surface = 1;
    if (extensions->has_VK_EXT_metal_surface) extensions->has_VK_KHR_win32_surface = 1;
}

static void map_device_extensions(struct vulkan_device_extensions *extensions) {}
static const struct vulkan_driver_funcs driver_funcs =
{
    .p_vulkan_surface_create = surface_create,
    .p_get_physical_device_presentation_support = presentation_support,
    .p_map_instance_extensions = map_instance_extensions,
    .p_map_device_extensions = map_device_extensions,
};

UINT winios_VulkanInit(UINT version, void *vulkan_handle, const struct vulkan_driver_funcs **funcs)
{
    if (version != WINE_VULKAN_DRIVER_VERSION) return STATUS_INVALID_PARAMETER;
    if (!madeira_vulkan_layer_acquire || !madeira_vulkan_layer_release)
        return STATUS_NOT_IMPLEMENTED;
    *funcs = &driver_funcs;
    return STATUS_SUCCESS;
}
