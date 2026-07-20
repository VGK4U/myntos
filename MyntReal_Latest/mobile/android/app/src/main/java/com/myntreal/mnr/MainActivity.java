package com.myntreal.mnr;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;
import com.myntreal.mnr.plugins.BackgroundLocationPlugin;
import com.myntreal.mnr.plugins.ContactsPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(BackgroundLocationPlugin.class);
        registerPlugin(ContactsPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
