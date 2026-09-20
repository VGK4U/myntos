package com.myntos.mobile.plugins;

import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.AudioDeviceInfo;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.os.Build;
import android.util.Log;

import com.getcapacitor.JSArray;
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
    private AudioFocusRequest audioFocusRequest = null;
    private boolean hasVoiceAudioFocus = false;
    private String currentDeviceRoute = "DEFAULT";

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

    private synchronized void requestVoiceAudioFocus(AudioManager am) {
        if (am == null || hasVoiceAudioFocus) return;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (audioFocusRequest == null) {
                    AudioAttributes playbackAttributes = new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build();
                    audioFocusRequest = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                        .setAudioAttributes(playbackAttributes)
                        .setAcceptsDelayedFocusGain(true)
                        .setOnAudioFocusChangeListener(focusChange -> {
                            Log.d(TAG, "[AudioRouting] Voice AudioFocus changed: " + focusChange);
                            if (focusChange == AudioManager.AUDIOFOCUS_LOSS) {
                                hasVoiceAudioFocus = false;
                            }
                        })
                        .build();
                }
                int res = am.requestAudioFocus(audioFocusRequest);
                hasVoiceAudioFocus = (res == AudioManager.AUDIOFOCUS_REQUEST_GRANTED);
            } else {
                int res = am.requestAudioFocus(null, AudioManager.STREAM_VOICE_CALL, AudioManager.AUDIOFOCUS_GAIN);
                hasVoiceAudioFocus = (res == AudioManager.AUDIOFOCUS_REQUEST_GRANTED);
            }
            Log.d(TAG, "[AudioRouting] Voice AudioFocus request granted: " + hasVoiceAudioFocus);
        } catch (Exception e) {
            Log.w(TAG, "[AudioRouting] Notice requesting voice AudioFocus: " + e.getMessage());
        }
    }

    private synchronized void abandonVoiceAudioFocus(AudioManager am) {
        if (am == null) return;
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (audioFocusRequest != null) {
                    am.abandonAudioFocusRequest(audioFocusRequest);
                    audioFocusRequest = null;
                }
            } else {
                am.abandonAudioFocus(null);
            }
            hasVoiceAudioFocus = false;
            Log.d(TAG, "[AudioRouting] Voice AudioFocus abandoned cleanly");
        } catch (Exception e) {
            Log.w(TAG, "[AudioRouting] Notice abandoning AudioFocus: " + e.getMessage());
        }
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
            // 1. Acquire voice communication audio focus so Android AudioPolicy routes WebView to in-call stream
            requestVoiceAudioFocus(am);

            // 2. Assert MODE_IN_COMMUNICATION for call audio routing and hardware AEC
            if (am.getMode() != AudioManager.MODE_IN_COMMUNICATION) {
                am.setMode(AudioManager.MODE_IN_COMMUNICATION);
            }
            am.setMicrophoneMute(false);

            if (enabled) {
                // Route audio to external loudspeaker
                am.setSpeakerphoneOn(true);
                currentDeviceRoute = "BUILTIN_SPEAKER";
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    am.clearCommunicationDevice();
                    List<AudioDeviceInfo> devices = am.getAvailableCommunicationDevices();
                    for (AudioDeviceInfo device : devices) {
                        if (device.getType() == AudioDeviceInfo.TYPE_BUILTIN_SPEAKER) {
                            boolean res = am.setCommunicationDevice(device);
                            Log.d(TAG, "[AudioRouting] Set communication device to SPEAKER: " + res);
                            break;
                        }
                    }
                }
            } else {
                // Route audio to normal in-call EARPIECE or connected headset (Wired > Bluetooth > Builtin Earpiece)
                am.setSpeakerphoneOn(false);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    am.clearCommunicationDevice();
                    List<AudioDeviceInfo> devices = am.getAvailableCommunicationDevices();
                    AudioDeviceInfo selectedDevice = null;
                    String selectedType = "DEFAULT_COMMUNICATION";

                    // Priority 1: Connected Wired Headset / Headphones / USB Headset
                    for (AudioDeviceInfo d : devices) {
                        int t = d.getType();
                        if (t == AudioDeviceInfo.TYPE_WIRED_HEADSET || t == AudioDeviceInfo.TYPE_WIRED_HEADPHONES || t == AudioDeviceInfo.TYPE_USB_HEADSET) {
                            selectedDevice = d;
                            selectedType = "WIRED_HEADSET";
                            break;
                        }
                    }

                    // Priority 2: Connected Bluetooth Headset (SCO or BLE)
                    if (selectedDevice == null) {
                        for (AudioDeviceInfo d : devices) {
                            int t = d.getType();
                            if (t == AudioDeviceInfo.TYPE_BLUETOOTH_SCO || t == AudioDeviceInfo.TYPE_BLE_HEADSET) {
                                selectedDevice = d;
                                selectedType = "BLUETOOTH_HEADSET";
                                break;
                            }
                        }
                    }

                    // Priority 3: Built-in Phone Earpiece (Front conversational receiver)
                    if (selectedDevice == null) {
                        for (AudioDeviceInfo d : devices) {
                            if (d.getType() == AudioDeviceInfo.TYPE_BUILTIN_EARPIECE) {
                                selectedDevice = d;
                                selectedType = "BUILTIN_EARPIECE";
                                break;
                            }
                        }
                    }

                    if (selectedDevice != null) {
                        boolean res = am.setCommunicationDevice(selectedDevice);
                        currentDeviceRoute = selectedType;
                        Log.d(TAG, "[AudioRouting] Set communication device to " + selectedType + ": " + res);
                    } else {
                        currentDeviceRoute = "EARPIECE_FALLBACK";
                        Log.d(TAG, "[AudioRouting] Retaining default communication device route for earpiece.");
                    }
                } else {
                    currentDeviceRoute = "LEGACY_EARPIECE";
                }
            }

            JSObject ret = new JSObject();
            ret.put("success", true);
            ret.put("speakerOn", enabled);
            ret.put("deviceRoute", currentDeviceRoute);
            ret.put("hasVoiceAudioFocus", hasVoiceAudioFocus);
            call.resolve(ret);
        } catch (Exception e) {
            Log.e(TAG, "[AudioRouting] Failed to set audio routing: " + e.getMessage(), e);
            call.reject("Failed to set audio routing: " + e.getMessage());
        }
    }

    @PluginMethod
    public void resetAudioMode(PluginCall call) {
        try {
            // Stop foreground in-call service as fail-safe when audio resets
            try {
                Context context = getContext();
                if (context != null) {
                    Intent intent = new Intent(context, InCallService.class);
                    intent.setAction(InCallService.ACTION_STOP);
                    context.stopService(intent);
                }
            } catch (Exception e) {
                Log.w(TAG, "Notice stopping in-call service during reset: " + e.getMessage());
            }

            AudioManager am = getAudioManager();
            if (am != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    am.clearCommunicationDevice();
                }
                am.setSpeakerphoneOn(false);
                am.setMicrophoneMute(false);
                am.setMode(AudioManager.MODE_NORMAL);
                abandonVoiceAudioFocus(am);
                currentDeviceRoute = "MODE_NORMAL";
                Log.d(TAG, "[AudioRouting] Audio mode reset to MODE_NORMAL and AudioFocus released");
            }
            call.resolve(new JSObject().put("success", true));
        } catch (Exception e) {
            Log.e(TAG, "[AudioRouting] Failed to reset audio mode: " + e.getMessage(), e);
            call.reject("Failed to reset audio mode: " + e.getMessage());
        }
    }

    @PluginMethod
    public void setMediaPlaybackMode(PluginCall call) {
        try {
            AudioManager am = getAudioManager();
            if (am != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    am.clearCommunicationDevice();
                }
                am.setSpeakerphoneOn(false);
                am.setMicrophoneMute(false);
                am.setMode(AudioManager.MODE_NORMAL);
                abandonVoiceAudioFocus(am);
                currentDeviceRoute = "MODE_NORMAL";
                Log.d(TAG, "[AudioRouting] Media playback mode set: MODE_NORMAL for loud audio");
            }
            call.resolve(new JSObject().put("success", true).put("mode", "MODE_NORMAL"));
        } catch (Exception e) {
            Log.e(TAG, "[AudioRouting] Failed to set media playback mode: " + e.getMessage(), e);
            call.reject("Failed to set media playback mode: " + e.getMessage());
        }
    }

    @PluginMethod
    public void startInCallService(PluginCall call) {
        try {
            Context context = getContext();
            if (context == null) {
                call.reject("Context unavailable");
                return;
            }
            String title = call.getString("title", "Active Softphone Call");
            String text = call.getString("text", "Call in progress...");

            Intent intent = new Intent(context, InCallService.class);
            intent.setAction(InCallService.ACTION_START);
            intent.putExtra("title", title);
            intent.putExtra("text", text);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
            Log.d(TAG, "InCallService start requested");
            JSObject ret = new JSObject();
            ret.put("success", true);
            call.resolve(ret);
        } catch (Exception e) {
            Log.e(TAG, "Failed to start InCallService: " + e.getMessage(), e);
            call.reject("Failed to start InCallService: " + e.getMessage());
        }
    }

    @PluginMethod
    public void stopInCallService(PluginCall call) {
        try {
            Context context = getContext();
            if (context != null) {
                Intent intent = new Intent(context, InCallService.class);
                intent.setAction(InCallService.ACTION_STOP);
                context.stopService(intent);
            }
            Log.d(TAG, "InCallService stop requested");
            if (call != null) {
                JSObject ret = new JSObject();
                ret.put("success", true);
                call.resolve(ret);
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to stop InCallService: " + e.getMessage(), e);
            if (call != null) {
                call.reject("Failed to stop InCallService: " + e.getMessage());
            }
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

    @PluginMethod
    public void getAudioDiagnostics(PluginCall call) {
        AudioManager am = getAudioManager();
        JSObject ret = new JSObject();
        if (am == null) {
            ret.put("error", "AudioManager unavailable");
            call.resolve(ret);
            return;
        }

        try {
            ret.put("audioMode", am.getMode());
            ret.put("speakerOn", am.isSpeakerphoneOn());
            ret.put("micMute", am.isMicrophoneMute());
            ret.put("currentDeviceRoute", currentDeviceRoute);
            ret.put("hasVoiceAudioFocus", hasVoiceAudioFocus);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                AudioDeviceInfo comm = am.getCommunicationDevice();
                if (comm != null) {
                    ret.put("commDeviceType", comm.getType());
                    ret.put("commDeviceName", comm.getProductName().toString());
                } else {
                    ret.put("commDeviceType", null);
                    ret.put("commDeviceName", "NONE");
                }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                JSArray devList = new JSArray();
                AudioDeviceInfo[] devices = am.getDevices(AudioManager.GET_DEVICES_OUTPUTS);
                for (AudioDeviceInfo d : devices) {
                    JSObject devObj = new JSObject();
                    devObj.put("id", d.getId());
                    devObj.put("type", d.getType());
                    devObj.put("productName", d.getProductName().toString());
                    devList.put(devObj);
                }
                ret.put("availableOutputs", devList);
            }
            call.resolve(ret);
        } catch (Exception e) {
            Log.e(TAG, "[AudioRouting] Error collecting diagnostics: " + e.getMessage(), e);
            ret.put("error", e.getMessage());
            call.resolve(ret);
        }
    }
}
