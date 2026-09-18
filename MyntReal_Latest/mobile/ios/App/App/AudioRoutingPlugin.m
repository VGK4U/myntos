#import <Capacitor/Capacitor.h>

CAP_PLUGIN(AudioRoutingPlugin, "AudioRouting",
    CAP_PLUGIN_METHOD(setSpeakerphoneOn, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(isSpeakerphoneOn, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(resetAudioMode, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(startInCallService, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(stopInCallService, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(getAudioDiagnostics, CAPPluginReturnPromise);
)
