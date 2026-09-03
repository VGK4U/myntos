package com.myntos.mobile.plugins;

import android.content.Context;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;
import android.os.Build;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.util.List;

@CapacitorPlugin(name = "AudioRouting")
public class AudioRoutingPlugin extends Plugin {
    private static final String TAG = "AudioRoutingPlugin";
    private AudioManager audioManager;

    @Override
    public void load() {
        super.load();
        Context context = getContext();
        if (context != null) {
            audioManager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        }
        Log.d(TAG, "AudioRoutingPlugin loaded");
    }

    @PluginMethod
    public void setSpeakerphoneOn(PluginCall call) {
        Boolean enabled = call.getBoolean("enabled");
        if (enabled == null) {
            call.reject("Missing 'enabled' parameter");
            return;
        }

        if (audioManager == null) {
            Context context = getContext();
            if (context != null) {
                audioManager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            }
        }

        if (audioManager == null) {
            call.reject("AudioManager service unavailable");
            return;
        }

        try {
            if (enabled) {
                // Set audio mode for active VoIP communication
                audioManager.setMode(AudioManager.MODE_IN_COMMUNICATION);

                // Android 12+ (API 31+) modern communication device routing
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    List<AudioDeviceInfo> devices = audioManager.getAvailableCommunicationDevices();
                    AudioDeviceInfo speakerDevice = null;
                    for (AudioDeviceInfo device : devices) {
                        if (device.getType() == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
                            speakerDevice = device;
                            break;
                        }
                    }
                    if (speakerDevice != null) {
                        boolean res = audioManager.setCommunicationDevice(speakerDevice);
                        Log.d(TAG, "setCommunicationDevice(BUILTIN_SPEAKER) result: " + res);
                    } else {
                        audioManager.setSpeakerphoneOn(true);
                    }
                } else {
                    // Legacy Android fallback
                    audioManager.setSpeakerphoneOn(true);
                }
            } else {
                // Restore standard communication audio routing
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    audioManager.clearCommunicationDevice();
                }
                audioManager.setSpeakerphoneOn(false);
                audioManager.setMode(AudioManager.MODE_NORMAL);
            }

            JSObject ret = new JSObject();
            ret.put("success", true);
            ret.put("speakerOn", enabled);
            call.resolve(ret);
        } catch (Exception e) {
            Log.e(TAG, "Failed to set audio routing: " + e.getMessage(), e);
            call.reject("Failed to set audio routing: " + e.getMessage());
        }
    }

    @PluginMethod
    public void isSpeakerphoneOn(PluginCall call) {
        if (audioManager == null) {
            call.resolve(new JSObject().put("speakerOn", false));
            return;
        }
        boolean isSpeaker = false;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                AudioDeviceInfo commDevice = audioManager.getCommunicationDevice();
                if (commDevice != null && commDevice.getType() == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
                    isSpeaker = true;
                }
            }
            if (!isSpeaker) {
                isSpeaker = audioManager.isSpeakerphoneOn();
            }
        } catch (Exception e) {
            Log.w(TAG, "Error checking speakerphone status: " + e.getMessage());
        }
        JSObject ret = new JSObject();
        ret.put("speakerOn", isSpeaker);
        call.resolve(ret);
    }
}
