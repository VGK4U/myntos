/**
 * Universal Engagement System - Reusable Component
 * DC Protocol Compliant with Company-Wise Data Segregation
 * 
 * Supports: Ratings, Comments, Shares for any entity type
 * Entity Types: announcement, property, product, article, service, event
 * 
 * Usage:
 *   const engagement = new UniversalEngagement({
 *       entityType: 'property',
 *       entityId: 123,
 *       companyId: 1,
 *       containerSelector: '#engagement-container',
 *       apiBaseUrl: 'https://api.example.com/api/v1'
 *   });
 *   engagement.init();
 * 
 * Created: December 08, 2025
 */

class UniversalEngagement {
    constructor(options) {
        this.entityType = options.entityType || 'property';
        this.entityId = options.entityId;
        this.companyId = options.companyId || 1;
        this.containerSelector = options.containerSelector || '#engagement-container';
        this.apiBaseUrl = options.apiBaseUrl || '/api/v1';
        
        this.currentPage = 1;
        this.commentsPage = 1;
        this.ratings = [];
        this.comments = [];
        this.stats = null;
        
        this.userId = localStorage.getItem('user_id') || null;
        this.userName = localStorage.getItem('user_name') || '';
        this.userEmail = localStorage.getItem('user_email') || '';
        this.userType = localStorage.getItem('user_type') || 'public';
    }

    async init() {
        await this.loadStats();
        await this.loadRatings();
        await this.loadComments();
        this.render();
        this.bindEvents();
    }

    async loadStats() {
        try {
            const response = await fetch(
                `${this.apiBaseUrl}/engagement/stats/${this.entityType}/${this.entityId}?company_id=${this.companyId}`
            );
            const data = await response.json();
            if (data.success) {
                this.stats = data.stats;
            }
        } catch (error) {
            console.error('Error loading engagement stats:', error);
        }
    }

    async loadRatings() {
        try {
            const response = await fetch(
                `${this.apiBaseUrl}/engagement/public/${this.entityType}/${this.entityId}/ratings?company_id=${this.companyId}&page=${this.currentPage}&per_page=10`
            );
            const data = await response.json();
            if (data.success) {
                this.ratings = data.ratings;
                this.avgRating = data.average_rating;
                this.totalRatings = data.total_ratings;
                this.ratingBreakdown = data.rating_breakdown;
            }
        } catch (error) {
            console.error('Error loading ratings:', error);
        }
    }

    async loadComments() {
        try {
            const response = await fetch(
                `${this.apiBaseUrl}/engagement/public/${this.entityType}/${this.entityId}/comments?company_id=${this.companyId}&page=${this.commentsPage}&per_page=20`
            );
            const data = await response.json();
            if (data.success) {
                this.comments = data.comments;
                this.totalComments = data.total_comments;
                this.commentsPagination = data.pagination;
            }
        } catch (error) {
            console.error('Error loading comments:', error);
        }
    }

    async submitRating(ratingValue) {
        const name = document.getElementById('ue-rater-name')?.value?.trim() || this.userName;
        const email = document.getElementById('ue-rater-email')?.value?.trim() || this.userEmail;
        
        if (!name) {
            this.showToast('Please enter your name', 'warning');
            return;
        }

        try {
            const response = await fetch(
                `${this.apiBaseUrl}/engagement/public/${this.entityType}/${this.entityId}/ratings?company_id=${this.companyId}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rating: ratingValue,
                        rater_name: name,
                        rater_email: email,
                        rater_type: this.userType,
                        rater_id: this.userId
                    })
                }
            );
            
            const data = await response.json();
            if (data.success) {
                this.showToast('Thank you for your rating!', 'success');
                await this.loadRatings();
                await this.loadStats();
                this.renderRatings();
            } else {
                this.showToast(data.detail || 'Failed to submit rating', 'error');
            }
        } catch (error) {
            console.error('Error submitting rating:', error);
            this.showToast('Error submitting rating', 'error');
        }
    }

    async submitComment(commentText, parentId = null) {
        const name = document.getElementById('ue-commenter-name')?.value?.trim() || this.userName;
        const email = document.getElementById('ue-commenter-email')?.value?.trim() || this.userEmail;
        
        if (!name) {
            this.showToast('Please enter your name', 'warning');
            return;
        }
        
        if (!commentText.trim()) {
            this.showToast('Please enter a comment', 'warning');
            return;
        }

        try {
            const response = await fetch(
                `${this.apiBaseUrl}/engagement/public/${this.entityType}/${this.entityId}/comments?company_id=${this.companyId}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        comment: commentText,
                        parent_id: parentId,
                        commenter_name: name,
                        commenter_email: email,
                        commenter_type: this.userType,
                        commenter_id: this.userId
                    })
                }
            );
            
            const data = await response.json();
            if (data.success) {
                this.showToast('Comment posted successfully!', 'success');
                document.getElementById('ue-comment-text').value = '';
                await this.loadComments();
                await this.loadStats();
                this.renderComments();
            } else {
                this.showToast(data.detail || 'Failed to post comment', 'error');
            }
        } catch (error) {
            console.error('Error posting comment:', error);
            this.showToast('Error posting comment', 'error');
        }
    }

    async trackShare(platform) {
        try {
            await fetch(
                `${this.apiBaseUrl}/engagement/public/${this.entityType}/${this.entityId}/share?company_id=${this.companyId}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        platform: platform,
                        sharer_type: this.userType,
                        sharer_id: this.userId
                    })
                }
            );
            await this.loadStats();
        } catch (error) {
            console.error('Error tracking share:', error);
        }
    }

    shareOn(platform) {
        const url = encodeURIComponent(window.location.href);
        const title = encodeURIComponent(document.title);
        let shareUrl = '';

        switch (platform) {
            case 'facebook':
                shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
                break;
            case 'twitter':
                shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${title}`;
                break;
            case 'whatsapp':
                shareUrl = `https://wa.me/?text=${title}%20${url}`;
                break;
            case 'linkedin':
                shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${url}`;
                break;
            case 'telegram':
                shareUrl = `https://t.me/share/url?url=${url}&text=${title}`;
                break;
            case 'email':
                shareUrl = `mailto:?subject=${title}&body=${url}`;
                break;
            case 'copy_link':
                navigator.clipboard.writeText(window.location.href).then(() => {
                    this.showToast('Link copied to clipboard!', 'success');
                });
                this.trackShare('copy_link');
                return;
        }

        if (shareUrl) {
            window.open(shareUrl, '_blank', 'width=600,height=400');
            this.trackShare(platform);
        }
    }

    render() {
        const container = document.querySelector(this.containerSelector);
        if (!container) return;

        container.innerHTML = `
            <div class="ue-engagement-system">
                <!-- Stats Summary -->
                <div class="ue-stats-bar mb-4">
                    <div class="d-flex align-items-center gap-4 flex-wrap">
                        <div class="ue-stat-item">
                            <i class="fas fa-star text-warning"></i>
                            <span class="ue-stat-value">${this.avgRating || 0}</span>
                            <span class="ue-stat-label">(${this.totalRatings || 0} ratings)</span>
                        </div>
                        <div class="ue-stat-item">
                            <i class="fas fa-comments text-primary"></i>
                            <span class="ue-stat-value">${this.totalComments || 0}</span>
                            <span class="ue-stat-label">comments</span>
                        </div>
                        <div class="ue-stat-item">
                            <i class="fas fa-share-alt text-success"></i>
                            <span class="ue-stat-value">${this.stats?.total_shares || 0}</span>
                            <span class="ue-stat-label">shares</span>
                        </div>
                    </div>
                </div>

                <!-- Share Buttons -->
                <div class="ue-share-section mb-4">
                    <h6 class="ue-section-title"><i class="fas fa-share-alt me-2"></i>Share</h6>
                    <div class="ue-share-buttons d-flex gap-2 flex-wrap">
                        <button class="btn btn-sm ue-share-btn ue-share-whatsapp" data-platform="whatsapp" title="Share on WhatsApp">
                            <i class="fab fa-whatsapp"></i>
                        </button>
                        <button class="btn btn-sm ue-share-btn ue-share-facebook" data-platform="facebook" title="Share on Facebook">
                            <i class="fab fa-facebook-f"></i>
                        </button>
                        <button class="btn btn-sm ue-share-btn ue-share-twitter" data-platform="twitter" title="Share on Twitter">
                            <i class="fab fa-twitter"></i>
                        </button>
                        <button class="btn btn-sm ue-share-btn ue-share-linkedin" data-platform="linkedin" title="Share on LinkedIn">
                            <i class="fab fa-linkedin-in"></i>
                        </button>
                        <button class="btn btn-sm ue-share-btn ue-share-telegram" data-platform="telegram" title="Share on Telegram">
                            <i class="fab fa-telegram-plane"></i>
                        </button>
                        <button class="btn btn-sm ue-share-btn ue-share-email" data-platform="email" title="Share via Email">
                            <i class="fas fa-envelope"></i>
                        </button>
                        <button class="btn btn-sm ue-share-btn ue-share-copy" data-platform="copy_link" title="Copy Link">
                            <i class="fas fa-link"></i>
                        </button>
                    </div>
                </div>

                <!-- Ratings Section -->
                <div class="ue-ratings-section mb-4" id="ue-ratings-section">
                    ${this.renderRatingsHTML()}
                </div>

                <!-- Comments Section -->
                <div class="ue-comments-section" id="ue-comments-section">
                    ${this.renderCommentsHTML()}
                </div>
            </div>

            <style>
                .ue-engagement-system {
                    background: var(--card-bg, #1e1e1e);
                    border-radius: 12px;
                    padding: 20px;
                    margin-top: 20px;
                }
                .ue-stats-bar {
                    background: rgba(255,255,255,0.05);
                    padding: 15px 20px;
                    border-radius: 8px;
                }
                .ue-stat-item {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .ue-stat-value {
                    font-weight: 600;
                    font-size: 1.1rem;
                }
                .ue-stat-label {
                    color: #999;
                    font-size: 0.85rem;
                }
                .ue-section-title {
                    color: #ccc;
                    font-size: 1rem;
                    margin-bottom: 12px;
                    border-bottom: 1px solid rgba(255,255,255,0.1);
                    padding-bottom: 8px;
                }
                .ue-share-btn {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: transform 0.2s;
                }
                .ue-share-btn:hover {
                    transform: scale(1.1);
                }
                .ue-share-whatsapp { background: #25D366; color: white; }
                .ue-share-facebook { background: #1877F2; color: white; }
                .ue-share-twitter { background: #1DA1F2; color: white; }
                .ue-share-linkedin { background: #0A66C2; color: white; }
                .ue-share-telegram { background: #0088cc; color: white; }
                .ue-share-email { background: #6c757d; color: white; }
                .ue-share-copy { background: #495057; color: white; }
                .ue-rating-stars {
                    display: flex;
                    gap: 4px;
                    cursor: pointer;
                }
                .ue-rating-stars .star {
                    font-size: 1.5rem;
                    color: #444;
                    transition: color 0.2s;
                }
                .ue-rating-stars .star.active,
                .ue-rating-stars .star.hover {
                    color: #ffc107;
                }
                .ue-rating-breakdown {
                    margin-top: 15px;
                }
                .ue-rating-bar-row {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 5px;
                }
                .ue-rating-bar-label {
                    width: 20px;
                    text-align: right;
                    color: #999;
                    font-size: 0.85rem;
                }
                .ue-rating-bar {
                    flex: 1;
                    height: 8px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 4px;
                    overflow: hidden;
                }
                .ue-rating-bar-fill {
                    height: 100%;
                    background: #ffc107;
                    border-radius: 4px;
                    transition: width 0.3s;
                }
                .ue-rating-bar-count {
                    width: 30px;
                    color: #999;
                    font-size: 0.85rem;
                }
                .ue-comment-form {
                    background: rgba(255,255,255,0.03);
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }
                .ue-comment-input {
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.1);
                    color: #fff;
                    border-radius: 8px;
                }
                .ue-comment-input:focus {
                    background: rgba(255,255,255,0.08);
                    border-color: var(--primary-color, #0d6efd);
                    color: #fff;
                    box-shadow: none;
                }
                .ue-comment-item {
                    padding: 15px;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                }
                .ue-comment-item:last-child {
                    border-bottom: none;
                }
                .ue-comment-header {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 8px;
                }
                .ue-comment-author {
                    font-weight: 500;
                    color: #fff;
                }
                .ue-comment-date {
                    color: #777;
                    font-size: 0.8rem;
                }
                .ue-comment-text {
                    color: #ccc;
                    line-height: 1.5;
                }
                .ue-comment-replies {
                    margin-left: 30px;
                    margin-top: 10px;
                    border-left: 2px solid rgba(255,255,255,0.1);
                    padding-left: 15px;
                }
                .ue-reply-btn {
                    font-size: 0.8rem;
                    color: #0d6efd;
                    cursor: pointer;
                    margin-top: 5px;
                }
                .ue-load-more {
                    text-align: center;
                    margin-top: 15px;
                }
            </style>
        `;
    }

    renderRatingsHTML() {
        const breakdown = this.ratingBreakdown || {'1': 0, '2': 0, '3': 0, '4': 0, '5': 0};
        const total = this.totalRatings || 0;
        
        return `
            <h6 class="ue-section-title"><i class="fas fa-star me-2"></i>Ratings & Reviews</h6>
            
            <div class="row g-4">
                <div class="col-md-4">
                    <div class="text-center">
                        <div class="display-4 fw-bold text-warning">${this.avgRating || 0}</div>
                        <div class="ue-rating-stars justify-content-center mb-2" id="ue-avg-stars">
                            ${this.renderStars(this.avgRating || 0)}
                        </div>
                        <div class="text-muted">${total} ratings</div>
                    </div>
                </div>
                <div class="col-md-8">
                    <div class="ue-rating-breakdown">
                        ${[5, 4, 3, 2, 1].map(star => {
                            const count = breakdown[String(star)] || 0;
                            const percent = total > 0 ? (count / total) * 100 : 0;
                            return `
                                <div class="ue-rating-bar-row">
                                    <div class="ue-rating-bar-label">${star}</div>
                                    <i class="fas fa-star text-warning" style="font-size: 0.8rem;"></i>
                                    <div class="ue-rating-bar">
                                        <div class="ue-rating-bar-fill" style="width: ${percent}%"></div>
                                    </div>
                                    <div class="ue-rating-bar-count">${count}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            </div>

            <div class="ue-rate-form mt-4 p-3 rounded" style="background: rgba(255,255,255,0.03);">
                <h6 class="mb-3">Rate this ${this.entityType}</h6>
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <input type="text" class="form-control ue-comment-input" id="ue-rater-name" 
                               placeholder="Your Name *" value="${this.userName}">
                    </div>
                    <div class="col-md-6">
                        <input type="email" class="form-control ue-comment-input" id="ue-rater-email" 
                               placeholder="Your Email (optional)" value="${this.userEmail}">
                    </div>
                </div>
                <div class="d-flex align-items-center gap-3">
                    <span class="text-muted">Your rating:</span>
                    <div class="ue-rating-stars" id="ue-user-rating-stars">
                        ${[1, 2, 3, 4, 5].map(i => `<i class="fas fa-star star" data-rating="${i}"></i>`).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    renderStars(rating) {
        const full = Math.floor(rating);
        const half = rating - full >= 0.5;
        const empty = 5 - full - (half ? 1 : 0);
        let html = '';
        
        for (let i = 0; i < full; i++) {
            html += '<i class="fas fa-star text-warning"></i>';
        }
        if (half) {
            html += '<i class="fas fa-star-half-alt text-warning"></i>';
        }
        for (let i = 0; i < empty; i++) {
            html += '<i class="far fa-star text-warning"></i>';
        }
        return html;
    }

    renderRatings() {
        const container = document.getElementById('ue-ratings-section');
        if (container) {
            container.innerHTML = this.renderRatingsHTML();
            this.bindRatingEvents();
        }
    }

    renderCommentsHTML() {
        return `
            <h6 class="ue-section-title"><i class="fas fa-comments me-2"></i>Comments (${this.totalComments || 0})</h6>
            
            <div class="ue-comment-form">
                <div class="row g-3 mb-3">
                    <div class="col-md-6">
                        <input type="text" class="form-control ue-comment-input" id="ue-commenter-name" 
                               placeholder="Your Name *" value="${this.userName}">
                    </div>
                    <div class="col-md-6">
                        <input type="email" class="form-control ue-comment-input" id="ue-commenter-email" 
                               placeholder="Your Email (optional)" value="${this.userEmail}">
                    </div>
                </div>
                <textarea class="form-control ue-comment-input mb-3" id="ue-comment-text" 
                          rows="3" placeholder="Write a comment..."></textarea>
                <button class="btn btn-primary" id="ue-submit-comment">
                    <i class="fas fa-paper-plane me-2"></i>Post Comment
                </button>
            </div>
            
            <div class="ue-comments-list" id="ue-comments-list">
                ${this.comments.length > 0 ? this.comments.map(c => this.renderCommentItem(c)).join('') : 
                  '<div class="text-center text-muted py-4">No comments yet. Be the first to comment!</div>'}
            </div>
            
            ${this.commentsPagination && this.commentsPagination.pages > 1 ? `
                <div class="ue-load-more">
                    <button class="btn btn-outline-light btn-sm" id="ue-load-more-comments">
                        Load More Comments
                    </button>
                </div>
            ` : ''}
        `;
    }

    renderCommentItem(comment, isReply = false) {
        const date = new Date(comment.created_at).toLocaleDateString('en-IN', {
            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
        
        return `
            <div class="ue-comment-item ${isReply ? 'ue-reply-item' : ''}">
                <div class="ue-comment-header">
                    <span class="ue-comment-author">
                        <i class="fas fa-user-circle me-2"></i>${comment.commenter_name}
                        ${comment.is_verified ? '<i class="fas fa-check-circle text-success ms-1" title="Verified"></i>' : ''}
                    </span>
                    <span class="ue-comment-date">${date}</span>
                </div>
                <div class="ue-comment-text">${this.escapeHtml(comment.comment)}</div>
                ${!isReply ? `<div class="ue-reply-btn" data-comment-id="${comment.id}"><i class="fas fa-reply me-1"></i>Reply</div>` : ''}
                ${comment.replies && comment.replies.length > 0 ? `
                    <div class="ue-comment-replies">
                        ${comment.replies.map(r => this.renderCommentItem(r, true)).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }

    renderComments() {
        const container = document.getElementById('ue-comments-section');
        if (container) {
            container.innerHTML = this.renderCommentsHTML();
            this.bindCommentEvents();
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    bindEvents() {
        this.bindShareEvents();
        this.bindRatingEvents();
        this.bindCommentEvents();
    }

    bindShareEvents() {
        document.querySelectorAll('.ue-share-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const platform = btn.dataset.platform;
                this.shareOn(platform);
            });
        });
    }

    bindRatingEvents() {
        const starsContainer = document.getElementById('ue-user-rating-stars');
        if (!starsContainer) return;

        const stars = starsContainer.querySelectorAll('.star');
        
        stars.forEach(star => {
            star.addEventListener('mouseenter', () => {
                const rating = parseInt(star.dataset.rating);
                stars.forEach((s, idx) => {
                    s.classList.toggle('hover', idx < rating);
                });
            });

            star.addEventListener('mouseleave', () => {
                stars.forEach(s => s.classList.remove('hover'));
            });

            star.addEventListener('click', () => {
                const rating = parseInt(star.dataset.rating);
                this.submitRating(rating);
            });
        });
    }

    bindCommentEvents() {
        const submitBtn = document.getElementById('ue-submit-comment');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => {
                const text = document.getElementById('ue-comment-text')?.value;
                this.submitComment(text);
            });
        }

        document.querySelectorAll('.ue-reply-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const commentId = btn.dataset.commentId;
                const reply = prompt('Enter your reply:');
                if (reply && reply.trim()) {
                    this.submitComment(reply, parseInt(commentId));
                }
            });
        });

        const loadMoreBtn = document.getElementById('ue-load-more-comments');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', async () => {
                this.commentsPage++;
                await this.loadComments();
                this.renderComments();
            });
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 250px; animation: slideIn 0.3s ease;';
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = UniversalEngagement;
}
