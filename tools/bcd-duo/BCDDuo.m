// SPDX-License-Identifier: GPL-3.0-or-later
// Unofficial display compatibility layer for BCD 623. Modified 2026-10-30.
// BCD's runtime, swapchain drawable resolution and game settings are untouched.
#import <UIKit/UIKit.h>
#import <QuartzCore/CAMetalLayer.h>
#import <AVFAudio/AVFAudio.h>
#import <objc/runtime.h>
#include <math.h>

static char probeKey;
static BOOL pending;
static void refreshWindows(void);

static BOOL isContentWindow(UIWindow *w) {
    return w.windowScene && [w.windowScene.session.role isEqualToString:UIWindowSceneSessionRoleApplication] &&
        !w.hidden && w.windowLevel == UIWindowLevelNormal;
}

static void scheduleRefresh(void) {
    if (pending) return;
    pending = YES;
    dispatch_async(dispatch_get_main_queue(), ^{
        pending = NO;
        refreshWindows();
    });
}

@interface BCDDuoProbe : UIView
@property(nonatomic,copy) NSString *lastContext;
@end
@implementation BCDDuoProbe
- (BOOL)pointInside:(CGPoint)p withEvent:(UIEvent *)e { return NO; }
- (void)layoutSubviews {
    [super layoutSubviews];
    UIWindow *w = self.window;
    if (!w || !isContentWindow(w)) return;
    UIScreen *screen = w.windowScene.screen;
    NSString *context = [NSString stringWithFormat:@"window=%p bounds=%@ scale=%.2f hz=%ld screen=%p safe=%@ capture=%d",
        w, NSStringFromCGRect(w.bounds), w.traitCollection.displayScale,
        (long)screen.maximumFramesPerSecond, screen, NSStringFromUIEdgeInsets(w.safeAreaInsets), screen.captured];
    if (![context isEqualToString:self.lastContext]) {
        self.lastContext = context;
        fprintf(stderr, "[bcd-duo-display] %s\n", context.UTF8String);
        scheduleRefresh();
    }
}
@end

static BOOL named(id obj, NSString *suffix) {
    return [NSStringFromClass([obj class]) hasSuffix:suffix];
}

static void refreshView(UIView *v) {
    if (named(v, @"MetalHostView") && [v.layer isKindOfClass:CAMetalLayer.class]) {
        // Preserve the singleton layer, drawableSize, format and frame-rate cap.
        // BCD's own layout and touch mapping remain the owners of its frame.
        CGFloat scale = v.window.traitCollection.displayScale;
        if (scale > 0 && isfinite(scale)) {
            if (v.contentScaleFactor != scale) v.contentScaleFactor = scale;
            if (v.layer.contentsScale != scale) v.layer.contentsScale = scale;
        }
    }
    if (named(v, @"MetalBackedView")) {
        [v setNeedsLayout];
        [v layoutIfNeeded];
    }
    for (UIView *child in v.subviews) refreshView(child);
}

static void refreshWindows(void) {
    for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
        if (![scene isKindOfClass:UIWindowScene.class] ||
            ![scene.session.role isEqualToString:UIWindowSceneSessionRoleApplication]) continue;
        UIWindowScene *ws = (UIWindowScene *)scene;
        UIWindow *content = nil;
        for (UIWindow *w in ws.windows) {
            if (isContentWindow(w) && (!content || w.keyWindow)) content = w;
        }
        if (!content) continue;
        BCDDuoProbe *probe = objc_getAssociatedObject(content, &probeKey);
        if (!probe) {
            probe = [[BCDDuoProbe alloc] initWithFrame:content.bounds];
            probe.userInteractionEnabled = NO;
            probe.accessibilityElementsHidden = YES;
            probe.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
            objc_setAssociatedObject(content, &probeKey, probe, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
            [content insertSubview:probe atIndex:0];
        }
        if (!CGRectEqualToRect(probe.frame, content.bounds)) probe.frame = content.bounds;
        [probe setNeedsLayout];
        [probe layoutIfNeeded];
        refreshView(content);
        // Only BCD's known touch windows in the content scene. No external
        // display scene/window is created, preserving system AirPlay mirroring.
        for (UIWindow *overlay in ws.windows) {
            if ((named(overlay, @"ControlsWindow") || named(overlay, @"JoystickWindow")) &&
                !CGRectEqualToRect(overlay.frame, content.frame)) {
                overlay.frame = content.frame;
                [overlay.rootViewController.view setNeedsLayout];
            }
        }
    }
}

// Hook only BCD's two concrete views, never UIKit or the renderer's methods.
static IMP originalLayout;
static IMP originalMove;
static void hostLayout(UIView *self, SEL cmd) {
    if (originalLayout) ((void(*)(id,SEL))originalLayout)(self,cmd);
    [objc_getAssociatedObject(self.window, &probeKey) setNeedsLayout];
}
static void backedMove(UIView *self, SEL cmd) {
    if (originalMove) ((void(*)(id,SEL))originalMove)(self,cmd);
    scheduleRefresh();
}
static void replaceMethod(Class cls, SEL sel, IMP replacement, IMP *saved) {
    if (!cls) return;
    Method method = class_getInstanceMethod(cls, sel);
    if (!method) return;
    *saved = method_getImplementation(method);
    class_replaceMethod(cls, sel, replacement, method_getTypeEncoding(method));
}
static void install(void) {
    replaceMethod(NSClassFromString(@"_TtC7Madeira13MetalHostView"), @selector(layoutSubviews), (IMP)hostLayout, &originalLayout);
    replaceMethod(NSClassFromString(@"_TtC7Madeira15MetalBackedView"), @selector(didMoveToWindow), (IMP)backedMove, &originalMove);
    fprintf(stderr, "[bcd-duo] unofficial compatibility patch 1; host-hook=%d input-hook=%d; original game runtime retained\n",
        originalLayout != NULL, originalMove != NULL);
    NSNotificationCenter *nc = NSNotificationCenter.defaultCenter;
    for (NSNotificationName name in @[UIApplicationDidBecomeActiveNotification, UIWindowDidBecomeVisibleNotification,
            UIScreenDidConnectNotification, UIScreenDidDisconnectNotification, UIScreenModeDidChangeNotification,
            UIScreenCapturedDidChangeNotification, UIDeviceOrientationDidChangeNotification]) {
        [nc addObserverForName:name object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *n) { scheduleRefresh(); }];
    }
    [nc addObserverForName:AVAudioSessionRouteChangeNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *n) {
        NSMutableArray *types = [NSMutableArray array];
        for (AVAudioSessionPortDescription *p in AVAudioSession.sharedInstance.currentRoute.outputs) [types addObject:p.portType];
        fprintf(stderr, "[bcd-duo-audio] outputs=%s\n", [types componentsJoinedByString:@","].UTF8String);
        scheduleRefresh();
    }];
    scheduleRefresh();
}
__attribute__((constructor)) static void start(void) {
    dispatch_async(dispatch_get_main_queue(), ^{ install(); });
}
#ifdef BCD_DUO_TESTING
void BCDDuoRefreshForTesting(void) { refreshWindows(); }
BOOL BCDDuoHooksInstalledForTesting(void) { return originalLayout && originalMove; }
#endif
