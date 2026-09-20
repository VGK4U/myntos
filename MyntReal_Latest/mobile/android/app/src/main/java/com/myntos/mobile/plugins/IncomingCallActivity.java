package com.myntos.mobile.plugins;

import android.app.KeyguardManager;
import android.app.NotificationManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.media.AudioAttributes;
import android.media.Ringtone;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.util.Log;
import android.view.WindowManager;
import android.widget.ImageButton;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.myntos.mobile.MainActivity;
import com.myntos.mobile.R;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * Native Full-Screen Incoming Call Activity for MyntOS Telephony.
 * Displays over Android Lock Screen with screen turned on when screen is off / locked.
 * Complies with Android 10-16 fullScreenIntent & keyguard dismiss security contracts.
 */
public class IncomingCallActivity extends AppCompatActivity {
    private static final String TAG = "IncomingCallActivity";
    public static final String ACTION_CALL_CANCELLED = "com.myntos.mobile.CALL_CANCELLED";

    private String callSessionId = "";
    private String callerPhone = "";
    private String callerName = "";
    private String providerCallId = "";
    private String category = "";
    private String leadType = "";
    private String city = "";
    private String leadStatus = "";
    private String dealValue = "";
    private String leadId = "";

    private Ringtone ringtone;
    private Vibrator vibrator;
    private boolean isReceiverRegistered = false;

    private final Handler timeoutHandler = new Handler(Looper.getMainLooper());
    private final Runnable timeoutRunnable = () -> {
        Log.d(TAG, "Incoming call timed out without user answer (45s safety limit)");
        stopRingtoneAndVibration();
        dismissNotification();
        finish();
    };

    private final BroadcastReceiver callCancelledReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (intent != null && ACTION_CALL_CANCELLED.equals(intent.getAction())) {
                String cancelledSessionId = intent.getStringExtra("call_session_id");
                Log.d(TAG, "Received call cancelled broadcast for session: " + cancelledSessionId);
                if (callSessionId == null || callSessionId.isEmpty() ||
                    cancelledSessionId == null || cancelledSessionId.isEmpty() ||
                    callSessionId.equals(cancelledSessionId)) {
                    stopRingtoneAndVibration();
                    dismissNotification();
                    finish();
                }
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.d(TAG, "IncomingCallActivity onCreate");

        configureWindowForLockScreen();
        setContentView(R.layout.activity_incoming_call);

        parseIntentExtras(getIntent());
        bindViews();
        startRingtoneAndVibration();
        registerCallCancelledReceiver();

        // 45-second fallback dismiss if caller leaves or agent does not answer
        timeoutHandler.postDelayed(timeoutRunnable, 45000L);
    }

    private void configureWindowForLockScreen() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
            KeyguardManager km = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
            if (km != null) {
                km.requestDismissKeyguard(this, null);
            }
        } else {
            getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
                WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD |
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON |
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            );
        }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    private void parseIntentExtras(Intent intent) {
        if (intent != null) {
            callSessionId = intent.getStringExtra("call_session_id");
            callerPhone = intent.getStringExtra("caller_phone");
            callerName = intent.getStringExtra("caller_name");
            category = intent.getStringExtra("category");
            leadType = intent.getStringExtra("lead_type");
            city = intent.getStringExtra("city");
            leadStatus = intent.getStringExtra("status");
            dealValue = intent.getStringExtra("deal_value");
            leadId = intent.getStringExtra("lead_id");
            providerCallId = intent.getStringExtra("provider_call_id");
        }
        if (callerName == null || callerName.trim().isEmpty()) {
            if (category != null && !category.trim().isEmpty()) {
                callerName = "[" + category.trim() + "] " + (callerPhone != null ? callerPhone : "Lead");
            } else {
                callerName = "Incoming Lead Inquiry";
            }
        }
        if (callerPhone == null || callerPhone.trim().isEmpty()) {
            callerPhone = "+91 ••••••••••";
        }
    }

    private void bindViews() {
        TextView tvLeadCategory = findViewById(R.id.tv_lead_category);
        TextView tvCallerName = findViewById(R.id.tv_caller_name);
        TextView tvCallerPhone = findViewById(R.id.tv_caller_phone);
        TextView tvLeadMeta = findViewById(R.id.tv_lead_meta);
        TextView tvCallStatus = findViewById(R.id.tv_call_status);
        ImageButton btnDecline = findViewById(R.id.btn_decline);
        ImageButton btnAccept = findViewById(R.id.btn_accept);

        if (tvLeadCategory != null) {
            if (category != null && !category.trim().isEmpty()) {
                tvLeadCategory.setText(category.toUpperCase() + " LEAD");
                tvLeadCategory.setVisibility(android.view.View.VISIBLE);
            } else {
                tvLeadCategory.setVisibility(android.view.View.GONE);
            }
        }

        if (tvCallerName != null) {
            tvCallerName.setText(callerName);
        }
        if (tvCallerPhone != null) {
            tvCallerPhone.setText(callerPhone);
        }

        if (tvLeadMeta != null) {
            StringBuilder metaBuilder = new StringBuilder();
            if (leadType != null && !leadType.trim().isEmpty()) {
                metaBuilder.append(leadType.trim());
            }
            if (city != null && !city.trim().isEmpty()) {
                if (metaBuilder.length() > 0) metaBuilder.append(" • ");
                metaBuilder.append(city.trim());
            }
            if (dealValue != null && !dealValue.trim().isEmpty()) {
                if (metaBuilder.length() > 0) metaBuilder.append(" • ");
                metaBuilder.append(dealValue.trim());
            }
            if (metaBuilder.length() > 0) {
                tvLeadMeta.setText(metaBuilder.toString());
                tvLeadMeta.setVisibility(android.view.View.VISIBLE);
            } else {
                tvLeadMeta.setVisibility(android.view.View.GONE);
            }
        }

        if (tvCallStatus != null && leadStatus != null && !leadStatus.trim().isEmpty()) {
            tvCallStatus.setText("Ringing... (" + leadStatus + ")");
        }

        if (btnAccept != null) {
            btnAccept.setOnClickListener(v -> onAcceptClicked());
        }

        if (btnDecline != null) {
            btnDecline.setOnClickListener(v -> onDeclineClicked());
        }
    }

    private void onAcceptClicked() {
        Log.d(TAG, "User accepted incoming call: session=" + callSessionId);
        timeoutHandler.removeCallbacks(timeoutRunnable);
        stopRingtoneAndVibration();
        dismissNotification();

        // 1. Store pending accepted call for bridge
        IncomingCallPlugin.setPendingCall(
            callSessionId, callerPhone, callerName, providerCallId,
            category, leadType, city, leadStatus, dealValue, leadId
        );

        // 2. Launch MainActivity to foreground and bridge to WebRTC
        Intent mainIntent = new Intent(this, MainActivity.class);
        mainIntent.setAction("com.myntos.mobile.ANSWER_CALL");
        mainIntent.putExtra("call_session_id", callSessionId);
        mainIntent.putExtra("caller_phone", callerPhone);
        mainIntent.putExtra("caller_name", callerName);
        mainIntent.putExtra("category", category);
        mainIntent.putExtra("lead_type", leadType);
        mainIntent.putExtra("city", city);
        mainIntent.putExtra("status", leadStatus);
        mainIntent.putExtra("deal_value", dealValue);
        mainIntent.putExtra("lead_id", leadId);
        mainIntent.putExtra("provider_call_id", providerCallId);
        mainIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        startActivity(mainIntent);

        finish();
    }

    private void onDeclineClicked() {
        Log.d(TAG, "User declined incoming call: session=" + callSessionId);
        timeoutHandler.removeCallbacks(timeoutRunnable);
        stopRingtoneAndVibration();
        dismissNotification();

        // Send async rejection to backend
        sendCallRejectAsync(callSessionId, providerCallId);

        finish();
    }

    private void sendCallRejectAsync(String sessionId, String callUuid) {
        if (sessionId == null || sessionId.isEmpty()) return;

        new Thread(() -> {
            try {
                SharedPreferences prefs = getSharedPreferences("myntos_push_prefs", Context.MODE_PRIVATE);
                String baseUrl = prefs.getString("server_base_url", "https://www.myntreal.com");
                String token = prefs.getString("auth_token", "");

                OkHttpClient client = new OkHttpClient.Builder()
                    .connectTimeout(10, TimeUnit.SECONDS)
                    .readTimeout(10, TimeUnit.SECONDS)
                    .build();

                String json = String.format(
                    "{\"call_session_id\":\"%s\",\"provider_call_id\":\"%s\",\"reason\":\"user_declined\"}",
                    sessionId != null ? sessionId : "",
                    callUuid != null ? callUuid : ""
                );

                RequestBody body = RequestBody.create(json, MediaType.parse("application/json"));
                Request.Builder reqBuilder = new Request.Builder()
                    .url(baseUrl.replaceAll("/+$", "") + "/api/v1/telephony/mobile/call/reject")
                    .post(body);

                if (token != null && !token.isEmpty()) {
                    reqBuilder.addHeader("Authorization", "Bearer " + token);
                }

                client.newCall(reqBuilder.build()).enqueue(new Callback() {
                    @Override
                    public void onFailure(@NonNull Call call, @NonNull IOException e) {
                        Log.w(TAG, "Call reject HTTP failed: " + e.getMessage());
                    }

                    @Override
                    public void onResponse(@NonNull Call call, @NonNull Response response) {
                        Log.d(TAG, "Call reject response code: " + response.code());
                        response.close();
                    }
                });
            } catch (Exception e) {
                Log.w(TAG, "Notice sending call reject: " + e.getMessage());
            }
        }).start();
    }

    private void startRingtoneAndVibration() {
        try {
            Uri ringtoneUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
            if (ringtoneUri == null) {
                ringtoneUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
            }
            ringtone = RingtoneManager.getRingtone(getApplicationContext(), ringtoneUri);
            if (ringtone != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    ringtone.setLooping(true);
                }
                ringtone.play();
                Log.d(TAG, "Incoming call ringtone started playing");
            }
        } catch (Exception e) {
            Log.w(TAG, "Notice starting ringtone: " + e.getMessage());
        }

        try {
            vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (vibrator != null && vibrator.hasVibrator()) {
                long[] pattern = {0, 1000, 1000};
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createWaveform(pattern, 0));
                } else {
                    vibrator.vibrate(pattern, 0);
                }
                Log.d(TAG, "Incoming call vibration pattern started");
            }
        } catch (Exception e) {
            Log.w(TAG, "Notice starting vibrator: " + e.getMessage());
        }
    }

    private void stopRingtoneAndVibration() {
        if (ringtone != null) {
            try {
                if (ringtone.isPlaying()) {
                    ringtone.stop();
                }
            } catch (Exception e) {
                Log.w(TAG, "Notice stopping ringtone: " + e.getMessage());
            }
            ringtone = null;
        }
        if (vibrator != null) {
            try {
                vibrator.cancel();
            } catch (Exception e) {
                Log.w(TAG, "Notice canceling vibrator: " + e.getMessage());
            }
            vibrator = null;
        }
    }

    private void dismissNotification() {
        try {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) {
                nm.cancel(MyntosFirebaseMessagingService.NOTIFICATION_ID);
            }
        } catch (Exception e) {
            Log.w(TAG, "Notice dismissing notification: " + e.getMessage());
        }
    }

    private void registerCallCancelledReceiver() {
        try {
            IntentFilter filter = new IntentFilter(ACTION_CALL_CANCELLED);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                registerReceiver(callCancelledReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
            } else {
                registerReceiver(callCancelledReceiver, filter);
            }
            isReceiverRegistered = true;
            Log.d(TAG, "Call cancelled broadcast receiver registered");
        } catch (Exception e) {
            Log.w(TAG, "Notice registering call cancelled receiver: " + e.getMessage());
        }
    }

    private void unregisterCallCancelledReceiver() {
        if (isReceiverRegistered) {
            try {
                unregisterReceiver(callCancelledReceiver);
            } catch (Exception e) {
                Log.w(TAG, "Notice unregistering call cancelled receiver: " + e.getMessage());
            }
            isReceiverRegistered = false;
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        parseIntentExtras(intent);
        bindViews();
    }

    @Override
    protected void onDestroy() {
        timeoutHandler.removeCallbacks(timeoutRunnable);
        stopRingtoneAndVibration();
        unregisterCallCancelledReceiver();
        super.onDestroy();
        Log.d(TAG, "IncomingCallActivity onDestroy complete");
    }
}
