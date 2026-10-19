package com.myntos.mobile;

import android.content.Intent;
import android.os.Bundle;

import com.getcapacitor.BridgeActivity;
import com.myntos.mobile.plugins.AudioRoutingPlugin;
import com.myntos.mobile.plugins.BackgroundLocationPlugin;
import com.myntos.mobile.plugins.ContactsPlugin;
import com.myntos.mobile.plugins.IncomingCallPlugin;
import com.myntos.mobile.plugins.SecureStoragePlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(AudioRoutingPlugin.class);
        registerPlugin(BackgroundLocationPlugin.class);
        registerPlugin(ContactsPlugin.class);
        registerPlugin(IncomingCallPlugin.class);
        registerPlugin(SecureStoragePlugin.class);
        super.onCreate(savedInstanceState);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
    }

    @Override
    public void onPause() {
        super.onPause();
        // Keep Chromium WebView timers and Plivo WebRTC SIP WebSocket active when screen turns off
        try {
            if (getBridge() != null && getBridge().getWebView() != null) {
                getBridge().getWebView().onResume();
                getBridge().getWebView().resumeTimers();
            }
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onStop() {
        super.onStop();
        try {
            if (getBridge() != null && getBridge().getWebView() != null) {
                getBridge().getWebView().onResume();
                getBridge().getWebView().resumeTimers();
            }
        } catch (Exception ignored) {
        }
    }
}

