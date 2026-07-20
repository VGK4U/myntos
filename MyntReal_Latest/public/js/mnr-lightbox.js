/**
 * MNR Lightbox Component
 * DC Protocol Compliant - Media Viewer with Navigation
 * Version: 1.0.0
 * 
 * Features:
 * - Fullscreen popup for images and videos
 * - Left/Right navigation arrows
 * - Keyboard support (Arrow keys, ESC)
 * - Touch swipe support for mobile
 * - Media counter indicator
 * - WVV Protocol: Validation and error handling
 */

(function() {
    'use strict';

    // Lightbox state
    let lightboxOpen = false;
    let currentMediaIndex = 0;
    let mediaItems = [];
    let touchStartX = 0;
    let touchEndX = 0;

    // Create lightbox HTML structure
    function createLightboxHTML() {
        const lightboxHTML = `
            <div id="mnrLightbox" class="mnr-lightbox" style="display: none;">
                <div class="mnr-lightbox-overlay"></div>
                <div class="mnr-lightbox-container">
                    <button class="mnr-lightbox-close" aria-label="Close lightbox">
                        <i class="fas fa-times"></i>
                    </button>
                    <button class="mnr-lightbox-nav mnr-lightbox-prev" aria-label="Previous media">
                        <i class="fas fa-chevron-left"></i>
                    </button>
                    <div class="mnr-lightbox-content">
                        <div class="mnr-lightbox-media"></div>
                        <div class="mnr-lightbox-counter"></div>
                    </div>
                    <button class="mnr-lightbox-nav mnr-lightbox-next" aria-label="Next media">
                        <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        `;

        // Add CSS styles
        const lightboxStyles = `
            <style id="mnrLightboxStyles">
                .mnr-lightbox {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: 99999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .mnr-lightbox-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.95);
                    cursor: pointer;
                }
                
                .mnr-lightbox-container {
                    position: relative;
                    width: 100%;
                    height: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 60px 80px;
                    box-sizing: border-box;
                }
                
                .mnr-lightbox-close {
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    width: 44px;
                    height: 44px;
                    background: rgba(255, 255, 255, 0.1);
                    border: none;
                    border-radius: 50%;
                    color: white;
                    font-size: 20px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.3s ease;
                    z-index: 100001;
                }
                
                .mnr-lightbox-close:hover {
                    background: rgba(249, 115, 22, 0.8);
                    transform: scale(1.1);
                }
                
                .mnr-lightbox-nav {
                    position: absolute;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 50px;
                    height: 50px;
                    background: rgba(255, 255, 255, 0.1);
                    border: none;
                    border-radius: 50%;
                    color: white;
                    font-size: 20px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.3s ease;
                    z-index: 100001;
                }
                
                .mnr-lightbox-nav:hover {
                    background: rgba(249, 115, 22, 0.8);
                    transform: translateY(-50%) scale(1.1);
                }
                
                .mnr-lightbox-nav:disabled {
                    opacity: 0.3;
                    cursor: not-allowed;
                }
                
                .mnr-lightbox-prev {
                    left: 20px;
                }
                
                .mnr-lightbox-next {
                    right: 20px;
                }
                
                .mnr-lightbox-content {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    max-width: 90%;
                    max-height: 90%;
                    z-index: 100000;
                }
                
                .mnr-lightbox-media {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    max-width: 100%;
                    max-height: calc(100vh - 150px);
                }
                
                .mnr-lightbox-media img {
                    max-width: 100%;
                    max-height: calc(100vh - 150px);
                    object-fit: contain;
                    border-radius: 8px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                }
                
                .mnr-lightbox-media video {
                    max-width: 100%;
                    max-height: calc(100vh - 150px);
                    border-radius: 8px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                    background: #000;
                }
                
                .mnr-lightbox-counter {
                    margin-top: 15px;
                    padding: 8px 16px;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                .mnr-lightbox-loading {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    color: white;
                }
                
                .mnr-lightbox-loading .spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid rgba(255, 255, 255, 0.3);
                    border-top-color: #f97316;
                    border-radius: 50%;
                    animation: mnr-lightbox-spin 1s linear infinite;
                }
                
                .mnr-lightbox-error {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    color: #ef4444;
                    text-align: center;
                    padding: 40px;
                }
                
                .mnr-lightbox-error i {
                    font-size: 48px;
                    margin-bottom: 16px;
                }
                
                @keyframes mnr-lightbox-spin {
                    to { transform: rotate(360deg); }
                }
                
                /* Mobile responsive */
                @media (max-width: 768px) {
                    .mnr-lightbox-container {
                        padding: 50px 15px;
                    }
                    
                    .mnr-lightbox-nav {
                        width: 40px;
                        height: 40px;
                        font-size: 16px;
                    }
                    
                    .mnr-lightbox-prev {
                        left: 10px;
                    }
                    
                    .mnr-lightbox-next {
                        right: 10px;
                    }
                    
                    .mnr-lightbox-close {
                        top: 10px;
                        right: 10px;
                        width: 36px;
                        height: 36px;
                        font-size: 16px;
                    }
                }
                
                /* Clickable media indicator */
                .mnr-lightbox-clickable {
                    cursor: zoom-in;
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }
                
                .mnr-lightbox-clickable:hover {
                    transform: scale(1.02);
                    box-shadow: 0 4px 15px rgba(249, 115, 22, 0.3);
                }
            </style>
        `;

        // Inject styles if not already present
        if (!document.getElementById('mnrLightboxStyles')) {
            document.head.insertAdjacentHTML('beforeend', lightboxStyles);
        }

        // Inject lightbox HTML if not already present
        if (!document.getElementById('mnrLightbox')) {
            document.body.insertAdjacentHTML('beforeend', lightboxHTML);
            initLightboxEvents();
        }
    }

    // Initialize lightbox events
    function initLightboxEvents() {
        const lightbox = document.getElementById('mnrLightbox');
        if (!lightbox) return;

        // Close button
        lightbox.querySelector('.mnr-lightbox-close').addEventListener('click', closeLightbox);

        // Overlay click to close
        lightbox.querySelector('.mnr-lightbox-overlay').addEventListener('click', closeLightbox);

        // Navigation buttons
        lightbox.querySelector('.mnr-lightbox-prev').addEventListener('click', prevMedia);
        lightbox.querySelector('.mnr-lightbox-next').addEventListener('click', nextMedia);

        // Keyboard navigation
        document.addEventListener('keydown', handleKeyboard);

        // Touch swipe support
        lightbox.addEventListener('touchstart', handleTouchStart, { passive: true });
        lightbox.addEventListener('touchend', handleTouchEnd, { passive: true });
    }

    // Handle keyboard navigation
    function handleKeyboard(e) {
        if (!lightboxOpen) return;

        switch(e.key) {
            case 'Escape':
                closeLightbox();
                break;
            case 'ArrowLeft':
                prevMedia();
                break;
            case 'ArrowRight':
                nextMedia();
                break;
        }
    }

    // Touch handlers for swipe
    function handleTouchStart(e) {
        touchStartX = e.changedTouches[0].screenX;
    }

    function handleTouchEnd(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }

    function handleSwipe() {
        const swipeThreshold = 50;
        const diff = touchStartX - touchEndX;
        
        if (Math.abs(diff) > swipeThreshold) {
            if (diff > 0) {
                nextMedia();
            } else {
                prevMedia();
            }
        }
    }

    // Open lightbox with media items
    function openLightbox(items, startIndex = 0) {
        // WVV Protocol: Validate input
        if (!items || !Array.isArray(items) || items.length === 0) {
            console.warn('[MNR Lightbox] WVV: No valid media items provided');
            return;
        }

        createLightboxHTML();
        
        mediaItems = items;
        currentMediaIndex = Math.max(0, Math.min(startIndex, items.length - 1));
        lightboxOpen = true;

        const lightbox = document.getElementById('mnrLightbox');
        lightbox.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        showMedia(currentMediaIndex);
        updateNavigationButtons();

        console.log('[MNR Lightbox] Opened with', items.length, 'media items');
    }

    // Close lightbox
    function closeLightbox() {
        const lightbox = document.getElementById('mnrLightbox');
        if (!lightbox) return;

        // Stop any playing videos
        const video = lightbox.querySelector('video');
        if (video) {
            video.pause();
        }

        lightbox.style.display = 'none';
        document.body.style.overflow = '';
        lightboxOpen = false;

        console.log('[MNR Lightbox] Closed');
    }

    // Show specific media item
    function showMedia(index) {
        const mediaContainer = document.querySelector('.mnr-lightbox-media');
        const counterContainer = document.querySelector('.mnr-lightbox-counter');
        
        if (!mediaContainer || !mediaItems[index]) return;

        const item = mediaItems[index];
        let mediaHTML = '';

        // WVV Protocol: Validate media URL
        if (!item.url) {
            mediaHTML = `
                <div class="mnr-lightbox-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Media unavailable</p>
                </div>
            `;
        } else if (item.type === 'video' || (item.file_type && item.file_type.startsWith('video/'))) {
            mediaHTML = `
                <video controls autoplay>
                    <source src="${escapeAttr(item.url)}" type="${item.file_type || 'video/mp4'}">
                    Your browser does not support video playback.
                </video>
            `;
        } else {
            // Default to image
            mediaHTML = `
                <img src="${escapeAttr(item.url)}" alt="${escapeAttr(item.title || 'Media')}" 
                     onerror="this.parentElement.innerHTML='<div class=\\'mnr-lightbox-error\\'><i class=\\'fas fa-image\\'></i><p>Image failed to load</p></div>';">
            `;
        }

        mediaContainer.innerHTML = mediaHTML;
        
        // Update counter
        if (mediaItems.length > 1) {
            counterContainer.textContent = `${index + 1} / ${mediaItems.length}`;
            counterContainer.style.display = 'block';
        } else {
            counterContainer.style.display = 'none';
        }

        updateNavigationButtons();
    }

    // Navigate to previous media
    function prevMedia() {
        if (currentMediaIndex > 0) {
            // Pause current video if playing
            pauseCurrentVideo();
            currentMediaIndex--;
            showMedia(currentMediaIndex);
        }
    }

    // Navigate to next media
    function nextMedia() {
        if (currentMediaIndex < mediaItems.length - 1) {
            // Pause current video if playing
            pauseCurrentVideo();
            currentMediaIndex++;
            showMedia(currentMediaIndex);
        }
    }

    // Pause current video
    function pauseCurrentVideo() {
        const video = document.querySelector('.mnr-lightbox-media video');
        if (video) {
            video.pause();
        }
    }

    // Update navigation button states
    function updateNavigationButtons() {
        const prevBtn = document.querySelector('.mnr-lightbox-prev');
        const nextBtn = document.querySelector('.mnr-lightbox-next');

        if (prevBtn) {
            prevBtn.style.visibility = currentMediaIndex > 0 ? 'visible' : 'hidden';
        }
        if (nextBtn) {
            nextBtn.style.visibility = currentMediaIndex < mediaItems.length - 1 ? 'visible' : 'hidden';
        }
    }

    // Helper: Escape HTML attributes
    function escapeAttr(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    // Parse media from announcement object
    function parseAnnouncementMedia(announcement) {
        if (!announcement || !announcement.media || !Array.isArray(announcement.media)) {
            return [];
        }

        return announcement.media.map(function(media) {
            return {
                url: media.file_path,
                file_type: media.file_type,
                type: media.file_type && media.file_type.startsWith('video/') ? 'video' : 'image',
                title: announcement.title || 'Media'
            };
        });
    }

    // Make media clickable in announcement containers
    function enableLightboxForContainer(containerSelector, getMediaFn) {
        document.addEventListener('click', function(e) {
            const container = e.target.closest(containerSelector);
            if (!container) return;

            const clickedImg = e.target.closest('img');
            const clickedVideo = e.target.closest('video');

            if (clickedImg || clickedVideo) {
                e.preventDefault();
                e.stopPropagation();

                const mediaItems = getMediaFn(container);
                if (mediaItems && mediaItems.length > 0) {
                    // Find which media was clicked
                    let startIndex = 0;
                    const clickedSrc = clickedImg ? clickedImg.src : (clickedVideo ? clickedVideo.querySelector('source')?.src : null);
                    
                    if (clickedSrc) {
                        const foundIndex = mediaItems.findIndex(m => m.url === clickedSrc || clickedSrc.includes(m.url));
                        if (foundIndex !== -1) startIndex = foundIndex;
                    }

                    openLightbox(mediaItems, startIndex);
                }
            }
        });
    }

    // Export to global scope
    window.MNRLightbox = {
        open: openLightbox,
        close: closeLightbox,
        parseAnnouncementMedia: parseAnnouncementMedia,
        enableLightboxForContainer: enableLightboxForContainer,
        init: createLightboxHTML
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createLightboxHTML);
    } else {
        createLightboxHTML();
    }

    console.log('[MNR Lightbox] Component loaded - DC Protocol v1.0.0');
})();
