/**
 * Universal Upload Widget
 * DC Protocol: Dual storage, auto-compression, complete audit trail
 * WVV Protocol: Real-time validation, progress tracking, error handling
 * 
 * FEATURES:
 * - Drag & drop file upload
 * - Real-time progress bar
 * - File type validation (images + documents + videos)
 * - Size validation (5MB images/docs, 20MB videos)
 * - Automatic background compression
 * - Complete error handling
 * 
 * USAGE:
 * 
 * HTML:
 * <div id="uploadContainer"></div>
 * 
 * JavaScript:
 * const uploader = new UniversalUploader({
 *     containerId: 'uploadContainer',
 *     uploadUrl: '/api/v1/endpoint/upload',
 *     maxFiles: 5,
 *     allowVideos: true,  // Enable 20MB video uploads
 *     onUploadComplete: (response) => console.log('Uploaded:', response),
 *     onUploadError: (error) => console.error('Error:', error)
 * });
 */

class UniversalUploader {
    constructor(options) {
        // Configuration
        this.config = {
            containerId: options.containerId || 'uploadContainer',
            uploadUrl: options.uploadUrl,
            maxFiles: options.maxFiles || 10,
            allowImages: options.allowImages !== false,  // Default true
            allowDocuments: options.allowDocuments !== false,  // Default true
            allowVideos: options.allowVideos || false,  // Default false (20MB limit)
            maxImageSize: 5 * 1024 * 1024,  // 5MB
            maxDocumentSize: 5 * 1024 * 1024,  // 5MB (DC Protocol requirement)
            maxVideoSize: 20 * 1024 * 1024,  // 20MB (DC Protocol requirement)
            onUploadComplete: options.onUploadComplete || (() => {}),
            onUploadError: options.onUploadError || (() => {}),
            onUploadProgress: options.onUploadProgress || (() => {}),
            showPreview: options.showPreview !== false,  // Default true
            multiple: options.multiple !== false  // Default true
        };
        
        // State
        this.files = [];
        this.uploadQueue = [];
        this.uploading = false;
        
        // Initialize
        this.init();
    }
    
    init() {
        this.container = document.getElementById(this.config.containerId);
        if (!this.container) {
            console.error(`UniversalUploader: Container #${this.config.containerId} not found`);
            return;
        }
        
        this.render();
        this.attachEvents();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="universal-upload-widget">
                <div class="upload-dropzone" id="${this.config.containerId}_dropzone">
                    <i class="fas fa-cloud-upload-alt upload-icon"></i>
                    <h5 class="upload-title">Drop files here or click to browse</h5>
                    <p class="upload-hint">
                        ${this.getAcceptedTypesText()}
                    </p>
                    <p class="upload-hint text-muted" style="font-size: 12px;">
                        ${this.config.allowImages ? 'Images: max 5MB (auto-compressed)' : ''} 
                        ${this.config.allowImages && (this.config.allowDocuments || this.config.allowVideos) ? ' | ' : ''}
                        ${this.config.allowDocuments ? 'Documents: max 5MB' : ''}
                        ${this.config.allowDocuments && this.config.allowVideos ? ' | ' : ''}
                        ${this.config.allowVideos ? 'Videos: max 20MB (auto-compressed)' : ''}
                    </p>
                    <input type="file" id="${this.config.containerId}_fileInput" 
                           style="display: none;" 
                           ${this.config.multiple ? 'multiple' : ''}
                           accept="${this.getAcceptedTypes()}">
                </div>
                
                <div class="upload-progress-container" id="${this.config.containerId}_progress" style="display: none;">
                    <div class="upload-progress-bar">
                        <div class="upload-progress-fill" id="${this.config.containerId}_progressFill" style="width: 0%;">
                            <span class="upload-progress-text" id="${this.config.containerId}_progressText">0%</span>
                        </div>
                    </div>
                    <p class="upload-progress-file" id="${this.config.containerId}_progressFile">Uploading...</p>
                </div>
                
                <div class="upload-file-list" id="${this.config.containerId}_fileList"></div>
            </div>
        `;
        
        this.injectStyles();
    }
    
    injectStyles() {
        if (document.getElementById('universal-upload-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'universal-upload-styles';
        style.textContent = `
            .universal-upload-widget { margin: 16px 0; }
            
            .upload-dropzone {
                border: 2px dashed #d1d5db;
                border-radius: 12px;
                padding: 40px 20px;
                text-align: center;
                background: #f9fafb;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .upload-dropzone:hover {
                border-color: #4f46e5;
                background: #eef2ff;
            }
            
            .upload-dropzone.drag-over {
                border-color: #4f46e5;
                background: #eef2ff;
                transform: scale(1.02);
            }
            
            .upload-icon {
                font-size: 48px;
                color: #9ca3af;
                margin-bottom: 12px;
            }
            
            .upload-dropzone:hover .upload-icon {
                color: #4f46e5;
            }
            
            .upload-title {
                font-size: 16px;
                font-weight: 600;
                color: #374151;
                margin-bottom: 8px;
            }
            
            .upload-hint {
                font-size: 14px;
                color: #6b7280;
                margin-bottom: 4px;
            }
            
            .upload-progress-container {
                margin: 16px 0;
                padding: 16px;
                background: #f9fafb;
                border-radius: 8px;
            }
            
            .upload-progress-bar {
                width: 100%;
                height: 28px;
                background: #e5e7eb;
                border-radius: 14px;
                overflow: hidden;
                position: relative;
            }
            
            .upload-progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #4f46e5, #8b5cf6);
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            
            .upload-progress-text {
                font-size: 13px;
                font-weight: 600;
                color: white;
                position: absolute;
                left: 50%;
                transform: translateX(-50%);
                z-index: 2;
            }
            
            .upload-progress-file {
                font-size: 13px;
                color: #6b7280;
                margin-top: 8px;
                text-align: center;
            }
            
            .upload-file-list {
                margin-top: 16px;
            }
            
            .upload-file-item {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .upload-file-icon {
                width: 40px;
                height: 40px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
            }
            
            .upload-file-icon.image { background: #dbeafe; color: #2563eb; }
            .upload-file-icon.document { background: #fee2e2; color: #dc2626; }
            .upload-file-icon.success { background: #dcfce7; color: #166534; }
            .upload-file-icon.error { background: #fee2e2; color: #dc2626; }
            
            .upload-file-details {
                flex: 1;
            }
            
            .upload-file-name {
                font-size: 14px;
                font-weight: 500;
                color: #1f2937;
                margin-bottom: 2px;
            }
            
            .upload-file-size {
                font-size: 12px;
                color: #6b7280;
            }
            
            .upload-file-status {
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 12px;
                font-weight: 500;
            }
            
            .upload-file-status.uploading {
                background: #dbeafe;
                color: #1e40af;
            }
            
            .upload-file-status.success {
                background: #dcfce7;
                color: #166534;
            }
            
            .upload-file-status.error {
                background: #fee2e2;
                color: #991b1b;
            }
            
            .upload-file-actions {
                display: flex;
                gap: 8px;
            }
            
            .upload-remove-btn {
                width: 28px;
                height: 28px;
                border-radius: 6px;
                border: none;
                background: #fee2e2;
                color: #dc2626;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: background 0.2s;
            }
            
            .upload-remove-btn:hover {
                background: #fca5a5;
            }
        `;
        
        document.head.appendChild(style);
    }
    
    getAcceptedTypes() {
        const types = [];
        if (this.config.allowImages) {
            types.push('image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp');
        }
        if (this.config.allowVideos) {
            types.push('video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska');
        }
        if (this.config.allowDocuments) {
            types.push('application/pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv');
        }
        return types.join(',');
    }
    
    getAcceptedTypesText() {
        const parts = [];
        if (this.config.allowImages) parts.push('Images (JPEG, PNG, GIF, WebP, BMP)');
        if (this.config.allowVideos) parts.push('Videos (MP4, WebM, QuickTime, AVI, MKV)');
        if (this.config.allowDocuments) parts.push('Documents (PDF, DOC, XLS, PPT, TXT, CSV)');
        return parts.join(' or ');
    }
    
    attachEvents() {
        const dropzone = document.getElementById(`${this.config.containerId}_dropzone`);
        const fileInput = document.getElementById(`${this.config.containerId}_fileInput`);
        
        // Click to browse
        dropzone.addEventListener('click', () => fileInput.click());
        
        // Drag & drop
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });
        
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('drag-over');
        });
        
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // File input change
        fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
    }
    
    handleFiles(fileList) {
        const files = Array.from(fileList);
        
        // Validate file count
        if (this.files.length + files.length > this.config.maxFiles) {
            this.config.onUploadError(`Maximum ${this.config.maxFiles} files allowed`);
            return;
        }
        
        // Validate each file
        for (const file of files) {
            const validation = this.validateFile(file);
            if (!validation.valid) {
                this.config.onUploadError(validation.error);
                continue;
            }
            
            this.files.push({
                file: file,
                id: Date.now() + Math.random(),
                status: 'pending',
                progress: 0
            });
        }
        
        this.renderFileList();
        
        // Start upload if not already uploading
        if (!this.uploading) {
            this.uploadNext();
        }
    }
    
    validateFile(file) {
        const isImage = file.type.startsWith('image/');
        const isVideo = file.type.startsWith('video/');
        const isDocument = !isImage && !isVideo;
        
        // Check if type is allowed
        if (isImage && !this.config.allowImages) {
            return { valid: false, error: 'Image files are not allowed' };
        }
        if (isVideo && !this.config.allowVideos) {
            return { valid: false, error: 'Video files are not allowed' };
        }
        if (isDocument && !this.config.allowDocuments) {
            return { valid: false, error: 'Document files are not allowed' };
        }
        
        // Check file size
        if (isImage && file.size > this.config.maxImageSize) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            return { valid: false, error: `Image "${file.name}" (${sizeMB}MB) exceeds 5MB limit` };
        }
        if (isVideo && file.size > this.config.maxVideoSize) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            return { valid: false, error: `Video "${file.name}" (${sizeMB}MB) exceeds 20MB limit` };
        }
        if (isDocument && file.size > this.config.maxDocumentSize) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            return { valid: false, error: `Document "${file.name}" (${sizeMB}MB) exceeds 5MB limit` };
        }
        
        return { valid: true };
    }
    
    renderFileList() {
        const listContainer = document.getElementById(`${this.config.containerId}_fileList`);
        
        if (this.files.length === 0) {
            listContainer.innerHTML = '';
            return;
        }
        
        listContainer.innerHTML = this.files.map((fileObj) => {
            const isImage = fileObj.file.type.startsWith('image/');
            const fileSize = this.formatFileSize(fileObj.file.size);
            const iconClass = isImage ? 'image' : 'document';
            const iconName = isImage ? 'fa-image' : 'fa-file-alt';
            
            let statusHTML = '';
            if (fileObj.status === 'uploading') {
                statusHTML = '<span class="upload-file-status uploading"><i class="fas fa-spinner fa-spin"></i> Uploading...</span>';
            } else if (fileObj.status === 'success') {
                statusHTML = '<span class="upload-file-status success"><i class="fas fa-check"></i> Uploaded</span>';
            } else if (fileObj.status === 'error') {
                statusHTML = `<span class="upload-file-status error"><i class="fas fa-exclamation-circle"></i> Failed</span>`;
            }
            
            return `
                <div class="upload-file-item" data-file-id="${fileObj.id}">
                    <div class="upload-file-icon ${iconClass}">
                        <i class="fas ${iconName}"></i>
                    </div>
                    <div class="upload-file-details">
                        <div class="upload-file-name">${fileObj.file.name}</div>
                        <div class="upload-file-size">${fileSize}</div>
                    </div>
                    ${statusHTML}
                    ${fileObj.status === 'pending' || fileObj.status === 'error' ? `
                        <button class="upload-remove-btn" onclick="window.uploaders['${this.config.containerId}'].removeFile(${fileObj.id})">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                </div>
            `;
        }).join('');
    }
    
    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    }
    
    removeFile(fileId) {
        this.files = this.files.filter(f => f.id !== fileId);
        this.renderFileList();
    }
    
    async uploadNext() {
        const pendingFile = this.files.find(f => f.status === 'pending');
        if (!pendingFile) {
            this.uploading = false;
            return;
        }
        
        this.uploading = true;
        pendingFile.status = 'uploading';
        this.renderFileList();
        this.showProgress(pendingFile.file.name);
        
        try {
            const result = await this.uploadFile(pendingFile.file, (progress) => {
                this.updateProgress(progress);
                this.config.onUploadProgress(progress, pendingFile.file);
            });
            
            pendingFile.status = 'success';
            pendingFile.result = result;
            this.config.onUploadComplete(result, pendingFile.file);
            
        } catch (error) {
            pendingFile.status = 'error';
            pendingFile.error = error.message;
            this.config.onUploadError(error.message, pendingFile.file);
        }
        
        this.renderFileList();
        this.hideProgress();
        
        // Upload next file
        setTimeout(() => this.uploadNext(), 500);
    }
    
    async uploadFile(file, onProgress) {
        const formData = new FormData();
        formData.append('file', file);
        
        const xhr = new XMLHttpRequest();
        
        return new Promise((resolve, reject) => {
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    onProgress(percentComplete);
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (e) {
                        reject(new Error('Invalid server response'));
                    }
                } else {
                    try {
                        const error = JSON.parse(xhr.responseText);
                        reject(new Error(error.detail || 'Upload failed'));
                    } catch (e) {
                        reject(new Error(`Upload failed: ${xhr.statusText}`));
                    }
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Network error'));
            });
            
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload cancelled'));
            });
            
            // Get auth token
            const token = localStorage.getItem('token');
            xhr.open('POST', this.config.uploadUrl, true);
            if (token) {
                xhr.setRequestHeader('Authorization', `Bearer ${token}`);
            }
            
            xhr.send(formData);
        });
    }
    
    showProgress(filename) {
        const progressContainer = document.getElementById(`${this.config.containerId}_progress`);
        const progressFile = document.getElementById(`${this.config.containerId}_progressFile`);
        progressContainer.style.display = 'block';
        progressFile.textContent = `Uploading: ${filename}`;
    }
    
    updateProgress(percent) {
        const progressFill = document.getElementById(`${this.config.containerId}_progressFill`);
        const progressText = document.getElementById(`${this.config.containerId}_progressText`);
        progressFill.style.width = `${percent}%`;
        progressText.textContent = `${Math.round(percent)}%`;
    }
    
    hideProgress() {
        const progressContainer = document.getElementById(`${this.config.containerId}_progress`);
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 1000);
    }
    
    reset() {
        this.files = [];
        this.renderFileList();
        const fileInput = document.getElementById(`${this.config.containerId}_fileInput`);
        if (fileInput) fileInput.value = '';
    }
    
    getUploadedFiles() {
        return this.files.filter(f => f.status === 'success').map(f => f.result);
    }
}

// Global registry for uploader instances
window.uploaders = window.uploaders || {};
