package com.myntreal.mnr.plugins;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.provider.Settings;
import android.util.Log;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

@CapacitorPlugin(
    name = "BackgroundLocation",
    permissions = {
        @Permission(
            alias = "location",
            strings = {
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            }
        ),
        @Permission(
            alias = "backgroundLocation",
            strings = { Manifest.permission.ACCESS_BACKGROUND_LOCATION }
        )
    }
)
public class BackgroundLocationPlugin extends Plugin {
    private static final String TAG = "BackgroundLocationPlugin";
    
    public static final String ACTION_LOCATION_UPDATE = "com.myntreal.mnr.LOCATION_UPDATE";
    public static final String ACTION_SERVICE_STATUS = "com.myntreal.mnr.SERVICE_STATUS";
    
    private BroadcastReceiver locationReceiver;
    private boolean isReceiverRegistered = false;
    
    @Override
    public void load() {
        super.load();
        registerLocationReceiver();
        Log.d(TAG, "BackgroundLocationPlugin loaded");
    }
    
    private void registerLocationReceiver() {
        if (isReceiverRegistered) return;
        
        locationReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                String action = intent.getAction();
                if (ACTION_LOCATION_UPDATE.equals(action)) {
                    double latitude = intent.getDoubleExtra("latitude", 0);
                    double longitude = intent.getDoubleExtra("longitude", 0);
                    float accuracy = intent.getFloatExtra("accuracy", 0);
                    float speed = intent.getFloatExtra("speed", 0);
                    float batteryLevel = intent.getFloatExtra("batteryLevel", 100);
                    long timestamp = intent.getLongExtra("timestamp", System.currentTimeMillis());
                    
                    JSObject data = new JSObject();
                    data.put("latitude", latitude);
                    data.put("longitude", longitude);
                    data.put("accuracy", accuracy);
                    data.put("speed", speed);
                    data.put("batteryLevel", batteryLevel);
                    data.put("timestamp", timestamp);
                    
                    notifyListeners("locationUpdate", data);
                    Log.d(TAG, "Location update broadcast received: " + latitude + ", " + longitude);
                } else if (ACTION_SERVICE_STATUS.equals(action)) {
                    boolean isRunning = intent.getBooleanExtra("isRunning", false);
                    String reason = intent.getStringExtra("reason");
                    
                    JSObject data = new JSObject();
                    data.put("isRunning", isRunning);
                    data.put("reason", reason != null ? reason : "");
                    
                    notifyListeners("serviceStatus", data);
                    Log.d(TAG, "Service status changed: " + isRunning + " - " + reason);
                }
            }
        };
        
        IntentFilter filter = new IntentFilter();
        filter.addAction(ACTION_LOCATION_UPDATE);
        filter.addAction(ACTION_SERVICE_STATUS);
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            getContext().registerReceiver(locationReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            getContext().registerReceiver(locationReceiver, filter);
        }
        isReceiverRegistered = true;
        Log.d(TAG, "Location receiver registered");
    }
    
    @PluginMethod
    public void startTracking(PluginCall call) {
        Log.d(TAG, "startTracking called");
        
        if (!hasRequiredPermissions()) {
            call.reject("Location permissions not granted");
            return;
        }
        
        int intervalMs = call.getInt("intervalMs", 60000);
        String authToken = call.getString("authToken", "");
        String apiUrl = call.getString("apiUrl", "");
        String notificationTitle = call.getString("notificationTitle", "Location Tracking Active");
        String notificationText = call.getString("notificationText", "GPS tracking is running");
        
        Intent serviceIntent = new Intent(getContext(), BackgroundLocationService.class);
        serviceIntent.setAction(BackgroundLocationService.ACTION_START);
        serviceIntent.putExtra("intervalMs", intervalMs);
        serviceIntent.putExtra("authToken", authToken);
        serviceIntent.putExtra("apiUrl", apiUrl);
        serviceIntent.putExtra("notificationTitle", notificationTitle);
        serviceIntent.putExtra("notificationText", notificationText);
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getContext().startForegroundService(serviceIntent);
        } else {
            getContext().startService(serviceIntent);
        }
        
        JSObject result = new JSObject();
        result.put("success", true);
        result.put("message", "Background location tracking started");
        call.resolve(result);
    }
    
    @PluginMethod
    public void stopTracking(PluginCall call) {
        Log.d(TAG, "stopTracking called");
        
        Intent serviceIntent = new Intent(getContext(), BackgroundLocationService.class);
        serviceIntent.setAction(BackgroundLocationService.ACTION_STOP);
        getContext().startService(serviceIntent);
        
        JSObject result = new JSObject();
        result.put("success", true);
        result.put("message", "Background location tracking stopped");
        call.resolve(result);
    }
    
    @PluginMethod
    public void isTracking(PluginCall call) {
        boolean isRunning = BackgroundLocationService.isRunning();
        
        JSObject result = new JSObject();
        result.put("isTracking", isRunning);
        call.resolve(result);
    }
    
    @PluginMethod
    public void updateInterval(PluginCall call) {
        int intervalMs = call.getInt("intervalMs", 60000);
        
        Intent serviceIntent = new Intent(getContext(), BackgroundLocationService.class);
        serviceIntent.setAction(BackgroundLocationService.ACTION_UPDATE_INTERVAL);
        serviceIntent.putExtra("intervalMs", intervalMs);
        getContext().startService(serviceIntent);
        
        JSObject result = new JSObject();
        result.put("success", true);
        result.put("intervalMs", intervalMs);
        call.resolve(result);
    }
    
    @PluginMethod
    public void checkPermissions(PluginCall call) {
        JSObject result = new JSObject();
        
        boolean fineLocation = ContextCompat.checkSelfPermission(getContext(), 
            Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        boolean coarseLocation = ContextCompat.checkSelfPermission(getContext(),
            Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        boolean backgroundLocation = true;
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            backgroundLocation = ContextCompat.checkSelfPermission(getContext(),
                Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED;
        }
        
        result.put("fineLocation", fineLocation);
        result.put("coarseLocation", coarseLocation);
        result.put("backgroundLocation", backgroundLocation);
        result.put("allGranted", fineLocation && coarseLocation && backgroundLocation);
        
        call.resolve(result);
    }
    
    @PluginMethod
    public void requestPermissions(PluginCall call) {
        if (hasRequiredPermissions()) {
            JSObject result = new JSObject();
            result.put("granted", true);
            call.resolve(result);
            return;
        }
        
        requestPermissionForAlias("location", call, "locationPermissionCallback");
    }
    
    @PermissionCallback
    private void locationPermissionCallback(PluginCall call) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            boolean fineGranted = ContextCompat.checkSelfPermission(getContext(),
                Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
            
            if (fineGranted) {
                requestPermissionForAlias("backgroundLocation", call, "backgroundLocationPermissionCallback");
                return;
            }
        }
        
        JSObject result = new JSObject();
        result.put("granted", hasRequiredPermissions());
        call.resolve(result);
    }
    
    @PermissionCallback
    private void backgroundLocationPermissionCallback(PluginCall call) {
        JSObject result = new JSObject();
        result.put("granted", hasRequiredPermissions());
        call.resolve(result);
    }
    
    @Override
    public boolean hasRequiredPermissions() {
        boolean fineLocation = ContextCompat.checkSelfPermission(getContext(),
            Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        boolean coarseLocation = ContextCompat.checkSelfPermission(getContext(),
            Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            boolean backgroundLocation = ContextCompat.checkSelfPermission(getContext(),
                Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED;
            return fineLocation && coarseLocation && backgroundLocation;
        }
        
        return fineLocation && coarseLocation;
    }
    
    @PluginMethod
    public void isIgnoringBatteryOptimizations(PluginCall call) {
        JSObject result = new JSObject();
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager pm = (PowerManager) getContext().getSystemService(Context.POWER_SERVICE);
            boolean isIgnoring = pm.isIgnoringBatteryOptimizations(getContext().getPackageName());
            result.put("isIgnoring", isIgnoring);
        } else {
            result.put("isIgnoring", true);
        }
        
        call.resolve(result);
    }
    
    @PluginMethod
    public void requestBatteryOptimizationExemption(PluginCall call) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager pm = (PowerManager) getContext().getSystemService(Context.POWER_SERVICE);
            if (!pm.isIgnoringBatteryOptimizations(getContext().getPackageName())) {
                Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                intent.setData(Uri.parse("package:" + getContext().getPackageName()));
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(intent);
                
                JSObject result = new JSObject();
                result.put("requested", true);
                call.resolve(result);
                return;
            }
        }
        
        JSObject result = new JSObject();
        result.put("requested", false);
        result.put("alreadyExempt", true);
        call.resolve(result);
    }
    
    @Override
    protected void handleOnDestroy() {
        if (isReceiverRegistered && locationReceiver != null) {
            try {
                getContext().unregisterReceiver(locationReceiver);
            } catch (Exception e) {
                Log.e(TAG, "Error unregistering receiver", e);
            }
            isReceiverRegistered = false;
        }
        super.handleOnDestroy();
    }
}
