/**
 * Mobile Runtime Compatibility Layer - Media Handling
 * DC Protocol: DC_RUNTIME_MEDIA_001
 * 
 * Handles Base64/Blob conversion, ObjectURL memory cleanup,
 * and upload progress tracking for mobile environments.
 * Updated: Uses mobileScheduler for background-safe cleanup
 */

import { mobileScheduler } from './scheduler';

const SCHEDULER_MEDIA_CLEANUP_ID = 'media-objecturl-cleanup';

interface ObjectURLEntry {
  url: string;
  createdAt: number;
  source: string;
}

interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

type ProgressCallback = (progress: UploadProgress) => void;

class MediaRuntime {
  private objectURLs: Map<string, ObjectURLEntry> = new Map();
  private maxObjectURLAge: number = 5 * 60 * 1000;

  init(): void {
    this.startCleanupTimer();
    console.log('[DC_MEDIA] Initialized with auto-cleanup');
  }

  private startCleanupTimer(): void {
    if (mobileScheduler.isScheduled(SCHEDULER_MEDIA_CLEANUP_ID)) return;
    
    mobileScheduler.schedule(
      SCHEDULER_MEDIA_CLEANUP_ID,
      () => { this.cleanupExpiredURLs(); },
      60000,
      { runInBackground: false, immediateOnResume: true }
    );
  }

  private cleanupExpiredURLs(): void {
    const now = Date.now();
    let cleaned = 0;

    this.objectURLs.forEach((entry, id) => {
      if (now - entry.createdAt > this.maxObjectURLAge) {
        URL.revokeObjectURL(entry.url);
        this.objectURLs.delete(id);
        cleaned++;
      }
    });

    if (cleaned > 0) {
      console.log(`[DC_MEDIA] Cleaned up ${cleaned} expired object URLs`);
    }
  }

  createObjectURL(blob: Blob, source: string = 'unknown'): string {
    const url = URL.createObjectURL(blob);
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    this.objectURLs.set(id, {
      url,
      createdAt: Date.now(),
      source
    });

    return url;
  }

  revokeObjectURL(url: string): void {
    URL.revokeObjectURL(url);
    
    for (const [id, entry] of this.objectURLs) {
      if (entry.url === url) {
        this.objectURLs.delete(id);
        break;
      }
    }
  }

  revokeAllObjectURLs(): void {
    this.objectURLs.forEach((entry) => {
      URL.revokeObjectURL(entry.url);
    });
    this.objectURLs.clear();
    console.log('[DC_MEDIA] Revoked all object URLs');
  }

  base64ToBlob(base64: string, mimeType: string = 'image/jpeg'): Blob {
    const cleanBase64 = base64.replace(/^data:[^;]+;base64,/, '');
    const byteCharacters = atob(cleanBase64);
    const byteNumbers = new Array(byteCharacters.length);
    
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
  }

  base64ToFile(base64: string, filename: string, mimeType: string = 'image/jpeg'): File {
    const blob = this.base64ToBlob(base64, mimeType);
    return new File([blob], filename, { type: mimeType });
  }

  async blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        resolve(base64.split(',')[1] || base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  async fileToBase64(file: File): Promise<string> {
    return this.blobToBase64(file);
  }

  async uploadWithProgress(
    url: string,
    formData: FormData,
    headers: Record<string, string> = {},
    onProgress?: ProgressCallback
  ): Promise<Response> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable && onProgress) {
          onProgress({
            loaded: event.loaded,
            total: event.total,
            percentage: Math.round((event.loaded / event.total) * 100)
          });
        }
      });

      xhr.addEventListener('load', () => {
        const response = new Response(xhr.response, {
          status: xhr.status,
          statusText: xhr.statusText,
          headers: this.parseHeaders(xhr.getAllResponseHeaders())
        });
        resolve(response);
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload aborted'));
      });

      xhr.addEventListener('timeout', () => {
        reject(new Error('Upload timeout'));
      });

      xhr.open('POST', url, true);
      xhr.timeout = 120000;

      Object.entries(headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value);
      });

      xhr.send(formData);
    });
  }

  private parseHeaders(headerString: string): Headers {
    const headers = new Headers();
    const lines = headerString.trim().split('\r\n');
    
    lines.forEach(line => {
      const parts = line.split(': ');
      if (parts.length === 2) {
        headers.append(parts[0], parts[1]);
      }
    });
    
    return headers;
  }

  async compressImage(
    base64: string,
    maxWidth: number = 1920,
    maxHeight: number = 1080,
    quality: number = 0.8
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      
      img.onload = () => {
        let { width, height } = img;
        
        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }
        
        if (height > maxHeight) {
          width = (width * maxHeight) / height;
          height = maxHeight;
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new Error('Failed to get canvas context'));
          return;
        }
        
        ctx.drawImage(img, 0, 0, width, height);
        
        const compressed = canvas.toDataURL('image/jpeg', quality);
        resolve(compressed.split(',')[1] || compressed);
      };

      img.onerror = () => reject(new Error('Failed to load image'));
      
      const prefix = base64.startsWith('data:') ? '' : 'data:image/jpeg;base64,';
      img.src = prefix + base64;
    });
  }

  getMimeTypeFromBase64(base64: string): string {
    if (base64.startsWith('data:')) {
      const match = base64.match(/data:([^;]+);/);
      return match ? match[1] : 'application/octet-stream';
    }
    
    if (base64.startsWith('/9j/')) return 'image/jpeg';
    if (base64.startsWith('iVBORw')) return 'image/png';
    if (base64.startsWith('R0lGOD')) return 'image/gif';
    if (base64.startsWith('UklGR')) return 'image/webp';
    if (base64.startsWith('AAAA')) return 'video/mp4';
    
    return 'application/octet-stream';
  }

  getFileSizeFromBase64(base64: string): number {
    const cleanBase64 = base64.replace(/^data:[^;]+;base64,/, '');
    const padding = (cleanBase64.match(/=/g) || []).length;
    return Math.floor((cleanBase64.length * 3) / 4) - padding;
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  cleanup(): void {
    mobileScheduler.cancel(SCHEDULER_MEDIA_CLEANUP_ID);
    this.revokeAllObjectURLs();
    console.log('[DC_MEDIA] Cleanup complete');
  }
}

export const mediaRuntime = new MediaRuntime();
