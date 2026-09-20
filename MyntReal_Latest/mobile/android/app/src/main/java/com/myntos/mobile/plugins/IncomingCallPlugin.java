package com.myntos.mobile.plugins;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.core.app.NotificationCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.firebase.messaging.FirebaseMessaging;
import com.myntos.mobile.R;

/**
 * Canonical Capacitor Bridge Plugin for Incoming Calls & VoIP Push.
 * Coordinates native lock-screen call events with the WebRTC softphone engine.
 */
@CapacitorPlugin(name = "IncomingCall")
public class IncomingCallPlugin extends Plugin {
    private static final String TAG = "IncomingCallPlugin";
    private static final String PREF_NAME = "myntos_push_prefs";
    private static final String KEY_FCM_TOKEN = "fcm_token";
    private static final String KEY_SERVER_URL = "server_base_url";
    private static final String KEY_AUTH_TOKEN = "auth_token";

    private static volatile String pendingSessionId = null;
    private static volatile String pendingCallerPhone = null;
    private static volatile String pendingCallerName = null;
    private static volatile String pendingProviderCallId = null;
    private static volatile String pendingCategory = null;
    private static volatile String pendingLeadType = null;
    private static volatile String pendingCity = null;
    private static volatile String pendingStatus = null;
    private static volatile String pendingDealValue = null;
    private static volatile String pendingLeadId = null;

    private static IncomingCallPlugin instance = null;

    @Override
    public void load() {
        super.load();
        instance = this;
        Log.d(TAG, "IncomingCallPlugin loaded into Capacitor bridge");
    }

    public static synchronized void setPendingCall(String sessionId, String phone, String name, String providerCallId) {
        setPendingCall(sessionId, phone, name, providerCallId, null, null, null, null, null, null);
    }

    public static synchronized void setPendingCall(String sessionId, String phone, String name, String providerCallId,
                                                   String category, String leadType, String city,
                                                   String status, String dealValue, String leadId) {
        pendingSessionId = sessionId;
        pendingCallerPhone = phone;
        pendingCallerName = name;
        pendingProviderCallId = providerCallId;
        pendingCategory = category;
        pendingLeadType = leadType;
        pendingCity = city;
        pendingStatus = status;
        pendingDealValue = dealValue;
        pendingLeadId = leadId;
        Log.d(TAG, "Stored pending accepted call: " + sessionId + " category=" + category);

        if (instance != null) {
            instance.emitCallAnswered(sessionId, phone, name, providerCallId, category, leadType, city, status, dealValue, leadId);
        }
    }

    public static void saveFcmToken(Context context, String token) {
        if (context == null || token == null || token.isEmpty()) return;
        try {
            SharedPreferences prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
            prefs.edit().putString(KEY_FCM_TOKEN, token).apply();
            Log.d(TAG, "Saved FCM token to SharedPreferences");

            if (instance != null) {
                JSObject ret = new JSObject();
                ret.put("token", token);
                instance.notifyListeners("tokenReceived", ret, true);
            }
        } catch (Exception e) {
            Log.w(TAG, "Error saving FCM token: " + e.getMessage());
        }
    }

    public static String getSavedFcmToken(Context context) {
        if (context == null) return null;
        try {
            SharedPreferences prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
            return prefs.getString(KEY_FCM_TOKEN, null);
        } catch (Exception e) {
            return null;
        }
    }

    @PluginMethod
    public void getPushToken(PluginCall call) {
        Context context = getContext();
        String savedToken = getSavedFcmToken(context);

        if (savedToken != null && !savedToken.isEmpty()) {
            JSObject res = new JSObject();
            res.put("pushToken", savedToken);
            res.put("platform", "android");
            res.put("tokenType", "fcm_data");
            call.resolve(res);
            return;
        }

        try {
            FirebaseMessaging.getInstance().getToken()
                .addOnCompleteListener(new OnCompleteListener<String>() {
                    @Override
                    public void onComplete(@NonNull Task<String> task) {
                        if (!task.isSuccessful() || task.getResult() == null) {
                            Log.w(TAG, "Fetching FCM registration token failed", task.getException());
                            JSObject res = new JSObject();
                            res.put("pushToken", null);
                            res.put("platform", "android");
                            res.put("tokenType", "fcm_data");
                            res.put("error", task.getException() != null ? task.getException().getMessage() : "Unknown error");
                            call.resolve(res);
                            return;
                        }

                        String token = task.getResult();
                        saveFcmToken(context, token);

                        JSObject res = new JSObject();
                        res.put("pushToken", token);
                        res.put("platform", "android");
                        res.put("tokenType", "fcm_data");
                        call.resolve(res);
                    }
                });
        } catch (Exception e) {
            Log.w(TAG, "FirebaseMessaging not initialized or missing config: " + e.getMessage());
            JSObject res = new JSObject();
            res.put("pushToken", null);
            res.put("platform", "android");
            res.put("tokenType", "fcm_data");
            res.put("error", e.getMessage());
            call.resolve(res);
        }
    }

    @PluginMethod
    public void getPendingCall(PluginCall call) {
        JSObject res = new JSObject();
        if (pendingSessionId != null) {
            res.put("hasPendingCall", true);
            res.put("sessionId", pendingSessionId);
            res.put("callerPhone", pendingCallerPhone);
            res.put("callerName", pendingCallerName);
            res.put("providerCallId", pendingProviderCallId);
            res.put("category", pendingCategory);
            res.put("leadType", pendingLeadType);
            res.put("city", pendingCity);
            res.put("status", pendingStatus);
            res.put("dealValue", pendingDealValue);
            res.put("leadId", pendingLeadId);

            // Clear after consumption
            pendingSessionId = null;
            pendingCallerPhone = null;
            pendingCallerName = null;
            pendingProviderCallId = null;
            pendingCategory = null;
            pendingLeadType = null;
            pendingCity = null;
            pendingStatus = null;
            pendingDealValue = null;
            pendingLeadId = null;
        } else {
            res.put("hasPendingCall", false);
        }
        call.resolve(res);
    }

    @PluginMethod
    public void clearPendingCall(PluginCall call) {
        pendingSessionId = null;
        pendingCallerPhone = null;
        pendingCallerName = null;
        pendingProviderCallId = null;
        pendingCategory = null;
        pendingLeadType = null;
        pendingCity = null;
        pendingStatus = null;
        pendingDealValue = null;
        pendingLeadId = null;
        call.resolve(new JSObject().put("success", true));
    }

    @PluginMethod
    public void dismissCallNotification(PluginCall call) {
        try {
            Context context = getContext();
            if (context != null) {
                NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
                if (nm != null) {
                    nm.cancel(MyntosFirebaseMessagingService.NOTIFICATION_ID);
                }
            }
            call.resolve(new JSObject().put("success", true));
        } catch (Exception e) {
            call.reject("Failed to dismiss notification: " + e.getMessage());
        }
    }

    @PluginMethod
    public void saveServerConfig(PluginCall call) {
        String baseUrl = call.getString("baseUrl");
        String authToken = call.getString("authToken");

        Context context = getContext();
        if (context != null) {
            SharedPreferences prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
            SharedPreferences.Editor editor = prefs.edit();
            if (baseUrl != null) editor.putString(KEY_SERVER_URL, baseUrl);
            if (authToken != null) editor.putString(KEY_AUTH_TOKEN, authToken);
            editor.apply();
        }
        call.resolve(new JSObject().put("success", true));
    }

    @PluginMethod
    public void triggerTestIncomingCall(PluginCall call) {
        String phone = call.getString("callerPhone", "+919876543210");
        String name = call.getString("callerName", "Rajesh Sharma");
        String category = call.getString("category", "Solar");
        String leadType = call.getString("leadType", "5kW Residential Rooftop");
        String city = call.getString("city", "Hyderabad");
        String status = call.getString("status", "Interested");
        String dealValue = call.getString("dealValue", "₹3,50,000");
        String leadId = call.getString("leadId", "test_lead_001");
        Double delay = call.getDouble("delaySeconds", 0.0);
        long delayMs = (long) ((delay != null ? delay : 0.0) * 1000);

        Context context = getContext();
        if (context == null) {
            call.reject("Context is null");
            return;
        }

        Runnable triggerRunnable = () -> {
            try {
                // 1. Ensure notification channel
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    NotificationChannel channel = new NotificationChannel(
                        MyntosFirebaseMessagingService.CHANNEL_ID,
                        "Incoming Phone Calls",
                        NotificationManager.IMPORTANCE_HIGH
                    );
                    channel.setDescription("Incoming VoIP telephony calls from Plivo");
                    channel.enableVibration(true);
                    channel.setVibrationPattern(new long[]{0, 1000, 1000});
                    channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
                    NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
                    if (nm != null) {
                        nm.createNotificationChannel(channel);
                    }
                }

                String sessionId = "test_" + System.currentTimeMillis();
                String providerCallId = "test_provider_" + sessionId;

                Intent fullScreenIntent = new Intent(context, IncomingCallActivity.class);
                fullScreenIntent.putExtra("call_session_id", sessionId);
                fullScreenIntent.putExtra("caller_phone", phone);
                fullScreenIntent.putExtra("caller_name", name);
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
                    context,
                    sessionId.hashCode(),
                    fullScreenIntent,
                    pendingFlags
                );

                String notifTitle = (category != null && !category.isEmpty() ? "[" + category + "] " : "") + name;
                StringBuilder notifSubtitle = new StringBuilder();
                if (leadType != null && !leadType.isEmpty()) notifSubtitle.append(leadType).append(" • ");
                if (city != null && !city.isEmpty()) notifSubtitle.append(city).append(" • ");
                notifSubtitle.append(phone);

                NotificationCompat.Builder builder = new NotificationCompat.Builder(context, MyntosFirebaseMessagingService.CHANNEL_ID)
                    .setSmallIcon(R.mipmap.ic_launcher)
                    .setContentTitle(notifTitle)
                    .setContentText(notifSubtitle.toString())
                    .setPriority(NotificationCompat.PRIORITY_MAX)
                    .setCategory(NotificationCompat.CATEGORY_CALL)
                    .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                    .setOngoing(true)
                    .setAutoCancel(true)
                    .setFullScreenIntent(fullScreenPendingIntent, true);

                NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
                if (nm != null) {
                    nm.notify(MyntosFirebaseMessagingService.NOTIFICATION_ID, builder.build());
                }

                context.startActivity(fullScreenIntent);
                Log.d(TAG, "Test incoming call UI triggered successfully on Android: " + notifTitle);
            } catch (Exception e) {
                Log.w(TAG, "Error triggering test incoming call on Android: " + e.getMessage());
            }
        };

        if (delayMs > 0) {
            new Handler(Looper.getMainLooper()).postDelayed(triggerRunnable, delayMs);
        } else {
            new Handler(Looper.getMainLooper()).post(triggerRunnable);
        }

        JSObject ret = new JSObject();
        ret.put("success", true);
        ret.put("delay", delay != null ? delay : 0.0);
        call.resolve(ret);
    }

    @Override
    protected void handleOnNewIntent(Intent intent) {
        super.handleOnNewIntent(intent);
        if (intent == null) return;

        String action = intent.getAction();
        Log.d(TAG, "handleOnNewIntent action: " + action);

        if ("com.myntos.mobile.ANSWER_CALL".equals(action)) {
            String sid = intent.getStringExtra("call_session_id");
            String phone = intent.getStringExtra("caller_phone");
            String name = intent.getStringExtra("caller_name");
            String uuid = intent.getStringExtra("provider_call_id");
            String cat = intent.getStringExtra("category");
            String ltype = intent.getStringExtra("lead_type");
            String cty = intent.getStringExtra("city");
            String st = intent.getStringExtra("status");
            String dv = intent.getStringExtra("deal_value");
            String lid = intent.getStringExtra("lead_id");

            emitCallAnswered(sid, phone, name, uuid, cat, ltype, cty, st, dv, lid);
        }
    }

    private void emitCallAnswered(String sessionId, String callerPhone, String callerName, String providerCallId) {
        emitCallAnswered(sessionId, callerPhone, callerName, providerCallId, null, null, null, null, null, null);
    }

    private void emitCallAnswered(String sessionId, String callerPhone, String callerName, String providerCallId,
                                 String category, String leadType, String city, String status, String dealValue, String leadId) {
        JSObject data = new JSObject();
        data.put("sessionId", sessionId);
        data.put("callerPhone", callerPhone);
        data.put("callerName", callerName);
        data.put("providerCallId", providerCallId);
        data.put("category", category);
        data.put("leadType", leadType);
        data.put("city", city);
        data.put("status", status);
        data.put("dealValue", dealValue);
        data.put("leadId", leadId);
        Log.d(TAG, "Emitting 'callAnswered' event to JavaScript: " + sessionId + " category=" + category);
        notifyListeners("callAnswered", data, true);
    }
}
