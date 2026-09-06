import Foundation
import CoreLocation
import UIKit
import Capacitor

@objc(BackgroundLocationPlugin)
public class BackgroundLocationPlugin: CAPPlugin, CLLocationManagerDelegate {
    private var locationManager: CLLocationManager?
    private var isTrackingLocation = false
    private var authToken: String?
    private var apiUrl: String?
    private var uploadInterval: TimeInterval = 15.0
    private var lastUploadTime: Date?
    private var isDrainingQueue = false
    private var pendingPermissionCall: CAPPluginCall?
    private let queueLock = NSLock()

    private var queueFilePath: URL {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return docs.appendingPathComponent("ios_bg_location_queue.json")
    }

    public override func load() {
        super.load()
        
        // Restore persisted auth/api configs if previously active
        self.authToken = UserDefaults.standard.string(forKey: "myntos_bg_auth_token")
        self.apiUrl = UserDefaults.standard.string(forKey: "myntos_bg_api_url")
        let savedInterval = UserDefaults.standard.double(forKey: "myntos_bg_upload_interval")
        if savedInterval > 0 {
            self.uploadInterval = savedInterval
        }

        DispatchQueue.main.async {
            self.locationManager = CLLocationManager()
            self.locationManager?.delegate = self
            self.locationManager?.desiredAccuracy = kCLLocationAccuracyBest
            self.locationManager?.distanceFilter = 10.0
            if #available(iOS 9.0, *) {
                self.locationManager?.allowsBackgroundLocationUpdates = true
            }
            if #available(iOS 11.0, *) {
                self.locationManager?.showsBackgroundLocationIndicator = true
            }
            self.locationManager?.pausesLocationUpdatesAutomatically = false

            // Auto-drain any queued records when app returns to foreground/becomes active
            NotificationCenter.default.addObserver(
                self,
                selector: #selector(self.appDidBecomeActive),
                name: UIApplication.didBecomeActiveNotification,
                object: nil
            )
        }
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    @objc private func appDidBecomeActive() {
        self.drainQueueIfDue(force: true)
    }

    @objc func startTracking(_ call: CAPPluginCall) {
        guard let token = call.getString("authToken"),
              let url = call.getString("apiUrl") else {
            call.reject("authToken and apiUrl are required")
            return
        }

        self.authToken = token
        self.apiUrl = url
        if let intervalMs = call.getDouble("intervalMs"), intervalMs > 0 {
            self.uploadInterval = intervalMs / 1000.0
        }

        // Persist credentials for lifecycle recovery
        UserDefaults.standard.set(token, forKey: "myntos_bg_auth_token")
        UserDefaults.standard.set(url, forKey: "myntos_bg_api_url")
        UserDefaults.standard.set(self.uploadInterval, forKey: "myntos_bg_upload_interval")

        DispatchQueue.main.async {
            self.locationManager?.startUpdatingLocation()
            self.isTrackingLocation = true
            self.notifyStatusChange(isRunning: true, reason: "active")
            self.drainQueueIfDue(force: true)
            call.resolve([
                "success": true,
                "message": "iOS background location tracking active"
            ])
        }
    }

    @objc func stopTracking(_ call: CAPPluginCall) {
        UserDefaults.standard.removeObject(forKey: "myntos_bg_auth_token")
        UserDefaults.standard.removeObject(forKey: "myntos_bg_api_url")
        UserDefaults.standard.removeObject(forKey: "myntos_bg_upload_interval")

        DispatchQueue.main.async {
            self.locationManager?.stopUpdatingLocation()
            self.isTrackingLocation = false
            self.notifyStatusChange(isRunning: false, reason: "stopped")
            call.resolve([
                "success": true,
                "message": "iOS background location tracking stopped"
            ])
        }
    }

    @objc func isTracking(_ call: CAPPluginCall) {
        call.resolve([
            "isTracking": isTrackingLocation
        ])
    }

    @objc func updateInterval(_ call: CAPPluginCall) {
        if let intervalMs = call.getDouble("intervalMs"), intervalMs > 0 {
            self.uploadInterval = intervalMs / 1000.0
            UserDefaults.standard.set(self.uploadInterval, forKey: "myntos_bg_upload_interval")
        }
        call.resolve([
            "success": true,
            "intervalMs": Int(self.uploadInterval * 1000)
        ])
    }

    @objc func checkPermissions(_ call: CAPPluginCall) {
        let status = currentAuthorizationStatus()
        let fine = status == .authorizedAlways || status == .authorizedWhenInUse
        let bg = status == .authorizedAlways
        call.resolve([
            "fineLocation": fine,
            "coarseLocation": fine,
            "backgroundLocation": bg,
            "allGranted": bg,
            "status": authorizationStatusString(status)
        ])
    }

    @objc func requestPermissions(_ call: CAPPluginCall) {
        let currentStatus = currentAuthorizationStatus()
        if currentStatus != .notDetermined {
            // Already determined, resolve truthfully with current status
            let fine = currentStatus == .authorizedAlways || currentStatus == .authorizedWhenInUse
            let bg = currentStatus == .authorizedAlways
            call.resolve([
                "granted": fine || bg,
                "fineLocation": fine,
                "coarseLocation": fine,
                "backgroundLocation": bg,
                "allGranted": bg,
                "status": authorizationStatusString(currentStatus)
            ])
            return
        }

        self.pendingPermissionCall = call
        DispatchQueue.main.async {
            self.locationManager?.requestAlwaysAuthorization()
        }

        // Safety timeout: resolve if delegate callback is delayed or dismissed without change
        DispatchQueue.main.asyncAfter(deadline: .now() + 15.0) { [weak self] in
            guard let self = self, let pending = self.pendingPermissionCall else { return }
            self.pendingPermissionCall = nil
            let status = self.currentAuthorizationStatus()
            let fine = status == .authorizedAlways || status == .authorizedWhenInUse
            let bg = status == .authorizedAlways
            pending.resolve([
                "granted": fine || bg,
                "fineLocation": fine,
                "coarseLocation": fine,
                "backgroundLocation": bg,
                "allGranted": bg,
                "status": self.authorizationStatusString(status)
            ])
        }
    }

    private func currentAuthorizationStatus() -> CLAuthorizationStatus {
        if #available(iOS 14.0, *) {
            return locationManager?.authorizationStatus ?? .notDetermined
        } else {
            return CLLocationManager.authorizationStatus()
        }
    }

    private func authorizationStatusString(_ status: CLAuthorizationStatus) -> String {
        switch status {
        case .authorizedAlways: return "authorizedAlways"
        case .authorizedWhenInUse: return "authorizedWhenInUse"
        case .denied: return "denied"
        case .restricted: return "restricted"
        case .notDetermined: return "notDetermined"
        @unknown default: return "unknown"
        }
    }

    private func notifyStatusChange(isRunning: Bool, reason: String) {
        self.notifyListeners("serviceStatus", data: [
            "isRunning": isRunning,
            "reason": reason
        ])
    }

    // MARK: - CLLocationManagerDelegate Authorization Callbacks

    @available(iOS 14.0, *)
    public func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        handleAuthorizationChange(status: manager.authorizationStatus)
    }

    public func locationManager(_ manager: CLLocationManager, didChangeAuthorization status: CLAuthorizationStatus) {
        handleAuthorizationChange(status: status)
    }

    private func handleAuthorizationChange(status: CLAuthorizationStatus) {
        guard let call = self.pendingPermissionCall else { return }
        self.pendingPermissionCall = nil

        let fine = status == .authorizedAlways || status == .authorizedWhenInUse
        let bg = status == .authorizedAlways
        call.resolve([
            "granted": fine || bg,
            "fineLocation": fine,
            "coarseLocation": fine,
            "backgroundLocation": bg,
            "allGranted": bg,
            "status": authorizationStatusString(status)
        ])
    }

    // MARK: - CLLocationManagerDelegate Location Callback

    public func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }

        // INVARIANT: Exactly ONE UUIDv4 generated per physical fix
        let clientObsId = UUID().uuidString.lowercased()

        let lat = location.coordinate.latitude
        let lng = location.coordinate.longitude
        let acc = Float(location.horizontalAccuracy)
        let speed = Float(max(0, location.speed))
        let timestamp = Int64(location.timestamp.timeIntervalSince1970 * 1000)

        UIDevice.current.isBatteryMonitoringEnabled = true
        let battery = Float(UIDevice.current.batteryLevel * 100.0)
        let batteryPct = battery >= 0 ? battery : 100.0

        let obsRecord: [String: Any] = [
            "latitude": lat,
            "longitude": lng,
            "accuracy": acc,
            "speed": speed,
            "battery_level": batteryPct,
            "timestamp": timestamp,
            "source": "native_background",
            "client_observation_id": clientObsId
        ]

        // 1. Deliver to JS listeners if app is foreground/active
        self.notifyListeners("locationUpdate", data: [
            "latitude": lat,
            "longitude": lng,
            "accuracy": acc,
            "speed": speed,
            "batteryLevel": batteryPct,
            "timestamp": timestamp,
            "client_observation_id": clientObsId
        ])

        // 2. If in background, enqueue to persistent queue and attempt drain
        if UIApplication.shared.applicationState == .background {
            enqueueLocation(obsRecord)
            drainQueueIfDue(force: false)
        }
    }

    public func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("[DC_IOS_BG_LOC] Location error: \(error.localizedDescription)")
    }

    // MARK: - Persistent Queue & Atomic Lock Management

    private func enqueueLocation(_ record: [String: Any]) {
        queueLock.lock()
        defer { queueLock.unlock() }

        var items = loadQueueInternal()
        if let newId = record["client_observation_id"] as? String {
            // Deduplicate by client_observation_id
            if !items.contains(where: { ($0["client_observation_id"] as? String) == newId }) {
                items.append(record)
                saveQueueInternal(items)
            }
        } else {
            items.append(record)
            saveQueueInternal(items)
        }
    }

    private func removeObservationFromQueue(clientObservationId: String) {
        queueLock.lock()
        defer { queueLock.unlock() }

        var items = loadQueueInternal()
        items.removeAll { ($0["client_observation_id"] as? String) == clientObservationId }
        saveQueueInternal(items)
    }

    private func loadQueueInternal() -> [[String: Any]] {
        guard let data = try? Data(contentsOf: queueFilePath),
              let json = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] else {
            return []
        }
        return json
    }

    private func saveQueueInternal(_ items: [[String: Any]]) {
        guard let data = try? JSONSerialization.data(withJSONObject: items, options: []) else { return }
        try? data.write(to: queueFilePath, options: .atomic)
    }

    private func drainQueueIfDue(force: Bool = false) {
        let now = Date()
        if !force, let lastUp = lastUploadTime, now.timeIntervalSince(lastUp) < uploadInterval {
            return
        }

        queueLock.lock()
        if isDrainingQueue {
            queueLock.unlock()
            return
        }
        let items = loadQueueInternal()
        if items.isEmpty {
            queueLock.unlock()
            return
        }
        isDrainingQueue = true
        queueLock.unlock()

        guard let urlStr = apiUrl, let url = URL(string: urlStr),
              let token = authToken else {
            queueLock.lock()
            isDrainingQueue = false
            queueLock.unlock()
            return
        }

        lastUploadTime = now

        // Request background execution time from iOS to ensure upload completes
        var bgTask: UIBackgroundTaskIdentifier = .invalid
        bgTask = UIApplication.shared.beginBackgroundTask(withName: "MyntOS_BG_Upload") {
            UIApplication.shared.endBackgroundTask(bgTask)
            bgTask = .invalid
        }

        // Upload items sequentially to preserve chronological ordering
        uploadQueueSequentially(items: items, index: 0, url: url, token: token) { [weak self] in
            guard let self = self else { return }
            self.queueLock.lock()
            self.isDrainingQueue = false
            self.queueLock.unlock()

            if bgTask != .invalid {
                UIApplication.shared.endBackgroundTask(bgTask)
                bgTask = .invalid
            }
        }
    }

    private func uploadQueueSequentially(items: [[String: Any]], index: Int, url: URL, token: String, completion: @escaping () -> Void) {
        guard index < items.count else {
            completion()
            return
        }

        let record = items[index]
        guard let obsId = record["client_observation_id"] as? String else {
            // Malformed record missing ID, skip to next
            uploadQueueSequentially(items: items, index: index + 1, url: url, token: token, completion: completion)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("iOS_Native_Background", forHTTPHeaderField: "User-Agent")
        request.httpBody = try? JSONSerialization.data(withJSONObject: record, options: [])

        let task = URLSession.shared.dataTask(with: request) { [weak self] _, response, error in
            guard let self = self else { completion(); return }
            if let httpResp = response as? HTTPURLResponse, (200...299).contains(httpResp.statusCode) {
                // ATOMIC SUCCESS: Remove ONLY this acknowledged observation from disk queue
                self.removeObservationFromQueue(clientObservationId: obsId)
                // Proceed to upload next item in current snapshot
                self.uploadQueueSequentially(items: items, index: index + 1, url: url, token: token, completion: completion)
            } else {
                // FAILURE: Network unreachable or server error. Retain this record and all subsequent records in persistent queue.
                print("[DC_IOS_BG_LOC] Upload failed for \(obsId) (status: \((response as? HTTPURLResponse)?.statusCode ?? -1), err: \(error?.localizedDescription ?? "none")), retaining in queue for next drain")
                completion()
            }
        }
        task.resume()
    }
}
