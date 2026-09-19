import Foundation
import Capacitor
import Security

@objc(SecureStoragePlugin)
public class SecureStoragePlugin: CAPPlugin {
    private let serviceName = "com.myntos.mobile.keychain"

    @objc func setKey(_ call: CAPPluginCall) {
        guard let key = call.getString("key"), !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              let value = call.getString("value") else {
            call.reject("Key and value are required")
            return
        }

        guard let data = value.data(using: .utf8) else {
            call.reject("Failed to encode value")
            return
        }

        // Delete existing item first
        let queryDelete: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: key
        ]
        SecItemDelete(queryDelete as CFDictionary)

        // Add new item with device-only hardware protection
        let queryAdd: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]

        let status = SecItemAdd(queryAdd as CFDictionary, nil)
        if status == errSecSuccess {
            call.resolve(["success": true])
        } else {
            call.reject("Keychain error: \(status)")
        }
    }

    @objc func getKey(_ call: CAPPluginCall) {
        guard let key = call.getString("key"), !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            call.reject("Key is required")
            return
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)

        if status == errSecSuccess, let data = dataTypeRef as? Data, let value = String(data: data, encoding: .utf8) {
            call.resolve(["value": value])
        } else {
            call.resolve(["value": NSNull()])
        }
    }

    @objc func removeKey(_ call: CAPPluginCall) {
        guard let key = call.getString("key"), !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            call.reject("Key is required")
            return
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: key
        ]

        SecItemDelete(query as CFDictionary)
        call.resolve(["success": true])
    }

    @objc func clear(_ call: CAPPluginCall) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName
        ]

        SecItemDelete(query as CFDictionary)
        call.resolve(["success": true])
    }

    @objc func getDeviceId(_ call: CAPPluginCall) {
        let key = "device_id"
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)

        if status == errSecSuccess, let data = dataTypeRef as? Data, let existingId = String(data: data, encoding: .utf8), !existingId.isEmpty {
            call.resolve(["deviceId": existingId])
            return
        }

        let newDeviceId = "ios_" + UUID().uuidString
        if let data = newDeviceId.data(using: .utf8) {
            let addQuery: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: serviceName,
                kSecAttrAccount as String: key,
                kSecValueData as String: data,
                kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            ]
            SecItemAdd(addQuery as CFDictionary, nil)
        }
        call.resolve(["deviceId": newDeviceId])
    }
}
