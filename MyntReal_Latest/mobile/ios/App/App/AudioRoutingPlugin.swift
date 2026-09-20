import Foundation
import AVFoundation
import Capacitor

@objc(AudioRoutingPlugin)
public class AudioRoutingPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "AudioRoutingPlugin"
    public let jsName = "AudioRouting"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "setSpeakerphoneOn", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "isSpeakerphoneOn", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "resetAudioMode", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "setMediaPlaybackMode", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "startInCallService", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "stopInCallService", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "getAudioDiagnostics", returnType: CAPPluginReturnPromise)
    ]

    @objc func setSpeakerphoneOn(_ call: CAPPluginCall) {
        let enabled = call.getBool("enabled") ?? false
        do {
            let session = AVAudioSession.sharedInstance()
            if enabled {
                try session.overrideOutputAudioPort(.speaker)
                NSLog("[AudioRoutingPlugin] iOS speaker overridden to SPEAKER")
                call.resolve([
                    "success": true,
                    "speakerOn": true,
                    "deviceRoute": "BUILTIN_SPEAKER"
                ])
            } else {
                try session.overrideOutputAudioPort(.none)
                NSLog("[AudioRoutingPlugin] iOS speaker reset to DEFAULT/RECEIVER")
                call.resolve([
                    "success": true,
                    "speakerOn": false,
                    "deviceRoute": "BUILTIN_EARPIECE"
                ])
            }
        } catch {
            NSLog("[AudioRoutingPlugin] Error setting speaker route: \(error)")
            call.reject("Failed to set audio routing: \(error.localizedDescription)")
        }
    }

    @objc func isSpeakerphoneOn(_ call: CAPPluginCall) {
        let session = AVAudioSession.sharedInstance()
        var isSpeaker = false
        for output in session.currentRoute.outputs {
            if output.portType == .builtInSpeaker {
                isSpeaker = true
                break
            }
        }
        call.resolve([
            "speakerOn": isSpeaker
        ])
    }

    @objc func resetAudioMode(_ call: CAPPluginCall) {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try? session.overrideOutputAudioPort(.speaker)
            try session.setActive(true)
            NSLog("[AudioRoutingPlugin] iOS resetAudioMode: routed to loud speaker")
            call.resolve([
                "success": true,
                "deviceRoute": "BUILTIN_SPEAKER"
            ])
        } catch {
            NSLog("[AudioRoutingPlugin] Failed to reset audio mode: \(error.localizedDescription)")
            call.reject("Failed to reset audio mode: \(error.localizedDescription)")
        }
    }

    @objc func setMediaPlaybackMode(_ call: CAPPluginCall) {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try? session.overrideOutputAudioPort(.speaker)
            try session.setActive(true)
            NSLog("[AudioRoutingPlugin] iOS setMediaPlaybackMode: routed to loud speaker")
            call.resolve([
                "success": true,
                "deviceRoute": "BUILTIN_SPEAKER"
            ])
        } catch {
            NSLog("[AudioRoutingPlugin] Failed to set media playback mode: \(error.localizedDescription)")
            call.reject("Failed to set media playback mode: \(error.localizedDescription)")
        }
    }

    @objc func startInCallService(_ call: CAPPluginCall) {
        // No-op on iOS (handled by AVAudioSession VoIP background category)
        call.resolve(["success": true])
    }

    @objc func stopInCallService(_ call: CAPPluginCall) {
        // No-op on iOS
        call.resolve(["success": true])
    }

    @objc func getAudioDiagnostics(_ call: CAPPluginCall) {
        let session = AVAudioSession.sharedInstance()
        var isSpeaker = false
        var outputsList: [[String: Any]] = []

        for output in session.currentRoute.outputs {
            if output.portType == .builtInSpeaker {
                isSpeaker = true
            }
            outputsList.append([
                "portName": output.portName,
                "portType": output.portType.rawValue
            ])
        }

        call.resolve([
            "category": session.category.rawValue,
            "mode": session.mode.rawValue,
            "speakerOn": isSpeaker,
            "currentOutputs": outputsList
        ])
    }
}
