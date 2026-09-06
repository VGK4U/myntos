import { CapacitorConfig } from '@capacitor/cli';

// Development mode: Set to true ONLY for local live-reload during active development.
// MUST be false for any Codemagic / production APK build.
const DEV_MODE = false;
const DEV_SERVER_URL = 'http://192.168.1.10:5001/mobile';

const config: CapacitorConfig = {
  appId: 'com.myntos.mobile',
  appName: 'MyntReal',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    iosScheme: 'https',
    hostname: 'app.myntreal.com',
    // Enable live reload from dev server in development mode
    ...(DEV_MODE && { url: DEV_SERVER_URL, cleartext: true })
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#1a1a2e',
      showSpinner: true,
      spinnerColor: '#10b981'
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#1a1a2e'
    },
    Camera: {
      cameraPermission: 'MyntReal needs camera access for attendance verification photos',
      photoLibraryPermission: 'MyntReal needs photo library access to upload documents'
    },
    Geolocation: {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0
    },
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert']
    }
  },
  android: {
    allowMixedContent: false,
    captureInput: true,
    webContentsDebuggingEnabled: DEV_MODE,
    orientation: 'portrait'
  },
  ios: {
    contentInset: 'always',
    allowsLinkPreview: false,
    preferredContentMode: 'mobile'
  }
};

export default config;
