package com.myntos.mobile.plugins;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.UUID;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

@CapacitorPlugin(name = "SecureStorage")
public class SecureStoragePlugin extends Plugin {

    private static final String TAG = "MyntSecureStorage";
    private static final String ANDROID_KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "MyntOS_SecureKey_v1";
    private static final String PREF_NAME = "mynt_secure_vault";
    private static final String AES_MODE = "AES/GCM/NoPadding";
    private static final int GCM_TAG_LENGTH = 128;

    private SharedPreferences getPrefs() {
        return getContext().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    private synchronized SecretKey getOrCreateKey() throws Exception {
        KeyStore keyStore = KeyStore.getInstance(ANDROID_KEYSTORE);
        keyStore.load(null);

        if (!keyStore.containsAlias(KEY_ALIAS)) {
            KeyGenerator keyGenerator = KeyGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_AES,
                ANDROID_KEYSTORE
            );
            KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT
            )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)
            .build();

            keyGenerator.init(spec);
            return keyGenerator.generateKey();
        }

        KeyStore.SecretKeyEntry entry = (KeyStore.SecretKeyEntry) keyStore.getEntry(KEY_ALIAS, null);
        return entry.getSecretKey();
    }

    private String encrypt(String plainText) throws Exception {
        SecretKey secretKey = getOrCreateKey();
        Cipher cipher = Cipher.getInstance(AES_MODE);
        cipher.init(Cipher.ENCRYPT_MODE, secretKey);

        byte[] iv = cipher.getIV();
        byte[] cipherText = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));

        String encodedIv = Base64.encodeToString(iv, Base64.NO_WRAP);
        String encodedCipher = Base64.encodeToString(cipherText, Base64.NO_WRAP);
        return encodedIv + ":" + encodedCipher;
    }

    private String decrypt(String encryptedData) throws Exception {
        if (encryptedData == null || !encryptedData.contains(":")) {
            return null;
        }

        String[] parts = encryptedData.split(":", 2);
        byte[] iv = Base64.decode(parts[0], Base64.NO_WRAP);
        byte[] cipherText = Base64.decode(parts[1], Base64.NO_WRAP);

        SecretKey secretKey = getOrCreateKey();
        Cipher cipher = Cipher.getInstance(AES_MODE);
        GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.DECRYPT_MODE, secretKey, spec);

        byte[] plainTextBytes = cipher.doFinal(cipherText);
        return new String(plainTextBytes, StandardCharsets.UTF_8);
    }

    @PluginMethod
    public void setKey(PluginCall call) {
        String key = call.getString("key");
        String value = call.getString("value");

        if (key == null || key.trim().isEmpty() || value == null) {
            call.reject("key and value are required");
            return;
        }

        try {
            String encrypted = encrypt(value);
            getPrefs().edit().putString(key, encrypted).apply();
            JSObject res = new JSObject();
            res.put("success", true);
            call.resolve(res);
        } catch (Exception e) {
            Log.e(TAG, "Failed to encrypt key: " + key, e);
            call.reject("Failed to securely store key: " + e.getMessage());
        }
    }

    @PluginMethod
    public void getKey(PluginCall call) {
        String key = call.getString("key");
        if (key == null || key.trim().isEmpty()) {
            call.reject("key is required");
            return;
        }

        try {
            String encrypted = getPrefs().getString(key, null);
            JSObject res = new JSObject();
            if (encrypted == null) {
                res.put("value", JSObject.NULL);
            } else {
                String decrypted = decrypt(encrypted);
                res.put("value", decrypted != null ? decrypted : JSObject.NULL);
            }
            call.resolve(res);
        } catch (Exception e) {
            Log.e(TAG, "Failed to decrypt key: " + key, e);
            JSObject res = new JSObject();
            res.put("value", JSObject.NULL);
            res.put("error", e.getMessage());
            call.resolve(res);
        }
    }

    @PluginMethod
    public void removeKey(PluginCall call) {
        String key = call.getString("key");
        if (key == null || key.trim().isEmpty()) {
            call.reject("key is required");
            return;
        }

        getPrefs().edit().remove(key).apply();
        JSObject res = new JSObject();
        res.put("success", true);
        call.resolve(res);
    }

    @PluginMethod
    public void clear(PluginCall call) {
        getPrefs().edit().clear().apply();
        JSObject res = new JSObject();
        res.put("success", true);
        call.resolve(res);
    }

    @PluginMethod
    public void getDeviceId(PluginCall call) {
        try {
            String existingEncrypted = getPrefs().getString("device_id", null);
            if (existingEncrypted != null) {
                String existing = decrypt(existingEncrypted);
                if (existing != null && !existing.isEmpty()) {
                    JSObject res = new JSObject();
                    res.put("deviceId", existing);
                    call.resolve(res);
                    return;
                }
            }

            String newId = "android_" + UUID.randomUUID().toString();
            String encrypted = encrypt(newId);
            getPrefs().edit().putString("device_id", encrypted).apply();

            JSObject res = new JSObject();
            res.put("deviceId", newId);
            call.resolve(res);
        } catch (Exception e) {
            Log.e(TAG, "Failed to manage device ID", e);
            String fallbackId = "fallback_" + UUID.randomUUID().toString();
            JSObject res = new JSObject();
            res.put("deviceId", fallbackId);
            call.resolve(res);
        }
    }
}
