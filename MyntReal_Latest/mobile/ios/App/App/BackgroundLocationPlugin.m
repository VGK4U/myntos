#import <Capacitor/Capacitor.h>

CAP_PLUGIN(BackgroundLocationPlugin, "BackgroundLocation",
    CAP_PLUGIN_METHOD(startTracking, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(stopTracking, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(isTracking, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(updateInterval, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(checkPermissions, CAPPluginReturnPromise);
    CAP_PLUGIN_METHOD(requestPermissions, CAPPluginReturnPromise);
)
