package com.myntos.mobile;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;
import com.myntos.mobile.plugins.BackgroundLocationPlugin;
import com.myntos.mobile.plugins.ContactsPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(BackgroundLocationPlugin.class);
        registerPlugin(ContactsPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
