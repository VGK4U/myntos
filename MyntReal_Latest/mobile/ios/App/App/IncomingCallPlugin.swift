import Foundation
import Capacitor

/**
 * IncomingCallPlugin — Capacitor Bridge for Native iOS Incoming Calls
 *
 * Exposes push token, pending call checks, dismissal, and server configuration
 * to the web runtime. Dispatches CallKit events to JavaScript listeners.
 */
@objc(IncomingCallPlugin)
public class IncomingCallPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "IncomingCallPlugin"
    public let jsName = "IncomingCall"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "getPushToken", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "getPendingCall", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "clearPendingCall", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "dismissCallNotification", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "saveServerConfig", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "triggerTestIncomingCall", returnType: CAPPluginReturnPromise)
    ]

    public static weak var sharedInstance: IncomingCallPlugin?

    override public func load() {
        super.load()
        IncomingCallPlugin.sharedInstance = self

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleVoIPCallAnswered(_:)),
            name: Notification.Name("VoIPCallAnswered"),
            object: nil
        )

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleVoIPTokenReceived(_:)),
            name: Notification.Name("VoIPTokenReceived"),
            object: nil
        )

        NSLog("[IncomingCallPlugin] Initialized and registered notification observers")
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    // MARK: - Plugin Methods

    @objc func getPushToken(_ call: CAPPluginCall) {
        let token = VoIPCallManager.shared.getVoIPToken()
        call.resolve([
            "pushToken": (token as Any),
            "platform": "ios",
            "tokenType": "apns_voip"
        ])
    }

    @objc func getPendingCall(_ call: CAPPluginCall) {
        if let pending = VoIPCallManager.shared.getPendingCallData() {
            call.resolve([
                "hasPendingCall": true,
                "sessionId": pending["sessionId"] as? String ?? "",
                "callerPhone": pending["callerPhone"] as? String ?? "",
                "callerName": pending["callerName"] as? String ?? "",
                "category": pending["category"] as? String ?? "",
                "leadType": pending["leadType"] as? String ?? "",
                "city": pending["city"] as? String ?? "",
                "status": pending["status"] as? String ?? "",
                "dealValue": pending["dealValue"] as? String ?? "",
                "leadId": pending["leadId"] as? String ?? "",
                "providerCallId": pending["providerCallId"] as? String ?? ""
            ])
        } else {
            call.resolve([
                "hasPendingCall": false
            ])
        }
    }

    @objc func clearPendingCall(_ call: CAPPluginCall) {
        VoIPCallManager.shared.clearPendingCallData()
        call.resolve(["success": true])
    }

    @objc func dismissCallNotification(_ call: CAPPluginCall) {
        VoIPCallManager.shared.endCurrentCall()
        call.resolve(["success": true])
    }

    @objc func saveServerConfig(_ call: CAPPluginCall) {
        if let baseUrl = call.getString("baseUrl") {
            UserDefaults.standard.set(baseUrl, forKey: "myntos_server_base_url")
        }
        if let authToken = call.getString("authToken") {
            UserDefaults.standard.set(authToken, forKey: "myntos_auth_token")
        }
        call.resolve(["success": true])
    }

    @objc func triggerTestIncomingCall(_ call: CAPPluginCall) {
        let callerPhone = call.getString("callerPhone") ?? "+919876543210"
        let callerName = call.getString("callerName") ?? "Rajesh Sharma"
        let delaySeconds = call.getDouble("delaySeconds") ?? 3.0
        let category = call.getString("category") ?? "Solar"
        let leadType = call.getString("leadType") ?? "5kW Residential Rooftop"
        let city = call.getString("city") ?? "Hyderabad"

        VoIPCallManager.shared.triggerTestIncomingCall(
            callerPhone: callerPhone,
            callerName: callerName,
            delaySeconds: delaySeconds,
            category: category,
            leadType: leadType,
            city: city
        )
        call.resolve(["success": true, "delay": delaySeconds])
    }

    // MARK: - Event Dispatching to JavaScript

    public func notifyCallAnswered(_ data: [String: Any]) {
        notifyListeners("callAnswered", data: [
            "sessionId": data["sessionId"] as? String ?? "",
            "callerPhone": data["callerPhone"] as? String ?? "",
            "callerName": data["callerName"] as? String ?? "",
            "category": data["category"] as? String ?? "",
            "leadType": data["leadType"] as? String ?? "",
            "city": data["city"] as? String ?? "",
            "status": data["status"] as? String ?? "",
            "dealValue": data["dealValue"] as? String ?? "",
            "leadId": data["leadId"] as? String ?? "",
            "providerCallId": data["providerCallId"] as? String ?? ""
        ])
    }

    public func notifyTokenReceived(_ token: String) {
        notifyListeners("tokenReceived", data: [
            "token": token
        ])
    }

    // MARK: - Notification Selectors

    @objc private func handleVoIPCallAnswered(_ notification: Notification) {
        if let userInfo = notification.userInfo as? [String: Any] {
            notifyCallAnswered(userInfo)
        }
    }

    @objc private func handleVoIPTokenReceived(_ notification: Notification) {
        if let token = notification.userInfo?["token"] as? String {
            notifyTokenReceived(token)
        }
    }
}
