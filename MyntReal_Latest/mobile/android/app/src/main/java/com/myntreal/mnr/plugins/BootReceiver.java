package com.myntreal.mnr.plugins;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.util.Base64;
import android.util.Log;

import org.json.JSONObject;

public class BootReceiver extends BroadcastReceiver {
    private static final String TAG = "MNRBootReceiver";
    private static final String PREFS_NAME = "mnr_background_location";
    private static final String KEY_WAS_TRACKING = "was_tracking";
    private static final String KEY_AUTH_TOKEN = "auth_token";
    private static final String KEY_API_URL = "api_url";
    private static final String KEY_INTERVAL_MS = "interval_ms";
    
    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) return;
        
        String action = intent.getAction();
        Log.d(TAG, "Received broadcast: " + action);
        
        if (Intent.ACTION_BOOT_COMPLETED.equals(action) || 
            Intent.ACTION_MY_PACKAGE_REPLACED.equals(action) ||
            "android.intent.action.QUICKBOOT_POWERON".equals(action)) {
            
            SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            boolean wasTracking = prefs.getBoolean(KEY_WAS_TRACKING, false);
            
            if (wasTracking) {
                Log.d(TAG, "Device booted while tracking was active - restarting service");
                restartTrackingService(context, prefs);
            } else {
                Log.d(TAG, "Device booted but tracking was not active - no action needed");
            }
        }
    }
    
    private boolean isTokenExpired(String token) {
        try {
            String[] parts = token.split("\\.");
            if (parts.length < 2) return true;
            String payload = new String(Base64.decode(parts[1], Base64.URL_SAFE | Base64.NO_WRAP));
            JSONObject json = new JSONObject(payload);
            long exp = json.optLong("exp", 0);
            if (exp == 0) return true;
            long nowSeconds = System.currentTimeMillis() / 1000;
            return nowSeconds >= exp;
        } catch (Exception e) {
            Log.w(TAG, "Failed to decode JWT expiry, treating as expired", e);
            return true;
        }
    }
    
    private void restartTrackingService(Context context, SharedPreferences prefs) {
        String authToken = prefs.getString(KEY_AUTH_TOKEN, "");
        String apiUrl = prefs.getString(KEY_API_URL, "");
        int intervalMs = prefs.getInt(KEY_INTERVAL_MS, 60000);
        
        if (authToken.isEmpty() || apiUrl.isEmpty()) {
            Log.w(TAG, "Cannot restart tracking - missing auth token or API URL");
            return;
        }
        
        if (isTokenExpired(authToken)) {
            Log.w(TAG, "Auth token expired - clearing tracking state instead of restarting");
            clearTrackingState(context);
            return;
        }
        
        Intent serviceIntent = new Intent(context, BackgroundLocationService.class);
        serviceIntent.setAction(BackgroundLocationService.ACTION_START);
        serviceIntent.putExtra("intervalMs", intervalMs);
        serviceIntent.putExtra("authToken", authToken);
        serviceIntent.putExtra("apiUrl", apiUrl);
        serviceIntent.putExtra("notificationTitle", "MNR Location Tracking");
        serviceIntent.putExtra("notificationText", "GPS tracking resumed after restart");
        serviceIntent.putExtra("isBootRestart", true);
        
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent);
            } else {
                context.startService(serviceIntent);
            }
            Log.d(TAG, "Tracking service restarted successfully");
        } catch (Exception e) {
            Log.e(TAG, "Failed to restart tracking service", e);
        }
    }
    
    public static void saveTrackingState(Context context, boolean isTracking, 
                                          String authToken, String apiUrl, int intervalMs) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();
        editor.putBoolean(KEY_WAS_TRACKING, isTracking);
        if (isTracking) {
            editor.putString(KEY_AUTH_TOKEN, authToken);
            editor.putString(KEY_API_URL, apiUrl);
            editor.putInt(KEY_INTERVAL_MS, intervalMs);
        } else {
            editor.remove(KEY_AUTH_TOKEN);
            editor.remove(KEY_API_URL);
        }
        editor.apply();
        Log.d(TAG, "Saved tracking state: " + isTracking);
    }
    
    public static void clearTrackingState(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().clear().apply();
        Log.d(TAG, "Cleared tracking state");
    }
}
