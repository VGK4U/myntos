export class ImageEditor {
  constructor(imageUrl, onSave) {
    this.originalImage = new Image();
    this.originalImage.crossOrigin = 'anonymous';
    this.imageUrl = imageUrl;
    this.onSave = onSave;
    this.canvas = null;
    this.ctx = null;
    this.cropper = null;
    this.isCropMode = false;
    this.cropData = null;
    this.logoImage = null;
    this.logoPosition = { x: 10, y: 10 };
    this.logoSize = { width: 100, height: 100 };
    this.isDraggingLogo = false;
    
    this.edits = {
      brightness: 0,
      contrast: 0,
      filter: 'none'
    };
  }

  async init(canvasId) {
    return new Promise((resolve, reject) => {
      this.canvas = document.getElementById(canvasId);
      this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
      
      this.originalImage.onload = () => {
        this.canvas.width = Math.min(this.originalImage.width, 800);
        this.canvas.height = (this.canvas.width / this.originalImage.width) * this.originalImage.height;
        this.render();
        this.attachCanvasListeners();
        resolve();
      };
      
      this.originalImage.onerror = () => reject(new Error('Failed to load image'));
      this.originalImage.src = this.imageUrl;
    });
  }

  enableCropMode(aspectRatio = NaN) {
    this.isCropMode = true;
    
    const existingContainer = document.getElementById('cropContainer');
    if (existingContainer) {
      existingContainer.remove();
    }
    
    const currentState = this.canvas.toDataURL();
    
    const cropContainer = document.createElement('div');
    cropContainer.id = 'cropContainer';
    cropContainer.style.display = 'none';
    document.body.appendChild(cropContainer);
    
    const cropImage = document.createElement('img');
    cropImage.id = 'cropImage';
    cropImage.src = currentState;
    cropImage.crossOrigin = 'anonymous';
    cropContainer.appendChild(cropImage);
    
    cropImage.onload = () => {
      try {
        this.canvas.style.display = 'none';
        cropContainer.style.display = 'block';
        
        this.cropper = new Cropper(cropImage, {
          aspectRatio: aspectRatio,
          viewMode: 1,
          autoCropArea: 1,
          responsive: true,
          restore: false,
          guides: true,
          center: true,
          highlight: true,
          cropBoxMovable: true,
          cropBoxResizable: true,
          toggleDragModeOnDblclick: false,
        });
      } catch (error) {
        console.error('Failed to initialize Cropper:', error);
        this.isCropMode = false;
        this.canvas.style.display = 'block';
        cropContainer.remove();
      }
    };
    
    cropImage.onerror = () => {
      console.error('Failed to load crop image');
      this.isCropMode = false;
      this.canvas.style.display = 'block';
      cropContainer.remove();
    };
  }

  applyCrop(callback) {
    if (!this.cropper) return;
    
    const croppedCanvas = this.cropper.getCroppedCanvas();
    this.cropData = this.cropper.getData();
    
    const croppedDataUrl = croppedCanvas.toDataURL();
    
    this.originalImage.onload = () => {
      this.canvas.width = croppedCanvas.width;
      this.canvas.height = croppedCanvas.height;
      this.ctx.drawImage(croppedCanvas, 0, 0);
      
      this.imageUrl = croppedDataUrl;
      
      this.edits.brightness = 0;
      this.edits.contrast = 0;
      this.edits.filter = 'none';
      
      this.cropper.destroy();
      this.cropper = null;
      
      const cropContainer = document.getElementById('cropContainer');
      if (cropContainer) {
        cropContainer.remove();
      }
      
      this.canvas.style.display = 'block';
      this.isCropMode = false;
      this.render();
      
      if (callback) callback();
    };
    
    this.originalImage.src = croppedDataUrl;
  }

  cancelCrop() {
    if (this.cropper) {
      this.cropper.destroy();
      this.cropper = null;
    }
    
    const cropContainer = document.getElementById('cropContainer');
    if (cropContainer) {
      cropContainer.remove();
    }
    
    this.canvas.style.display = 'block';
    this.isCropMode = false;
  }

  attachCanvasListeners() {
    let isDragging = false;
    let dragOffset = { x: 0, y: 0 };

    this.canvas.addEventListener('mousedown', (e) => {
      if (!this.logoImage || this.isCropMode) return;
      
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      if (x >= this.logoPosition.x && x <= this.logoPosition.x + this.logoSize.width &&
          y >= this.logoPosition.y && y <= this.logoPosition.y + this.logoSize.height) {
        isDragging = true;
        dragOffset = {
          x: x - this.logoPosition.x,
          y: y - this.logoPosition.y
        };
        this.canvas.style.cursor = 'move';
      }
    });

    this.canvas.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      
      const rect = this.canvas.getBoundingClientRect();
      this.logoPosition.x = e.clientX - rect.left - dragOffset.x;
      this.logoPosition.y = e.clientY - rect.top - dragOffset.y;
      
      this.logoPosition.x = Math.max(0, Math.min(this.canvas.width - this.logoSize.width, this.logoPosition.x));
      this.logoPosition.y = Math.max(0, Math.min(this.canvas.height - this.logoSize.height, this.logoPosition.y));
      
      this.render();
    });

    this.canvas.addEventListener('mouseup', () => {
      isDragging = false;
      this.canvas.style.cursor = 'default';
    });
  }

  setBrightness(value) {
    this.edits.brightness = parseFloat(value);
    this.render();
  }

  setContrast(value) {
    this.edits.contrast = parseFloat(value);
    this.render();
  }

  setFilter(filterName) {
    this.edits.filter = filterName;
    this.render();
  }

  async uploadLogo(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.logoImage = new Image();
        this.logoImage.onload = () => {
          const aspectRatio = this.logoImage.width / this.logoImage.height;
          this.logoSize.width = 100;
          this.logoSize.height = 100 / aspectRatio;
          this.logoPosition = { 
            x: this.canvas.width - this.logoSize.width - 10, 
            y: 10 
          };
          this.render();
          resolve();
        };
        this.logoImage.src = e.target.result;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  removeLogo() {
    this.logoImage = null;
    this.render();
  }

  render() {
    if (this.isCropMode) return;
    
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    this.ctx.drawImage(this.originalImage, 0, 0, this.canvas.width, this.canvas.height);
    
    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = imageData.data;
    
    const brightness = this.edits.brightness;
    const contrast = this.edits.contrast;
    const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));
    
    for (let i = 0; i < data.length; i += 4) {
      let r = data[i];
      let g = data[i + 1];
      let b = data[i + 2];
      
      r += brightness;
      g += brightness;
      b += brightness;
      
      r = factor * (r - 128) + 128;
      g = factor * (g - 128) + 128;
      b = factor * (b - 128) + 128;
      
      if (this.edits.filter === 'grayscale') {
        const gray = 0.299 * r + 0.587 * g + 0.114 * b;
        r = g = b = gray;
      } else if (this.edits.filter === 'sepia') {
        const tr = 0.393 * r + 0.769 * g + 0.189 * b;
        const tg = 0.349 * r + 0.686 * g + 0.168 * b;
        const tb = 0.272 * r + 0.534 * g + 0.131 * b;
        r = tr;
        g = tg;
        b = tb;
      } else if (this.edits.filter === 'vintage') {
        r *= 1.2;
        g *= 1.1;
        b *= 0.9;
      }
      
      data[i] = Math.min(255, Math.max(0, r));
      data[i + 1] = Math.min(255, Math.max(0, g));
      data[i + 2] = Math.min(255, Math.max(0, b));
    }
    
    this.ctx.putImageData(imageData, 0, 0);
    
    if (this.logoImage) {
      this.ctx.save();
      this.ctx.globalAlpha = 0.8;
      this.ctx.drawImage(
        this.logoImage,
        this.logoPosition.x,
        this.logoPosition.y,
        this.logoSize.width,
        this.logoSize.height
      );
      this.ctx.strokeStyle = '#fff';
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(
        this.logoPosition.x,
        this.logoPosition.y,
        this.logoSize.width,
        this.logoSize.height
      );
      this.ctx.restore();
    }
  }

  async getEditedImageBlob() {
    return new Promise((resolve) => {
      this.canvas.toBlob((blob) => {
        resolve(blob);
      }, 'image/jpeg', 0.9);
    });
  }

  getEditMetadata() {
    return {
      brightness: this.edits.brightness,
      contrast: this.edits.contrast,
      filter: this.edits.filter,
      crop: this.cropData,
      logo: this.logoImage ? {
        position: this.logoPosition,
        size: this.logoSize
      } : null
    };
  }

  reset() {
    this.edits = {
      brightness: 0,
      contrast: 0,
      filter: 'none'
    };
    this.logoImage = null;
    this.cropData = null;
    if (this.cropper) {
      this.cancelCrop();
    }
    this.render();
  }
}
