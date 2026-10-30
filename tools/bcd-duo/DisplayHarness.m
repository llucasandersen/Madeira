// SPDX-License-Identifier: GPL-3.0-or-later
// UIKit integration fixture for the compatibility layer, not BCD game code.
#import <UIKit/UIKit.h>
#import <QuartzCore/CAMetalLayer.h>
#import <Metal/Metal.h>
extern void BCDDuoRefreshForTesting(void);
extern BOOL BCDDuoHooksInstalledForTesting(void);

__attribute__((objc_runtime_name("_TtC7Madeira13MetalHostView")))
@interface TestMetalHostView : UIView @end
@implementation TestMetalHostView
+ (Class)layerClass { return CAMetalLayer.class; }
@end
__attribute__((objc_runtime_name("_TtC7Madeira15MetalBackedView")))
@interface TestMetalBackedView : UIView
@property(nonatomic,weak) UIView *surface;
@end
@implementation TestMetalBackedView
- (void)layoutSubviews {
    [super layoutSubviews];
    // Representative BCD fit frame. Geometry stays owned by the placeholder.
    CGFloat height = self.bounds.size.width * 9.0 / 16.0;
    self.surface.frame = CGRectMake(0,(self.bounds.size.height-height)/2,self.bounds.size.width,height);
}
@end
@interface TestControlsWindow : UIWindow @end
@implementation TestControlsWindow @end

@interface HarnessScene : UIResponder <UIWindowSceneDelegate>
@property(nonatomic,strong) UIWindow *window;
@property(nonatomic,strong) UIWindow *controls;
@end
@implementation HarnessScene
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)options {
    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    self.window.rootViewController = [UIViewController new];
    TestMetalHostView *host = [[TestMetalHostView alloc] initWithFrame:CGRectMake(0,0,960,540)];
    host.userInteractionEnabled = NO;
    CAMetalLayer *metal = (CAMetalLayer *)host.layer;
    metal.device = MTLCreateSystemDefaultDevice();
    metal.drawableSize = CGSizeMake(960,540);
    TestMetalBackedView *input = [[TestMetalBackedView alloc] initWithFrame:self.window.bounds];
    input.surface = host;
    input.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    [self.window.rootViewController.view addSubview:input];
    [self.window addSubview:host];
    [self.window makeKeyAndVisible];
    self.controls = [[TestControlsWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    // Use BCD's actual runtime class name suffix for the overlay test.
    self.controls.windowLevel = UIWindowLevelNormal+101;
    self.controls.rootViewController = [UIViewController new];
    self.controls.hidden = NO;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,2*NSEC_PER_SEC),dispatch_get_main_queue(),^{
        NSMutableArray *results = [NSMutableArray array];
        NSArray *spaces = @[[NSValue valueWithCGSize:CGSizeMake(466,678)],
                            [NSValue valueWithCGSize:CGSizeMake(890,626)],
                            [NSValue valueWithCGSize:CGSizeMake(626,890)],
                            [NSValue valueWithCGSize:CGSizeMake(678,466)]];
        CALayer *original = host.layer;
        for (NSValue *space in spaces) {
            self.window.bounds = (CGRect){CGPointZero,space.CGSizeValue};
            self.window.rootViewController.view.frame = self.window.bounds;
            input.frame = self.window.bounds;
            host.contentScaleFactor = 1;
            host.layer.contentsScale = 1;
            [input setNeedsLayout];
            BCDDuoRefreshForTesting();
            [input layoutIfNeeded];
            BOOL probe = NO;
            for (UIView *v in self.window.subviews) if ([NSStringFromClass(v.class) isEqualToString:@"BCDDuoProbe"]) probe = !v.userInteractionEnabled;
            BOOL ok = BCDDuoHooksInstalledForTesting() && probe && host.layer == original && CGSizeEqualToSize(metal.drawableSize,CGSizeMake(960,540)) &&
                host.contentScaleFactor == self.window.traitCollection.displayScale &&
                host.layer.contentsScale == self.window.traitCollection.displayScale &&
                CGRectEqualToRect(self.controls.frame,self.window.frame) &&
                fabs(host.frame.size.width-input.bounds.size.width)<0.01;
            [results addObject:@{@"bounds":NSStringFromCGSize(space.CGSizeValue),@"passed":@(ok)}];
        }
        BOOL all = YES;
        for (NSDictionary *r in results) all &= [r[@"passed"] boolValue];
        NSDictionary *report = @{@"passed":@(all),@"checks":results,@"scope":@"UIKit integration fixture; physical BCD gameplay pending"};
        NSData *data = [NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:NULL];
        NSURL *dir = [NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
        [data writeToURL:[dir URLByAppendingPathComponent:@"duo-fixture.json"] atomically:YES];
        fprintf(stderr,"[duo-fixture] passed=%d\n",all);
    });
}
@end

@interface HarnessApp : UIResponder <UIApplicationDelegate> @end
@implementation HarnessApp
- (UISceneConfiguration *)application:(UIApplication *)app configurationForConnectingSceneSession:(UISceneSession *)session options:(UISceneConnectionOptions *)options {
    UISceneConfiguration *c = [[UISceneConfiguration alloc] initWithName:@"Test" sessionRole:session.role];
    c.delegateClass = HarnessScene.class;
    return c;
}
@end
int main(int argc,char **argv) {
    @autoreleasepool { return UIApplicationMain(argc,argv,nil,NSStringFromClass(HarnessApp.class)); }
}
