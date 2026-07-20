import { defineConfig } from 'vite';
import { resolve } from 'path';

// DC_VITE_BASE_001: Use VITE_BASE_URL env var to control the base path.
// Replit web server: base='/mobile/' (default, no env var needed)
// Codemagic APK build: VITE_BASE_URL='/' — assets must be at root inside APK WebView.
// Without this, dist/index.html has src="/mobile/assets/..." which 404s in the APK.
const viteBase = process.env.VITE_BASE_URL || '/mobile/';

export default defineConfig({
  root: '.',
  base: viteBase,
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    target: 'es2022',
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      input: resolve(__dirname, 'index.html'),
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/@capacitor/core')) return 'vendor-capacitor-core';
          if (id.includes('node_modules/@capacitor/')) return 'vendor-capacitor-plugins';
          if (id.includes('node_modules/')) return 'vendor';
          if (id.includes('/src/services/gps.service')) return 'services-gps';
          if (id.includes('/src/services/')) return 'services';
          if (id.includes('/src/runtime/')) return 'services';
          if (id.includes('/src/journey/')) return 'services';
          if (id.includes('/src/constants/')) return 'services';
          if (id.includes('/src/config/')) return 'services';
          if (id.includes('/src/pages/mnr/')) return 'pages-mnr';
          if (id.includes('/src/pages/vgk/')) return 'pages-vgk';
          if (id.includes('/src/pages/partner/')) return 'pages-partner';
          if (id.includes('/src/pages/zynova/')) return 'pages-zynova';
          if (id.includes('/src/pages/myntreal/')) return 'pages-myntreal';
          if (id.includes('/src/pages/')) return 'pages-staff';
          if (id.includes('/src/components/')) return 'components';
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5100,
    host: true
  }
});
