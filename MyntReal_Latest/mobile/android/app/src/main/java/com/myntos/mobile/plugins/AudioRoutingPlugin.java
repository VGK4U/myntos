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

    private AudioManager getAudioManager() {
        if (audioManager == null) {
            Context context = getContext();
            if (context != null) {
                audioManager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
            }
        }
        return audioManager;
    }

    @Override
    public void load() {
        super.load();
        getAudioManager();
        Log.d(TAG, "AudioRoutingPlugin loaded");
    }

    @PluginMethod
    public void setSpeakerphoneOn(PluginCall call) {
        Boolean enabled = call.getBoolean("enabled");
        if (enabled == null) {
            call.reject("Missing 'enabled' parameter");
            return;
        }

        AudioManager am = getAudioManager();
        if (am == null) {
            call.reject("AudioManager service unavailable");
            return;
        }

        try {
            // Assert MODE_IN_COMMUNICATION for call audio routing and AEC
            if (am.getMode() != AudioManager.MODE_IN_COMMUNICATION) {
                am.setMode(AudioManager.MODE_IN_COMMUNICATION);
            }
            am.setMicrophoneMute(false);

            if (enabled) {
                // Route audio to external loudspeaker
                am.setSpeakerphoneOn(true);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    List<AudioDeviceInfo> devices = am.getAvailableCommunicationDevices();
                    for (AudioDeviceInfo device : devices) {
                        if (device.getType() == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
                            boolean res = am.setCommunicationDevice(device);
                            Log.d(TAG, "Set communication device to SPEAKER: " + res);
                            break;
                        }
                    }
                }
            } else {
                // Route audio to normal in-call EARPIECE (default during call)
                am.setSpeakerphoneOn(false);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    // Always clear first so any forced speaker route is dropped
                    am.clearCommunicationDevice();
                    List<AudioDeviceInfo> devices = am.getAvailableCommunicationDevices();
                    boolean foundEarpiece = false;
                    for (AudioDeviceInfo device : devices) {
                        if (device.getType() == AudioDeviceInfo.TYPE_BUILTIN_EARPIECE) {
                            boolean res = am.setCommunicationDevice(device);
                            Log.d(TAG, "Set communication device to EARPIECE: " + res);
                            foundEarpiece = true;
                            break;
                        }
                    }
                    if (!foundEarpiece) {
                        Log.d(TAG, "No builtin earpiece device found; default communication device retained.");
                    }
                }
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
    public void resetAudioMode(PluginCall call) {
        try {
            AudioManager am = getAudioManager();
            if (am != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    am.clearCommunicationDevice();
                }
                am.setSpeakerphoneOn(false);
                am.setMicrophoneMute(false);
                am.setMode(AudioManager.MODE_NORMAL);
                Log.d(TAG, "Audio mode reset to MODE_NORMAL");
            }
            call.resolve(new JSObject().put("success", true));
        } catch (Exception e) {
            Log.e(TAG, "Failed to reset audio mode: " + e.getMessage(), e);
            call.reject("Failed to reset audio mode: " + e.getMessage());
        }
    }

    @PluginMethod
    public void isSpeakerphoneOn(PluginCall call) {
        AudioManager am = getAudioManager();
        if (am == null) {
            call.resolve(new JSObject().put("speakerOn", false));
            return;
        }
        boolean isSpeaker = false;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                AudioDeviceInfo commDevice = am.getCommunicationDevice();
                if (commDevice != null && commDevice.getType() == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
                    isSpeaker = true;
                }
            }
            if (!isSpeaker) {
                isSpeaker = am.isSpeakerphoneOn();
            }
        } catch (Exception e) {
            Log.w(TAG, "Error checking speakerphone status: " + e.getMessage());
        }
        JSObject ret = new JSObject();
        ret.put("speakerOn", isSpeaker);
        call.resolve(ret);
    }
}
