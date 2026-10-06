/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Wine calls client_surface_present even when the host presentation failed.
 * Only successful/suboptimal submissions may advance the app's launch gate.
 * Included after ntgdi_private.h so the macro does not alter its declaration.
 * The pinned upstream call site has swapchain_res in scope (checked by tests).
 */
static inline void madeira_vulkan_present_if_success(struct client_surface *client, int result)
{
    if (result >= 0) client_surface_present(client);
}
#define client_surface_present(client) madeira_vulkan_present_if_success(client, swapchain_res)
