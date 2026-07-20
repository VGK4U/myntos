package com.myntreal.mnr.plugins;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.location.Location;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationCallback;
import com.google.android.gms.location.LocationRequest;
import com.google.android.gms.location.LocationResult;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;

import com.myntreal.mnr.MainActivity;
import com.myntreal.mnr.R;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class BackgroundLocationService extends Service {
    private static final String TAG = "BackgroundLocationSvc";
    private static final String CHANNEL_ID = "mnr_location_tracking";
    private static final int NOTIFICATION_ID = 1001;
    
    public static final String ACTION_START = "com.myntreal.mnr.START_TRACKING";
    public static final String ACTION_STOP = "com.myntreal.mnr.STOP_TRACKING";
    public static final String ACTION_UPDATE_INTERVAL = "com.myntreal.mnr.UPDATE_INTERVAL";
    
    private static volatile boolean isServiceRunning = false;
    
    private FusedLocationProviderClient fusedLocationClient;
    private LocationCallback locationCallback;
    private OkHttpClient httpClient;
    private Handler handler;
    private PowerManager.WakeLock wakeLock;
    
    private String authToken = "";
    private String apiUrl = "";
    private int intervalMs = 60000;
    private String notificationTitle = "Location Tracking Active";
    private String notificationText = "GPS tracking is running";
    
    private Location lastLocation;
    private long lastSentTimestamp = 0;
    private int consecutive401Count = 0;
    private static final int MAX_401_BEFORE_STOP = 3;
    
    public static boolean isRunning() {
        return isServiceRunning;
    }
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "Service onCreate");
        
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this);
        handler = new Handler(Looper.getMainLooper());
        
        httpClient = new OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build();
        
        createNotificationChannel();
        initLocationCallback();
        acquireWakeLock();
    }
    
    private void acquireWakeLock() {
        if (wakeLock == null) {
            PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
            wakeLock = powerManager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "MNR::LocationTrackingWakeLock"
            );
            wakeLock.acquire();
            Log.d(TAG, "WakeLock acquired");
        }
    }
    
    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
            wakeLock = null;
            Log.d(TAG, "WakeLock released");
        }
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            Log.w(TAG, "onStartCommand with null intent");
            return START_STICKY;
        }
        
        String action = intent.getAction();
        Log.d(TAG, "onStartCommand action: " + action);
        
        if (ACTION_START.equals(action)) {
            intervalMs = intent.getIntExtra("intervalMs", 60000);
            authToken = intent.getStringExtra("authToken");
            apiUrl = intent.getStringExtra("apiUrl");
            notificationTitle = intent.getStringExtra("notificationTitle");
            notificationText = intent.getStringExtra("notificationText");
            boolean isBootRestart = intent.getBooleanExtra("isBootRestart", false);
            
            if (notificationTitle == null) notificationTitle = "Location Tracking Active";
            if (notificationText == null) notificationText = "GPS tracking is running";
            
            startForeground(NOTIFICATION_ID, createNotification());
            startLocationUpdates();
            isServiceRunning = true;
            
            BootReceiver.saveTrackingState(this, true, authToken, apiUrl, intervalMs);
            
            if (isBootRestart) {
                reportOfflinePeriod("device_reboot", "Tracking resumed after device restart");
            }
            
            broadcastServiceStatus(true, "started");
            
        } else if (ACTION_STOP.equals(action)) {
            stopLocationUpdates();
            isServiceRunning = false;
            
            BootReceiver.clearTrackingState(this);
            
            broadcastServiceStatus(false, "stopped");
            stopForeground(true);
            stopSelf();
            
        } else if (ACTION_UPDATE_INTERVAL.equals(action)) {
            int newInterval = intent.getIntExtra("intervalMs", intervalMs);
            if (newInterval != intervalMs) {
                intervalMs = newInterval;
                restartLocationUpdates();
                Log.d(TAG, "Interval updated to: " + intervalMs + "ms");
            }
        }
        
        return START_STICKY;
    }
    
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Location Tracking",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Background location tracking for attendance");
            channel.setShowBadge(false);
            channel.enableVibration(false);
            channel.setSound(null, null);
            
            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.createNotificationChannel(channel);
            Log.d(TAG, "Notification channel created");
        }
    }
    
    private Notification createNotification() {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        notificationIntent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        
        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        }
        
        PendingIntent pendingIntent = PendingIntent.getActivity(
            this, 0, notificationIntent, pendingFlags
        );
        
        Intent stopIntent = new Intent(this, BackgroundLocationService.class);
        stopIntent.setAction(ACTION_STOP);
        PendingIntent stopPendingIntent = PendingIntent.getService(
            this, 1, stopIntent, pendingFlags
        );
        
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(notificationTitle)
            .setContentText(notificationText)
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop Tracking", stopPendingIntent);
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            builder.setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE);
        }
        
        return builder.build();
    }
    
    private void initLocationCallback() {
        locationCallback = new LocationCallback() {
            @Override
            public void onLocationResult(@NonNull LocationResult locationResult) {
                Location location = locationResult.getLastLocation();
                if (location != null) {
                    lastLocation = location;
                    handleLocationUpdate(location);
                }
            }
        };
    }
    
    private void startLocationUpdates() {
        try {
            LocationRequest locationRequest = new LocationRequest.Builder(
                Priority.PRIORITY_HIGH_ACCURACY, intervalMs
            )
                .setMinUpdateIntervalMillis(intervalMs / 2)
                .setMaxUpdateDelayMillis(intervalMs * 2)
                .setWaitForAccurateLocation(false)
                .build();
            
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                Looper.getMainLooper()
            );
            
            Log.d(TAG, "Location updates started with interval: " + intervalMs + "ms");
        } catch (SecurityException e) {
            Log.e(TAG, "Location permission not granted", e);
            broadcastServiceStatus(false, "permission_denied");
            stopSelf();
        }
    }
    
    private void stopLocationUpdates() {
        if (fusedLocationClient != null && locationCallback != null) {
            fusedLocationClient.removeLocationUpdates(locationCallback);
            Log.d(TAG, "Location updates stopped");
        }
    }
    
    private void restartLocationUpdates() {
        stopLocationUpdates();
        startLocationUpdates();
    }
    
    private void handleLocationUpdate(Location location) {
        double latitude = location.getLatitude();
        double longitude = location.getLongitude();
        float accuracy = location.getAccuracy();
        float speed = location.getSpeed();
        float batteryLevel = getBatteryLevel();
        long timestamp = System.currentTimeMillis();
        
        Log.d(TAG, String.format(
            "Location update: lat=%.6f, lng=%.6f, acc=%.1fm, battery=%.0f%%",
            latitude, longitude, accuracy, batteryLevel
        ));
        
        Intent updateIntent = new Intent(BackgroundLocationPlugin.ACTION_LOCATION_UPDATE);
        updateIntent.putExtra("latitude", latitude);
        updateIntent.putExtra("longitude", longitude);
        updateIntent.putExtra("accuracy", accuracy);
        updateIntent.putExtra("speed", speed);
        updateIntent.putExtra("batteryLevel", batteryLevel);
        updateIntent.putExtra("timestamp", timestamp);
        sendBroadcast(updateIntent);
        
        long timeSinceLastSend = timestamp - lastSentTimestamp;
        if (timeSinceLastSend >= intervalMs - 5000) {
            sendLocationToBackend(latitude, longitude, accuracy, speed, batteryLevel, timestamp);
            lastSentTimestamp = timestamp;
        }
    }
    
    private float getBatteryLevel() {
        IntentFilter filter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
        Intent batteryStatus = registerReceiver(null, filter);
        
        if (batteryStatus != null) {
            int level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
            if (level >= 0 && scale > 0) {
                return (level * 100f) / scale;
            }
        }
        return 100f;
    }
    
    private void sendLocationToBackend(double lat, double lng, float accuracy, 
                                        float speed, float batteryLevel, long timestamp) {
        if (apiUrl == null || apiUrl.isEmpty() || authToken == null || authToken.isEmpty()) {
            Log.w(TAG, "API URL or auth token not configured, skipping backend send");
            return;
        }
        
        String json = String.format(
            "{\"latitude\": %.8f, \"longitude\": %.8f, \"accuracy\": %.2f, \"speed\": %.2f, \"battery_level\": %.0f, \"timestamp\": %d, \"source\": \"native_background\"}",
            lat, lng, accuracy, speed, batteryLevel, timestamp
        );
        
        RequestBody body = RequestBody.create(json, MediaType.parse("application/json"));
        
        Request request = new Request.Builder()
            .url(apiUrl)
            .addHeader("Authorization", "Bearer " + authToken)
            .addHeader("Content-Type", "application/json")
            .post(body)
            .build();
        
        httpClient.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                Log.e(TAG, "Failed to send location to backend", e);
            }
            
            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) throws IOException {
                if (response.isSuccessful()) {
                    Log.d(TAG, "Location sent to backend successfully");
                    consecutive401Count = 0;
                } else if (response.code() == 401) {
                    consecutive401Count++;
                    Log.w(TAG, "Backend returned 401 Unauthorized (" + consecutive401Count + "/" + MAX_401_BEFORE_STOP + ")");
                    if (consecutive401Count >= MAX_401_BEFORE_STOP) {
                        Log.w(TAG, "Too many 401 responses - session expired. Stopping tracking service.");
                        handler.post(() -> {
                            stopLocationUpdates();
                            isServiceRunning = false;
                            BootReceiver.clearTrackingState(BackgroundLocationService.this);
                            broadcastServiceStatus(false, "session_expired");
                            stopForeground(true);
                            stopSelf();
                        });
                    }
                } else {
                    Log.w(TAG, "Backend returned error: " + response.code());
                }
                response.close();
            }
        });
    }
    
    private void broadcastServiceStatus(boolean isRunning, String reason) {
        Intent statusIntent = new Intent(BackgroundLocationPlugin.ACTION_SERVICE_STATUS);
        statusIntent.putExtra("isRunning", isRunning);
        statusIntent.putExtra("reason", reason);
        sendBroadcast(statusIntent);
    }
    
    private void reportOfflinePeriod(String reason, String description) {
        if (apiUrl == null || apiUrl.isEmpty() || authToken == null || authToken.isEmpty()) {
            Log.w(TAG, "Cannot report offline period - missing credentials");
            return;
        }
        
        String gapUrl = apiUrl.replace("/location/update", "/tracking-gap");
        
        String json = String.format(
            "{\"reason\": \"%s\", \"description\": \"%s\", \"timestamp\": %d, \"source\": \"native_android\"}",
            reason, description, System.currentTimeMillis()
        );
        
        RequestBody body = RequestBody.create(json, MediaType.parse("application/json"));
        
        Request request = new Request.Builder()
            .url(gapUrl)
            .addHeader("Authorization", "Bearer " + authToken)
            .addHeader("Content-Type", "application/json")
            .post(body)
            .build();
        
        httpClient.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                Log.e(TAG, "Failed to report offline period", e);
            }
            
            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) throws IOException {
                if (response.isSuccessful()) {
                    Log.d(TAG, "Offline period reported: " + reason);
                } else {
                    Log.w(TAG, "Failed to report offline period: " + response.code());
                }
                response.close();
            }
        });
    }
    
    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
    
    @Override
    public void onDestroy() {
        Log.d(TAG, "Service onDestroy");
        stopLocationUpdates();
        releaseWakeLock();
        isServiceRunning = false;
        broadcastServiceStatus(false, "destroyed");
        super.onDestroy();
    }
    
    @Override
    public void onTaskRemoved(Intent rootIntent) {
        Log.d(TAG, "Task removed - service continuing in background");
        super.onTaskRemoved(rootIntent);
    }
}
