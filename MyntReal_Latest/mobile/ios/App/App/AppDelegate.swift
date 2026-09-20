import UIKit
import Capacitor
import AVFoundation

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        // Configure AVAudioSession for loud media playback & recording listening by default
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try session.overrideOutputAudioPort(.speaker)
            try session.setActive(true)
        } catch {
            print("[AppDelegate] Notice initializing AVAudioSession: \(error)")
        }

        // Initialize CallKit and PushKit for screen-off VoIP incoming call handling
        VoIPCallManager.shared.start()

        // Register Darwin notification observer to allow direct incoming call triggers from host/devicectl
        let darwinCenter = CFNotificationCenterGetDarwinNotifyCenter()
        CFNotificationCenterAddObserver(
            darwinCenter,
            nil,
            { (_, _, _, _, _) in
                NSLog("[AppDelegate] Darwin notification received: triggering test incoming call immediately")
                VoIPCallManager.shared.triggerTestIncomingCall(
                    callerPhone: "+919876543210",
                    callerName: "Rajesh Sharma",
                    delaySeconds: 0,
                    category: "Solar",
                    leadType: "5kW Residential Rooftop",
                    city: "Hyderabad"
                )
            },
            "com.myntos.trigger_test_call" as CFString,
            nil,
            .deliverImmediately
        )

        return true
    }

    func applicationWillResignActive(_ application: UIApplication) {
        // Sent when the application is about to move from active to inactive state. This can occur for certain types of temporary interruptions (such as an incoming phone call or SMS message) or when the user quits the application and it begins the transition to the background state.
        // Use this method to pause ongoing tasks, disable timers, and invalidate graphics rendering callbacks. Games should use this method to pause the game.
    }

    func applicationDidEnterBackground(_ application: UIApplication) {
        // Use this method to release shared resources, save user data, invalidate timers, and store enough application state information to restore your application to its current state in case it is terminated later.
        // If your application supports background execution, this method is called instead of applicationWillTerminate: when the user quits.
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        // Called as part of the transition from the background to the active state; here you can undo many of the changes made on entering the background.
    }

    func applicationDidBecomeActive(_ application: UIApplication) {
        // Restart any tasks that were paused (or not yet started) while the application was inactive. If the application was previously in the background, optionally refresh the user interface.
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Called when the application is about to terminate. Save data if appropriate. See also applicationDidEnterBackground:.
    }

    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey: Any] = [:]) -> Bool {
        if url.scheme == "myntreal" && (url.host == "test-call" || url.path.contains("test-call")) {
            NSLog("[AppDelegate] URL scheme received: \(url.absoluteString)")
            VoIPCallManager.shared.triggerTestIncomingCall(
                callerPhone: "+919876543210",
                callerName: "Rajesh Sharma",
                delaySeconds: 0,
                category: "Solar",
                leadType: "5kW Residential Rooftop",
                city: "Hyderabad"
            )
            return true
        }
        return ApplicationDelegateProxy.shared.application(app, open: url, options: options)
    }

    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        // Called when the app was launched with an activity, including Universal Links.
        // Feel free to add additional processing here, but if you want the App API to support
        // tracking app url opens, make sure to keep this call
        return ApplicationDelegateProxy.shared.application(application, continue: userActivity, restorationHandler: restorationHandler)
    }

}
