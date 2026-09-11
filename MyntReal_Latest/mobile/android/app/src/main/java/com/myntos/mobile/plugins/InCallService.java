package com.myntos.mobile.plugins;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import com.myntos.mobile.MainActivity;
import com.myntos.mobile.R;

/**
 * Dedicated In-Call Foreground Service for MyntOS Mobile Telephony.
 * Maintains microphone access and WebRTC socket connectivity when the device screen locks.
 * Complies with Android 14+ (API 34/35/36) FOREGROUND_SERVICE_MICROPHONE security requirements.
 */
public class InCallService extends Service {
    private static final String TAG = "InCallService";
    private static final String CHANNEL_ID = "myntos_incall_channel";
    private static final int NOTIFICATION_ID = 2002;

    public static final String ACTION_START = "com.myntos.mobile.START_IN_CALL";
    public static final String ACTION_STOP = "com.myntos.mobile.STOP_IN_CALL";

    private static volatile boolean isServiceRunning = false;
    private PowerManager.WakeLock wakeLock;

    public static boolean isRunning() {
        return isServiceRunning;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "InCallService onCreate");
        createNotificationChannel();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "MyntOS In-Call Service",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Maintains microphone audio and WebRTC call stability during active calls");
            channel.setShowBadge(false);
            channel.enableLights(false);
            channel.enableVibration(false);
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    private Notification createNotification(String title, String text) {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        notificationIntent.setAction(Intent.ACTION_MAIN);
        notificationIntent.addCategory(Intent.CATEGORY_LAUNCHER);
        notificationIntent.setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);

        int pendingIntentFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            pendingIntentFlags |= PendingIntent.FLAG_IMMUTABLE;
        }

        PendingIntent pendingIntent = PendingIntent.getActivity(
            this,
            0,
            notificationIntent,
            pendingIntentFlags
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(title != null && !title.trim().isEmpty() ? title : "Active Softphone Call")
            .setContentText(text != null && !text.trim().isEmpty() ? text : "Call in progress")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .build();
    }

    private void acquireWakeLock() {
        if (wakeLock == null) {
            PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (powerManager != null) {
                wakeLock = powerManager.newWakeLock(
                    PowerManager.PARTIAL_WAKE_LOCK,
                    "MyntOS::InCallWakeLock"
                );
                wakeLock.setReferenceCounted(false);
                // Safety bound of 2 hours max per call to prevent battery drain if unreleased
                wakeLock.acquire(2 * 60 * 60 * 1000L);
                Log.d(TAG, "In-call WakeLock acquired");
            }
        }
    }

    private void releaseWakeLock() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception e) {
                Log.w(TAG, "Notice releasing wakeLock: " + e.getMessage());
            }
            wakeLock = null;
            Log.d(TAG, "In-call WakeLock released");
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null) {
            return START_NOT_STICKY;
        }

        String action = intent.getAction();
        Log.d(TAG, "onStartCommand action: " + action);

        if (ACTION_STOP.equals(action)) {
            stopServiceGracefully();
            return START_NOT_STICKY;
        }

        if (ACTION_START.equals(action)) {
            String title = intent.getStringExtra("title");
            String text = intent.getStringExtra("text");

            Notification notification = createNotification(title, text);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
            acquireWakeLock();
            isServiceRunning = true;
            Log.d(TAG, "InCallService running in foreground (type: microphone)");
        }

        return START_NOT_STICKY;
    }

    private void stopServiceGracefully() {
        releaseWakeLock();
        isServiceRunning = false;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } else {
            stopForeground(true);
        }
        stopSelf();
        Log.d(TAG, "InCallService gracefully stopped");
    }

    @Override
    public void onDestroy() {
        stopServiceGracefully();
        super.onDestroy();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
