/**
 * MNR Profile Edit Page
 * DC Protocol: DC_MOBILE_MNR_PROFILE_EDIT_001
 * Edit personal profile details
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

export class MNRProfileEdit {
  private container: HTMLElement;
  private profile: any = null;
  private loading: boolean = true;
  private saving: boolean = false;
  private uploadingPhoto: string | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadProfile();
  }

  private async loadProfile(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/users/profile');
      if (response.success && response.data) {
        this.profile = response.data;
      }
    } catch (error) {
      console.error('[MNRProfileEdit] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .profile-edit-page .form-group { margin-bottom: 16px; }
        .profile-edit-page .form-group label {
          display: block; color: #8892b0; font-size: 13px;
          margin-bottom: 6px; font-weight: 500;
        }
        .profile-edit-page .form-input {
          width: 100%; padding: 12px 16px; background: #1a2744;
          border: 1px solid #2d3b4f; border-radius: 8px;
          color: #e6f1ff; font-size: 15px;
        }
        .profile-edit-page .form-input:focus {
          outline: none; border-color: #64ffda;
        }
        .profile-edit-page .form-row {
          display: flex; gap: 12px;
        }
        .profile-edit-page .form-row .form-group { flex: 1; }
        .profile-edit-page .section-title {
          color: #64ffda; font-size: 16px; font-weight: 600;
          margin: 20px 0 12px; padding-bottom: 8px;
          border-bottom: 1px solid #2d3b4f;
        }
        .profile-edit-page .form-actions {
          display: flex; gap: 12px; margin-top: 24px;
        }
        .profile-edit-page .form-actions .btn { flex: 1; padding: 14px; border-radius: 8px; font-weight: 600; }
        .profile-edit-page .btn-secondary { background: #2d3b4f; color: #e6f1ff; border: none; }
        .profile-edit-page .btn-primary { background: #64ffda; color: #0a192f; border: none; }
        .profile-edit-page .btn:disabled { opacity: 0.6; }
        .profile-edit-page select.form-input { appearance: none; }
        .profile-edit-page .photo-upload-section {
          display: flex; gap: 16px; margin-bottom: 20px;
        }
        .profile-edit-page .photo-box {
          flex: 1; text-align: center; padding: 16px;
          background: #1a2744; border-radius: 12px; border: 1px dashed #2d3b4f;
        }
        .profile-edit-page .photo-box.has-photo { border: 2px solid #64ffda; }
        .profile-edit-page .photo-preview {
          width: 80px; height: 80px; border-radius: 50%;
          margin: 0 auto 10px; background: #2d3b4f;
          display: flex; align-items: center; justify-content: center;
          overflow: hidden; font-size: 24px;
        }
        .profile-edit-page .photo-preview img {
          width: 100%; height: 100%; object-fit: cover;
        }
        .profile-edit-page .photo-label { color: #8892b0; font-size: 12px; margin-bottom: 8px; }
        .profile-edit-page .photo-btn {
          padding: 8px 16px; font-size: 12px; border-radius: 6px;
          border: none; cursor: pointer;
        }
        .profile-edit-page .photo-btn.primary { background: #64ffda; color: #0a192f; }
        .profile-edit-page .photo-btn.secondary { background: #2d3b4f; color: #e6f1ff; }
      </style>
      <div class="page-container profile-edit-page">
        ${PageHeader.render({ title: '✏️ Edit Profile', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '✏️ Edit Profile', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const p = this.profile || {};

    const isUploadingProfile = this.uploadingPhoto === 'profile_photo';
    const isUploadingPassport = this.uploadingPhoto === 'passport_photo';

    content.innerHTML = `
      <div class="card">
        <h3 class="section-title">Photos</h3>
        <div class="photo-upload-section">
          <div class="photo-box ${p.profile_photo_url ? 'has-photo' : ''}">
            <div class="photo-preview">
              ${p.profile_photo_url ? `<img src="${p.profile_photo_url}" alt="Profile">` : '📷'}
            </div>
            <div class="photo-label">Profile Photo</div>
            <button class="photo-btn ${p.profile_photo_url ? 'secondary' : 'primary'}" 
              id="uploadProfileBtn" ${isUploadingProfile ? 'disabled' : ''}>
              ${isUploadingProfile ? 'Uploading...' : p.profile_photo_url ? 'Change' : 'Upload'}
            </button>
          </div>
          <div class="photo-box ${p.passport_photo_url ? 'has-photo' : ''}">
            <div class="photo-preview">
              ${p.passport_photo_url ? `<img src="${p.passport_photo_url}" alt="Passport">` : '🖼️'}
            </div>
            <div class="photo-label">Passport Photo</div>
            <button class="photo-btn ${p.passport_photo_url ? 'secondary' : 'primary'}" 
              id="uploadPassportBtn" ${isUploadingPassport ? 'disabled' : ''}>
              ${isUploadingPassport ? 'Uploading...' : p.passport_photo_url ? 'Change' : 'Upload'}
            </button>
          </div>
        </div>
        <input type="file" id="photoInput" accept="image/*" style="display: none;">
        
        <h3 class="section-title">Personal Information</h3>
        
        <div class="form-group">
          <label>Full Name</label>
          <input type="text" id="fullName" class="form-input" 
            value="${p.name || ''}" placeholder="Contact admin to change" 
            readonly disabled style="opacity: 0.6; cursor: not-allowed;">
          <small style="color: #6b7280; font-size: 11px;">Name cannot be changed. Contact admin for updates.</small>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="email" class="form-input" 
              value="${p.email || ''}" placeholder="your@email.com">
          </div>
          <div class="form-group">
            <label>Mobile</label>
            <input type="tel" id="mobile" class="form-input" 
              value="${p.mobile || ''}" placeholder="Contact admin to change"
              readonly disabled style="opacity: 0.6; cursor: not-allowed;">
            <small style="color: #6b7280; font-size: 11px;">Mobile cannot be changed.</small>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>Gender</label>
            <select id="gender" class="form-input">
              <option value="">Select</option>
              <option value="Male" ${p.gender === 'Male' ? 'selected' : ''}>Male</option>
              <option value="Female" ${p.gender === 'Female' ? 'selected' : ''}>Female</option>
              <option value="Other" ${p.gender === 'Other' ? 'selected' : ''}>Other</option>
            </select>
          </div>
          <div class="form-group">
            <label>Actual DOB</label>
            <input type="date" id="actualDob" class="form-input" 
              value="${p.actual_dob ? p.actual_dob.split('T')[0] : ''}">
          </div>
        </div>
        
        <h3 class="section-title">Address</h3>
        
        <div class="form-group">
          <label>Street Address</label>
          <input type="text" id="address" class="form-input" 
            value="${p.address || ''}" placeholder="Street address">
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>City</label>
            <input type="text" id="city" class="form-input" 
              value="${p.city || ''}" placeholder="City">
          </div>
          <div class="form-group">
            <label>State</label>
            <input type="text" id="state" class="form-input" 
              value="${p.state || ''}" placeholder="State">
          </div>
        </div>
        
        <div class="form-group">
          <label>Pincode</label>
          <input type="text" id="pincode" class="form-input" 
            value="${p.pincode || ''}" placeholder="6-digit pincode" maxlength="6">
        </div>
        
        <h3 class="section-title">KYC Details</h3>
        
        <div class="form-row">
          <div class="form-group">
            <label>Aadhaar Number</label>
            <input type="text" id="aadhaarNumber" class="form-input" 
              value="${p.aadhaar_number || ''}" placeholder="12-digit Aadhaar" maxlength="12">
          </div>
          <div class="form-group">
            <label>PAN Number</label>
            <input type="text" id="panNumber" class="form-input" 
              value="${p.pan_number || ''}" placeholder="e.g., ABCDE1234F" maxlength="10">
          </div>
        </div>
        
        <div class="form-actions">
          <button class="btn btn-secondary" id="cancelBtn" ${this.saving ? 'disabled' : ''}>
            Cancel
          </button>
          <button class="btn btn-primary" id="saveBtn" ${this.saving ? 'disabled' : ''}>
            ${this.saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.getElementById('cancelBtn')?.addEventListener('click', () => {
      routerService.navigate('mnr-profile');
    });

    document.getElementById('saveBtn')?.addEventListener('click', () => {
      this.saveProfile();
    });

    const photoInput = document.getElementById('photoInput') as HTMLInputElement;
    
    document.getElementById('uploadProfileBtn')?.addEventListener('click', () => {
      this.uploadingPhoto = 'profile_photo';
      photoInput?.click();
    });

    document.getElementById('uploadPassportBtn')?.addEventListener('click', () => {
      this.uploadingPhoto = 'passport_photo';
      photoInput?.click();
    });

    photoInput?.addEventListener('change', async () => {
      const file = photoInput.files?.[0];
      if (file && this.uploadingPhoto) {
        await this.uploadPhoto(this.uploadingPhoto, file);
      }
      photoInput.value = '';
    });
  }

  private async uploadPhoto(docType: string, file: File): Promise<void> {
    this.updateContent();

    try {
      const formData = new FormData();
      formData.append('file', file);  // DC Protocol Feb 2026: Fix field name
      formData.append('document_type', docType);

      // DC Protocol Feb 2026: Fix endpoint path - use /profile/ not /users/
      const response = await apiService.uploadFile('/profile/upload-kyc-document', formData);
      
      if (response.success) {
        alert('Photo uploaded successfully!');
        await this.loadProfile();
      } else {
        alert(response.error || 'Failed to upload photo');
      }
    } catch (error) {
      console.error('[MNRProfileEdit] Photo upload failed:', error);
      alert('Failed to upload photo. Please try again.');
    } finally {
      this.uploadingPhoto = null;
      this.updateContent();
    }
  }

  private async saveProfile(): Promise<void> {
    const getValue = (id: string) => (document.getElementById(id) as HTMLInputElement)?.value?.trim() || null;

    const data = {
      name: getValue('fullName'),
      email: getValue('email'),
      mobile: getValue('mobile'),
      gender: getValue('gender'),
      actual_dob: getValue('actualDob'),
      address: getValue('address'),
      city: getValue('city'),
      state: getValue('state'),
      pincode: getValue('pincode'),
      aadhaar_number: getValue('aadhaarNumber'),
      pan_number: getValue('panNumber')
    };

    if (!data.name) {
      alert('Please enter your full name');
      return;
    }

    this.saving = true;
    this.updateContent();

    try {
      const response = await apiService.put<any>('/users/profile', data);

      if (response.success) {
        alert('Profile updated successfully!');
        routerService.navigate('mnr-profile');
      } else {
        alert(response.error || 'Failed to update profile');
      }
    } catch (error) {
      console.error('[MNRProfileEdit] Save failed:', error);
      alert('Failed to update profile. Please try again.');
    } finally {
      this.saving = false;
    }
  }
}
