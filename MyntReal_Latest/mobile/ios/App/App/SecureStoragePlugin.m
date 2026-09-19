#import <Capacitor/Capacitor.h>

CAP_PLUGIN(SecureStoragePlugin, "SecureStorage",
    CAP_PLUGIN_METHOD(setKey, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(getKey, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(removeKey, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(clear, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(getDeviceId, CAPPluginReturnPromise);
)
