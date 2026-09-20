#import <Capacitor/Capacitor.h>

CAP_PLUGIN(IncomingCallPlugin, "IncomingCall",
    CAP_PLUGIN_METHOD(getPushToken, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(getPendingCall, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(clearPendingCall, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(dismissCallNotification, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(saveServerConfig, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(triggerTestIncomingCall, CAPPluginReturnPromise);
)
