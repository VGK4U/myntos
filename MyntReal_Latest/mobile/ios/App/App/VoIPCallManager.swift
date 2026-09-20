import Foundation
import UIKit
import PushKit
import CallKit
import AVFoundation

/**
 * VoIPCallManager — Native iOS PushKit & CallKit Orchestrator
 *
 * Manages VoIP push registrations (PKPushRegistry) and native incoming call screens (CXProvider).
 * Complies strictly with Apple iOS 13+ requirement: every VoIP push triggers CXProvider.reportNewIncomingCall.
 * Bridges CallKit answer/decline events to Capacitor JS layer and backend rejection endpoints.
 */
@objc public class VoIPCallManager: NSObject, PKPushRegistryDelegate, CXProviderDelegate {

    @objc public static let shared = VoIPCallManager()

    private var voipRegistry: PKPushRegistry?
    private var callProvider: CXProvider?
    private let callController = CXCallController()

    private var currentCallUUID: UUID?
    private var currentCallData: [String: Any]?
    private var pendingCallData: [String: Any]?
    private var voipToken: String?

    private override init() {
        super.init()
    }

    // MARK: - Lifecycle Initialization

    @objc public func start() {
        NSLog("[VoIPCallManager] Initializing CallKit & PushKit...")
        setupCallKit()
        setupPushKit()
    }

    private func setupCallKit() {
        let configuration = CXProviderConfiguration(localizedName: "MyntReal")
        configuration.supportsVideo = false
        configuration.maximumCallsPerCallGroup = 1
        configuration.supportedHandleTypes = [.generic, .phoneNumber]
        configuration.includesCallsInRecents = true

        let provider = CXProvider(configuration: configuration)
        provider.setDelegate(self, queue: nil)
        self.callProvider = provider
        NSLog("[VoIPCallManager] CXProvider configured successfully")
    }

    private func setupPushKit() {
        let registry = PKPushRegistry(queue: DispatchQueue.main)
        registry.delegate = self
        registry.desiredPushTypes = [.voIP]
        self.voipRegistry = registry
        NSLog("[VoIPCallManager] PKPushRegistry registered for .voIP")
    }

    // MARK: - PKPushRegistryDelegate

    public func pushRegistry(_ registry: PKPushRegistry, didUpdate pushCredentials: PKPushCredentials, for type: PKPushType) {
        guard type == .voIP else { return }

        let token = pushCredentials.token.map { String(format: "%02.2hhx", $0) }.joined()
        self.voipToken = token
        UserDefaults.standard.set(token, forKey: "myntos_voip_push_token")
        NSLog("[VoIPCallManager] VoIP Push Token registered: \(token.prefix(8))...")

        NotificationCenter.default.post(
            name: Notification.Name("VoIPTokenReceived"),
            object: nil,
            userInfo: ["token": token]
        )
    }

    public func pushRegistry(_ registry: PKPushRegistry, didInvalidatePushTokenFor type: PKPushType) {
        guard type == .voIP else { return }
        self.voipToken = nil
        UserDefaults.standard.removeObject(forKey: "myntos_voip_push_token")
        NSLog("[VoIPCallManager] VoIP Push Token invalidated by Apple")
    }

    public func pushRegistry(
        _ registry: PKPushRegistry,
        didReceiveIncomingPushWith payload: PKPushPayload,
        for type: PKPushType,
        completionHandler: @escaping () -> Void
    ) {
        guard type == .voIP else {
            completionHandler()
            return
        }

        var rawData: [String: Any] = [:]
        for (key, value) in payload.dictionaryPayload {
            if let stringKey = key as? String {
                rawData[stringKey] = value
            }
        }
        let data = (rawData["data"] as? [String: Any]) ?? rawData

        let eventType = (data["type"] as? String) ?? (data["event"] as? String) ?? "incoming_call"
        let sessionId = (data["call_session_id"] as? String) ?? (data["sessionId"] as? String) ?? UUID().uuidString
        let providerCallId = (data["provider_call_id"] as? String) ?? (data["providerCallId"] as? String) ?? ""
        let callerPhone = (data["caller_number"] as? String) ?? (data["callerPhone"] as? String) ?? "Unknown"
        let rawCallerName = (data["raw_caller_name"] as? String) ?? (data["caller_name"] as? String) ?? (data["callerName"] as? String) ?? ""
        let category = (data["category"] as? String) ?? (data["segment"] as? String) ?? ""
        let leadType = (data["lead_type"] as? String) ?? (data["requirements"] as? String) ?? ""
        let city = (data["city"] as? String) ?? ""
        let status = (data["status"] as? String) ?? ""
        let dealValue = (data["deal_value"] as? String) ?? ""
        let leadId = (data["lead_id"] as? String) ?? ""

        // Format clean Title for CallKit (Avoid parentheses that trigger Apple's horizontal marquee/truncation):
        let displayTitle: String
        let baseName = rawCallerName.isEmpty || rawCallerName == "Incoming Call" ? "" : rawCallerName
        if !category.isEmpty && !baseName.isEmpty {
            displayTitle = "[\(category)] \(baseName)"
        } else if !category.isEmpty {
            displayTitle = "[\(category)] \(callerPhone)"
        } else if !baseName.isEmpty {
            displayTitle = baseName
        } else {
            displayTitle = callerPhone.isEmpty ? "Incoming Lead Inquiry" : callerPhone
        }

        // Multi-attribute Subtitle for CXHandle (Displayed directly underneath Title on Lock Screen):
        var metaParts: [String] = []
        if !category.isEmpty { metaParts.append(category) }
        if !leadType.isEmpty { metaParts.append(leadType) }
        if !city.isEmpty { metaParts.append(city) }
        if !callerPhone.isEmpty { metaParts.append(callerPhone) }
        let displaySubtitle = metaParts.joined(separator: " • ")

        NSLog("[VoIPCallManager] VoIP push received: type=\(eventType), session=\(sessionId), title=\(displayTitle)")

        if eventType == "call_cancelled" {
            // Dismiss existing ringing CallKit screen
            if let activeUUID = currentCallUUID {
                callProvider?.reportCall(with: activeUUID, endedAt: Date(), reason: .remoteEnded)
                currentCallUUID = nil
                currentCallData = nil
                pendingCallData = nil
                completionHandler()
            } else {
                // Mandatory iOS 13 compliance: satisfy reportNewIncomingCall before completion
                let dummyUUID = UUID()
                let dummyUpdate = CXCallUpdate()
                dummyUpdate.remoteHandle = CXHandle(type: .generic, value: callerPhone)
                callProvider?.reportNewIncomingCall(with: dummyUUID, update: dummyUpdate) { [weak self] _ in
                    self?.callProvider?.reportCall(with: dummyUUID, endedAt: Date(), reason: .remoteEnded)
                    completionHandler()
                }
            }
            return
        }

        // Standard incoming call presentation
        let callUUID = UUID()
        self.currentCallUUID = callUUID
        let callInfo: [String: Any] = [
            "sessionId": sessionId,
            "callerPhone": callerPhone,
            "callerName": displayTitle,
            "rawCallerName": baseName,
            "category": category,
            "leadType": leadType,
            "city": city,
            "status": status,
            "dealValue": dealValue,
            "leadId": leadId,
            "providerCallId": providerCallId
        ]
        self.currentCallData = callInfo

        let update = CXCallUpdate()
        update.remoteHandle = CXHandle(type: .generic, value: displaySubtitle)
        update.localizedCallerName = displayTitle
        update.hasVideo = false
        update.supportsDTMF = true
        update.supportsHolding = false
        update.supportsGrouping = false
        update.supportsUngrouping = false

        callProvider?.reportNewIncomingCall(with: callUUID, update: update) { [weak self] error in
            if let error = error {
                NSLog("[VoIPCallManager] CXProvider reportNewIncomingCall failed: \(error.localizedDescription)")
                self?.currentCallUUID = nil
                self?.currentCallData = nil
            } else {
                NSLog("[VoIPCallManager] CXProvider successfully presented incoming call: \(displayTitle) (\(displaySubtitle))")
            }
            completionHandler()
        }
    }

    // MARK: - CXProviderDelegate

    public func providerDidReset(_ provider: CXProvider) {
        NSLog("[VoIPCallManager] CXProvider did reset")
        currentCallUUID = nil
        currentCallData = nil
        pendingCallData = nil
    }

    public func provider(_ provider: CXProvider, perform action: CXAnswerCallAction) {
        NSLog("[VoIPCallManager] User answered call via CallKit (action: \(action.callUUID))")

        // 1. Configure and activate AVAudioSession for conversational voice call
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .allowBluetoothA2DP])
            try session.setActive(true)
        } catch {
            NSLog("[VoIPCallManager] Error activating AVAudioSession on answer: \(error)")
        }

        // 2. Prepare payload
        let callData = currentCallData ?? [
            "sessionId": action.callUUID.uuidString,
            "callerPhone": "Unknown",
            "callerName": "Incoming Call",
            "providerCallId": ""
        ]
        self.pendingCallData = callData

        // 3. Fulfill CallKit action
        action.fulfill()

        // 4. Notify app listeners
        NotificationCenter.default.post(
            name: Notification.Name("VoIPCallAnswered"),
            object: nil,
            userInfo: callData
        )
    }

    public func provider(_ provider: CXProvider, perform action: CXEndCallAction) {
        NSLog("[VoIPCallManager] User declined or ended call via CallKit (action: \(action.callUUID))")

        let callData = currentCallData
        self.currentCallUUID = nil
        self.currentCallData = nil
        self.pendingCallData = nil

        action.fulfill()

        // Send decline HTTP POST to backend
        if let data = callData, let sessionId = data["sessionId"] as? String {
            let providerCallId = (data["providerCallId"] as? String) ?? ""
            sendDeclineToServer(sessionId: sessionId, providerCallId: providerCallId)
        }
    }

    public func provider(_ provider: CXProvider, didActivate audioSession: AVAudioSession) {
        NSLog("[VoIPCallManager] CallKit audioSession didActivate")
    }

    public func provider(_ provider: CXProvider, didDeactivate audioSession: AVAudioSession) {
        NSLog("[VoIPCallManager] CallKit audioSession didDeactivate")
    }

    // MARK: - Server Rejection & State Helpers

    private func sendDeclineToServer(sessionId: String, providerCallId: String) {
        let baseUrl = UserDefaults.standard.string(forKey: "myntos_server_base_url") ?? "http://localhost:8000"
        let authToken = UserDefaults.standard.string(forKey: "myntos_auth_token")

        guard let url = URL(string: "\(baseUrl)/api/v1/telephony/mobile/call/reject") else {
            NSLog("[VoIPCallManager] Invalid reject URL: \(baseUrl)")
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = authToken, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let body: [String: Any] = [
            "call_session_id": sessionId,
            "provider_call_id": providerCallId,
            "reason": "user_declined"
        ]

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: body, options: [])
            let task = URLSession.shared.dataTask(with: request) { _, response, error in
                if let error = error {
                    NSLog("[VoIPCallManager] Error dispatching decline to backend: \(error.localizedDescription)")
                } else if let httpResponse = response as? HTTPURLResponse {
                    NSLog("[VoIPCallManager] Backend decline response status: \(httpResponse.statusCode)")
                }
            }
            task.resume()
        } catch {
            NSLog("[VoIPCallManager] Failed to serialize decline request payload: \(error)")
        }
    }

    @objc public func endCurrentCall(reason: CXCallEndedReason = .declinedElsewhere) {
        guard let uuid = currentCallUUID else { return }
        callProvider?.reportCall(with: uuid, endedAt: Date(), reason: reason)
        currentCallUUID = nil
        currentCallData = nil
        pendingCallData = nil
    }

    @objc public func getPendingCallData() -> [String: Any]? {
        return pendingCallData
    }

    @objc public func clearPendingCallData() {
        pendingCallData = nil
    }

    @objc public func getVoIPToken() -> String? {
        return voipToken ?? UserDefaults.standard.string(forKey: "myntos_voip_push_token")
    }

    @objc public func triggerTestIncomingCall(
        callerPhone: String = "+919876543210",
        callerName: String = "Rajesh Sharma",
        delaySeconds: Double = 0.0,
        category: String = "Solar",
        leadType: String = "5kW Residential Rooftop",
        city: String = "Hyderabad"
    ) {
        if self.callProvider == nil {
            self.setupCallKit()
        }

        var bgTask: UIBackgroundTaskIdentifier = .invalid
        if delaySeconds > 0 {
            bgTask = UIApplication.shared.beginBackgroundTask(withName: "MyntOSTestIncomingCall") {
                if bgTask != .invalid {
                    UIApplication.shared.endBackgroundTask(bgTask)
                    bgTask = .invalid
                }
            }
        }

        let block = { [weak self] in
            defer {
                if bgTask != .invalid {
                    UIApplication.shared.endBackgroundTask(bgTask)
                    bgTask = .invalid
                }
            }
            guard let self = self else { return }
            let callUUID = UUID()
            self.currentCallUUID = callUUID
            let sessionId = "test_\(UUID().uuidString.prefix(8))"

            let displayCategory = category.isEmpty ? "Solar" : category
            let displayLeadType = leadType.isEmpty ? "5kW Residential Rooftop" : leadType
            let displayCity = city.isEmpty ? "Hyderabad" : city
            let baseName = callerName.isEmpty ? "Rajesh Sharma" : callerName

            let displayTitle = baseName.contains("[") ? baseName : "[\(displayCategory)] \(baseName)"
            let displaySubtitle = "\(displayCategory) • \(displayLeadType) • \(displayCity) • \(callerPhone)"

            let callInfo: [String: Any] = [
                "sessionId": sessionId,
                "callerPhone": callerPhone,
                "callerName": displayTitle,
                "rawCallerName": baseName,
                "category": displayCategory,
                "leadType": displayLeadType,
                "city": displayCity,
                "status": "Interested",
                "dealValue": "₹3,50,000",
                "providerCallId": "test_provider_\(sessionId)"
            ]
            self.currentCallData = callInfo

            let update = CXCallUpdate()
            update.remoteHandle = CXHandle(type: .generic, value: displaySubtitle)
            update.localizedCallerName = displayTitle
            update.hasVideo = false
            update.supportsDTMF = true
            update.supportsHolding = false
            update.supportsGrouping = false
            update.supportsUngrouping = false

            NSLog("[VoIPCallManager] Presenting CXProvider incoming call: \(displayTitle) (\(displaySubtitle))...")

            self.callProvider?.reportNewIncomingCall(with: callUUID, update: update) { error in
                if let error = error {
                    NSLog("[VoIPCallManager] Test CXProvider reportNewIncomingCall failed: \(error.localizedDescription)")
                    self.currentCallUUID = nil
                    self.currentCallData = nil
                } else {
                    NSLog("[VoIPCallManager] Test CXProvider successfully presented incoming call")
                }
            }
        }

        if delaySeconds > 0 {
            DispatchQueue.main.asyncAfter(deadline: .now() + delaySeconds, execute: block)
        } else {
            DispatchQueue.main.async(execute: block)
        }
    }
}
