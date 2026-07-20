package com.myntreal.mnr.plugins;

import android.database.Cursor;
import android.net.Uri;
import android.provider.ContactsContract;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;

@CapacitorPlugin(
    name = "MyntContacts",
    permissions = {
        @Permission(strings = {"android.permission.READ_CONTACTS"}, alias = "contacts")
    }
)
public class ContactsPlugin extends Plugin {

    @PluginMethod()
    public void getContactName(PluginCall call) {
        String phoneNumber = call.getString("phoneNumber");
        if (phoneNumber == null || phoneNumber.isEmpty()) {
            call.resolve(new JSObject().put("name", JSObject.NULL));
            return;
        }

        try {
            Uri lookupUri = Uri.withAppendedPath(
                ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                Uri.encode(phoneNumber)
            );

            Cursor cursor = getContext().getContentResolver().query(
                lookupUri,
                new String[] { ContactsContract.PhoneLookup.DISPLAY_NAME },
                null, null, null
            );

            String name = null;
            if (cursor != null) {
                if (cursor.moveToFirst()) {
                    name = cursor.getString(0);
                }
                cursor.close();
            }

            JSObject result = new JSObject();
            result.put("name", name != null ? name : JSObject.NULL);
            call.resolve(result);
        } catch (Exception e) {
            JSObject result = new JSObject();
            result.put("name", JSObject.NULL);
            result.put("error", e.getMessage());
            call.resolve(result);
        }
    }

    @PluginMethod()
    public void getContactNames(PluginCall call) {
        JSArray phoneNumbers = call.getArray("phoneNumbers");
        if (phoneNumbers == null) {
            call.resolve(new JSObject().put("contacts", new JSObject()));
            return;
        }

        JSObject contacts = new JSObject();

        try {
            for (int i = 0; i < phoneNumbers.length(); i++) {
                String phone = phoneNumbers.getString(i);
                if (phone == null || phone.isEmpty()) continue;

                Uri lookupUri = Uri.withAppendedPath(
                    ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
                    Uri.encode(phone)
                );

                Cursor cursor = getContext().getContentResolver().query(
                    lookupUri,
                    new String[] { ContactsContract.PhoneLookup.DISPLAY_NAME },
                    null, null, null
                );

                if (cursor != null) {
                    if (cursor.moveToFirst()) {
                        contacts.put(phone, cursor.getString(0));
                    }
                    cursor.close();
                }
            }
        } catch (Exception e) {
            contacts.put("_error", e.getMessage());
        }

        JSObject result = new JSObject();
        result.put("contacts", contacts);
        call.resolve(result);
    }

    @PluginMethod()
    public void checkPermissions(PluginCall call) {
        super.checkPermissions(call);
    }

    @PluginMethod()
    public void requestPermissions(PluginCall call) {
        super.requestPermissions(call);
    }
}
