package com.myntos.mobile.plugins;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.core.app.NotificationCompat;

import com.capacitorjs.plugins.pushnotifications.MessagingService;
import com.google.firebase.messaging.RemoteMessage;
import com.myntos.mobile.R;

import java.util.Map;

/**
 * Firebase Cloud Messaging Service for MyntOS Mobile Telephony.
 * Intercepts high-priority incoming call data pushes to wake device and present
 * full-screen incoming call UI even when device screen is locked or app is terminated.
 * Extends Capacitor MessagingService to preserve full compatibility with regular push notifications.
 */
public class MyntosFirebaseMessagingService extends MessagingService {
    private static final String TAG = "MyntosFCMService";
    public static final String CHANNEL_ID = "myntos_incoming_calls";
    public static final int NOTIFICATION_ID = 2026;

    @Override
    public void onMessageReceived(@NonNull RemoteMessage remoteMessage) {
        Map<String, String> data = remoteMessage.getData();
        Log.d(TAG, "FCM onMessageReceived with data: " + data);

        if (data != null && data.containsKey("type")) {
            String type = data.get("type");
            if ("incoming_call".equalsIgnoreCase(type)) {
                handleIncomingCall(data);
                return;
            } else if ("call_cancelled".equalsIgnoreCase(type)) {
                handleCallCancelled(data);
                return;
            }
        }

        // Delegate standard push notifications to Capacitor's default handler
        super.onMessageReceived(remoteMessage);
    }

    private void handleIncomingCall(Map<String, String> data) {
        String callSessionId = data.get("call_session_id");
        String callerPhone = data.get("caller_phone");
        if (callerPhone == null || callerPhone.trim().isEmpty()) {
            callerPhone = data.get("raw_caller_phone");
        }
        if (callerPhone == null || callerPhone.trim().isEmpty()) {
            callerPhone = data.get("caller_number");
        }
        String callerName = data.get("caller_name");
        if (callerName == null || callerName.trim().isEmpty()) {
            callerName = data.get("lead_name");
        }

        String category = data.get("category");
        String leadType = data.get("lead_type");
        String city = data.get("city");
        String status = data.get("status");
        String dealValue = data.get("deal_value");
        String leadId = data.get("lead_id");
        String subtitleDisplay = data.get("subtitle_display");

        if (callerName == null || callerName.trim().isEmpty()) {
            if (category != null && !category.trim().isEmpty()) {
                callerName = "[" + category.trim() + "] " + callerPhone;
            } else {
                callerName = "Incoming Lead Inquiry";
            }
        }
        if (callerPhone == null || callerPhone.trim().isEmpty()) {
            callerPhone = "+91 ••••••••••";
        }

        Log.d(TAG, "Dispatching native incoming call UI for session: " + callSessionId + " (" + callerName + ")");

        // 1. Acquire temporary partial wake lock (20s bound) to guarantee CPU stays active
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        PowerManager.WakeLock wakeLock = null;
        if (pm != null) {
            wakeLock = pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "MyntOS::IncomingCallWakeLock"
            );
            wakeLock.acquire(20000L);
        }

        // 2. Ensure high-importance notification channel is registered
        createNotificationChannel();

        // 3. Construct Full-Screen Intent targeting IncomingCallActivity
        Intent fullScreenIntent = new Intent(this, IncomingCallActivity.class);
        fullScreenIntent.putExtra("call_session_id", callSessionId);
        fullScreenIntent.putExtra("caller_phone", callerPhone);
        fullScreenIntent.putExtra("caller_name", callerName);
        fullScreenIntent.putExtra("category", category);
        fullScreenIntent.putExtra("lead_type", leadType);
        fullScreenIntent.putExtra("city", city);
        fullScreenIntent.putExtra("status", status);
        fullScreenIntent.putExtra("deal_value", dealValue);
        fullScreenIntent.putExtra("lead_id", leadId);
        fullScreenIntent.putExtra("provider_call_id", providerCallId);
        fullScreenIntent.addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK |
            Intent.FLAG_ACTIVITY_CLEAR_TOP |
            Intent.FLAG_ACTIVITY_SINGLE_TOP
        );

        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        }

        PendingIntent fullScreenPendingIntent = PendingIntent.getActivity(
            this,
            (callSessionId != null ? callSessionId.hashCode() : 100),
            fullScreenIntent,
            pendingFlags
        );

        String notifContent = (subtitleDisplay != null && !subtitleDisplay.isEmpty()) ? subtitleDisplay : callerPhone;

        // 4. Build high-priority call notification
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("Incoming Call: " + callerName)
            .setContentText(notifContent)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOngoing(true)
            .setAutoCancel(true)
            .setFullScreenIntent(fullScreenPendingIntent, true);

        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.notify(NOTIFICATION_ID, builder.build());
        }

        // 5. Start activity directly as well
        try {
            startActivity(fullScreenIntent);
        } catch (Exception e) {
            Log.w(TAG, "Notice starting IncomingCallActivity: " + e.getMessage());
        }
    }

    private void handleCallCancelled(Map<String, String> data) {
        String callSessionId = data.get("call_session_id");
        Log.d(TAG, "Call cancelled notification received: " + callSessionId);

        // 1. Dismiss native notification
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) {
            nm.cancel(NOTIFICATION_ID);
        }

        // 2. Broadcast cancellation to dismiss IncomingCallActivity if open
        Intent cancelIntent = new Intent(IncomingCallActivity.ACTION_CALL_CANCELLED);
        cancelIntent.putExtra("call_session_id", callSessionId);
        sendBroadcast(cancelIntent);
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Incoming Phone Calls",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Incoming VoIP telephony calls from Plivo");
            channel.enableVibration(true);
            channel.setVibrationPattern(new long[]{0, 1000, 1000});
            channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);

            Uri ringtoneUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
            if (ringtoneUri != null) {
                AudioAttributes audioAttributes = new AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                    .build();
                channel.setSound(ringtoneUri, audioAttributes);
            }

            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) {
                nm.createNotificationChannel(channel);
            }
        }
    }

    @Override
    public void onNewToken(@NonNull String token) {
        Log.d(TAG, "New FCM Token received: " + token);
        super.onNewToken(token);
        IncomingCallPlugin.saveFcmToken(this, token);
    }
}
