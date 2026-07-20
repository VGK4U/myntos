/**
 * Camera Service for Selfie Capture
 * DC Protocol: DC_MOBILE_CAMERA_001
 * Handles mandatory clock-in/out selfie capture
 */

import { Camera, CameraResultType, CameraSource, Photo } from '@capacitor/camera';

interface SelfieResult {
  success: boolean;
  base64?: string;
  error?: string;
  timestamp: number;
}

class CameraService {
  
  async takeSelfie(): Promise<SelfieResult> {
    try {
      // Request camera permission
      const permission = await Camera.requestPermissions();
      if (permission.camera !== 'granted') {
        return {
          success: false,
          error: 'Camera permission denied',
          timestamp: Date.now()
        };
      }

      // Capture selfie from front camera
      const photo: Photo = await Camera.getPhoto({
        quality: 80,
        allowEditing: false,
        resultType: CameraResultType.Base64,
        source: CameraSource.Camera,
        direction: 'front' as any, // Front camera for selfie
        saveToGallery: false,
        correctOrientation: true,
        width: 640,
        height: 480
      });

      if (!photo.base64String) {
        return {
          success: false,
          error: 'Failed to capture photo',
          timestamp: Date.now()
        };
      }

      console.log('[DC_CAMERA] Selfie captured successfully');
      
      return {
        success: true,
        base64: photo.base64String,
        timestamp: Date.now()
      };
    } catch (error: any) {
      console.error('[DC_CAMERA] Selfie capture failed:', error);
      
      // Handle user cancellation
      if (error.message?.includes('cancelled') || error.message?.includes('canceled')) {
        return {
          success: false,
          error: 'Photo capture cancelled',
          timestamp: Date.now()
        };
      }

      return {
        success: false,
        error: error.message || 'Camera error',
        timestamp: Date.now()
      };
    }
  }

  async takeDocumentPhoto(): Promise<SelfieResult> {
    try {
      const permission = await Camera.requestPermissions();
      if (permission.camera !== 'granted') {
        return {
          success: false,
          error: 'Camera permission denied',
          timestamp: Date.now()
        };
      }

      const photo: Photo = await Camera.getPhoto({
        quality: 90,
        allowEditing: false,
        resultType: CameraResultType.Base64,
        source: CameraSource.Camera,
        direction: 'rear' as any, // Back camera for documents
        saveToGallery: false,
        correctOrientation: true
      });

      if (!photo.base64String) {
        return {
          success: false,
          error: 'Failed to capture photo',
          timestamp: Date.now()
        };
      }

      return {
        success: true,
        base64: photo.base64String,
        timestamp: Date.now()
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Camera error',
        timestamp: Date.now()
      };
    }
  }

  async pickFromGallery(): Promise<SelfieResult> {
    try {
      const permission = await Camera.requestPermissions();
      if (permission.photos !== 'granted') {
        return {
          success: false,
          error: 'Photo library permission denied',
          timestamp: Date.now()
        };
      }

      const photo: Photo = await Camera.getPhoto({
        quality: 80,
        allowEditing: false,
        resultType: CameraResultType.Base64,
        source: CameraSource.Photos
      });

      if (!photo.base64String) {
        return {
          success: false,
          error: 'Failed to load photo',
          timestamp: Date.now()
        };
      }

      return {
        success: true,
        base64: photo.base64String,
        timestamp: Date.now()
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.message || 'Gallery error',
        timestamp: Date.now()
      };
    }
  }

  // Add timestamp overlay to image (done server-side for security)
  formatBase64ForUpload(base64: string): string {
    // Ensure proper data URL format
    if (base64.startsWith('data:image')) {
      return base64;
    }
    return `data:image/jpeg;base64,${base64}`;
  }
}

export const cameraService = new CameraService();
