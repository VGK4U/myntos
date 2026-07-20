/**
 * Staff Vendors Page
 * DC Protocol: DC_MOBILE_STAFF_VENDORS_001
 * Accounts → Vendor Master — full web parity: list, view, create, edit
 * Mirrors frontend/staff_accounts_vendors.html
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';

interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code: string;
  vendor_type: string;
  gst_type: string;
  gstin: string | null;
  pan: string | null;
  phone: string | null;
  email: string | null;
  contact_person: string | null;
  address: string | null;
  city: string | null;
  state: string | null;
  pincode: string | null;
  bank_name: string | null;
  account_no: string | null;
  ifsc_code: string | null;
  account_holder: string | null;
  is_active: boolean;
  applicable_companies: string[];
  vendor_logo_url: string | null;
  created_at?: string;
}

interface VendorFormData {
  vendor_name: string;
  vendor_code: string;
  vendor_type: string;
  gst_type: string;
  gstin: string;
  pan: string;
  phone: string;
  email: string;
  contact_person: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  bank_name: string;
  account_no: string;
  ifsc_code: string;
  account_holder: string;
  applicable_companies: string[];
  is_active: boolean;
}

export class StaffVendorsPage {
  private container: HTMLElement;
  private vendors: Vendor[] = [];
  private filteredVendors: Vendor[] = [];
  private searchQuery: string = '';
  private typeFilter: string = '';
  private editingVendor: Vendor | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async render(): Promise<void> {
    const token = authService.getToken();
    if (!token) return;

    this.container.innerHTML = `
      <div style="min-height:100vh;background:#0f172a;color:#f8fafc;font-family:'Inter',sans-serif;">
        ${PageHeader.render({ title: 'Vendors', showBack: true })}

        <!-- Search + Filter Bar -->
        <div style="padding:12px 16px;background:#1e293b;border-bottom:1px solid #334155;display:flex;gap:8px;">
          <div style="flex:1;position:relative;">
            <input id="vendorSearch" type="text" placeholder="Search vendors..."
              style="width:100%;padding:8px 12px 8px 36px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;"
              oninput="window._vendorsPage.onSearch(this.value)">
            <span style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:#94a3b8;font-size:14px;">🔍</span>
          </div>
          <select id="vendorTypeFilter"
            style="padding:8px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:13px;"
            onchange="window._vendorsPage.onTypeFilter(this.value)">
            <option value="">All Types</option>
            <option value="PRODUCT">Product</option>
            <option value="SERVICE">Service</option>
            <option value="BOTH">Both</option>
            <option value="SOLAR">Solar</option>
          </select>
        </div>

        <!-- Action bar -->
        <div style="padding:10px 16px;display:flex;justify-content:flex-end;">
          <button onclick="window._vendorsPage.openCreateModal()"
            style="padding:8px 16px;background:#3b82f6;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">
            + New Vendor
          </button>
        </div>

        <!-- Vendor List -->
        <div id="vendorList" style="padding:0 16px 80px;">
          <div style="text-align:center;padding:40px;color:#64748b;">Loading vendors…</div>
        </div>

        <!-- Detail / Edit Modal -->
        <div id="vendorModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:1000;overflow-y:auto;">
          <div style="background:#1e293b;margin:20px 16px;border-radius:12px;padding:20px;max-width:500px;margin-left:auto;margin-right:auto;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
              <h3 id="vendorModalTitle" style="margin:0;font-size:16px;color:#f8fafc;">Vendor Details</h3>
              <button onclick="window._vendorsPage.closeModal()"
                style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;">✕</button>
            </div>
            <div id="vendorModalBody"></div>
          </div>
        </div>

        <!-- Create Modal -->
        <div id="createModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:1000;overflow-y:auto;">
          <div style="background:#1e293b;margin:20px 16px;border-radius:12px;padding:20px;max-width:500px;margin-left:auto;margin-right:auto;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
              <h3 style="margin:0;font-size:16px;color:#f8fafc;">New Vendor</h3>
              <button onclick="window._vendorsPage.closeCreateModal()"
                style="background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;">✕</button>
            </div>
            <div id="createModalBody">${this.renderVendorForm(null)}</div>
            <button onclick="window._vendorsPage.submitCreate()"
              style="width:100%;margin-top:16px;padding:12px;background:#3b82f6;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">
              Create Vendor
            </button>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachBackHandler();
    (window as any)._vendorsPage = this;
    await this.loadVendors();
  }

  private renderVendorForm(v: Vendor | null): string {
    const val = (x: any) => x ?? '';
    const gstType = v?.gst_type ?? 'CGST_SGST';
    return `
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Vendor Name *</label>
          <input id="vf_name" value="${val(v?.vendor_name)}"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Vendor Code *</label>
          <input id="vf_code" value="${val(v?.vendor_code)}" ${v ? 'readonly style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#94a3b8;font-size:14px;box-sizing:border-box;"' : 'style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;"'}>
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Type</label>
          <select id="vf_type" style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
            ${['PRODUCT','SERVICE','BOTH','SOLAR'].map(t => `<option value="${t}" ${val(v?.vendor_type || 'BOTH') === t ? 'selected' : ''}>${t}</option>`).join('')}
          </select>
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">GST Treatment</label>
          <div style="display:flex;gap:8px;">
            <label style="flex:1;padding:8px;border:2px solid ${gstType === 'CGST_SGST' ? '#3b82f6' : '#334155'};border-radius:8px;display:flex;align-items:center;gap:6px;cursor:pointer;">
              <input type="radio" name="vf_gst_type" value="CGST_SGST" ${gstType === 'CGST_SGST' ? 'checked' : ''}> CGST + SGST
            </label>
            <label style="flex:1;padding:8px;border:2px solid ${gstType === 'IGST' ? '#3b82f6' : '#334155'};border-radius:8px;display:flex;align-items:center;gap:6px;cursor:pointer;">
              <input type="radio" name="vf_gst_type" value="IGST" ${gstType === 'IGST' ? 'checked' : ''}> IGST
            </label>
          </div>
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">GSTIN</label>
          <input id="vf_gstin" value="${val(v?.gstin)}" placeholder="15-char GST number"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">PAN</label>
          <input id="vf_pan" value="${val(v?.pan)}"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Contact Person</label>
          <input id="vf_contact" value="${val(v?.contact_person)}"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Phone</label>
          <input id="vf_phone" value="${val(v?.phone)}" type="tel"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Email</label>
          <input id="vf_email" value="${val(v?.email)}" type="email"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Address</label>
          <input id="vf_address" value="${val(v?.address)}"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div style="display:flex;gap:8px;">
          <div style="flex:1;">
            <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">City</label>
            <input id="vf_city" value="${val(v?.city)}"
              style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
          </div>
          <div style="flex:1;">
            <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">State</label>
            <input id="vf_state" value="${val(v?.state)}"
              style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
          </div>
        </div>
        <div>
          <label style="font-size:12px;color:#94a3b8;display:block;margin-bottom:4px;">Pincode</label>
          <input id="vf_pincode" value="${val(v?.pincode)}"
            style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
        </div>
        <div style="padding-top:8px;border-top:1px solid #334155;">
          <p style="font-size:12px;color:#94a3b8;margin:0 0 8px;">Bank Details</p>
          <div style="display:flex;flex-direction:column;gap:8px;">
            <input id="vf_bank" value="${val(v?.bank_name)}" placeholder="Bank Name"
              style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
            <input id="vf_acc" value="${val(v?.account_no)}" placeholder="Account Number"
              style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
            <input id="vf_ifsc" value="${val(v?.ifsc_code)}" placeholder="IFSC Code"
              style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
            <input id="vf_holder" value="${val(v?.account_holder)}" placeholder="Account Holder Name"
              style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#f8fafc;font-size:14px;box-sizing:border-box;">
          </div>
        </div>
      </div>
    `;
  }

  private collectFormData(): VendorFormData | null {
    const name = (document.getElementById('vf_name') as HTMLInputElement)?.value.trim();
    const code = (document.getElementById('vf_code') as HTMLInputElement)?.value.trim();
    if (!name) { alert('Vendor name is required'); return null; }
    if (!code) { alert('Vendor code is required'); return null; }
    const gstTypeEl = document.querySelector('input[name="vf_gst_type"]:checked') as HTMLInputElement;
    return {
      vendor_name: name,
      vendor_code: code.toUpperCase(),
      vendor_type: (document.getElementById('vf_type') as HTMLSelectElement)?.value || 'BOTH',
      gst_type: gstTypeEl?.value || 'CGST_SGST',
      gstin: (document.getElementById('vf_gstin') as HTMLInputElement)?.value.trim() || '',
      pan: (document.getElementById('vf_pan') as HTMLInputElement)?.value.trim() || '',
      contact_person: (document.getElementById('vf_contact') as HTMLInputElement)?.value.trim() || '',
      phone: (document.getElementById('vf_phone') as HTMLInputElement)?.value.trim() || '',
      email: (document.getElementById('vf_email') as HTMLInputElement)?.value.trim().toLowerCase() || '',
      address: (document.getElementById('vf_address') as HTMLInputElement)?.value.trim() || '',
      city: (document.getElementById('vf_city') as HTMLInputElement)?.value.trim() || '',
      state: (document.getElementById('vf_state') as HTMLInputElement)?.value.trim() || '',
      pincode: (document.getElementById('vf_pincode') as HTMLInputElement)?.value.trim() || '',
      bank_name: (document.getElementById('vf_bank') as HTMLInputElement)?.value.trim() || '',
      account_no: (document.getElementById('vf_acc') as HTMLInputElement)?.value.trim() || '',
      ifsc_code: (document.getElementById('vf_ifsc') as HTMLInputElement)?.value.trim() || '',
      account_holder: (document.getElementById('vf_holder') as HTMLInputElement)?.value.trim() || '',
      applicable_companies: ['ALL'],
      is_active: true,
    };
  }

  async loadVendors(): Promise<void> {
    const token = authService.getToken();
    const listEl = document.getElementById('vendorList');
    if (!listEl) return;
    try {
      const resp = await apiService.get('/api/v1/accounts/vendors?limit=500', token || '');
      if (resp.ok) {
        const data = await resp.json();
        this.vendors = Array.isArray(data) ? data : (data.vendors || data.items || []);
        this.applyFilters();
      } else {
        listEl.innerHTML = '<div style="text-align:center;padding:40px;color:#ef4444;">Failed to load vendors</div>';
      }
    } catch (e) {
      listEl.innerHTML = '<div style="text-align:center;padding:40px;color:#ef4444;">Network error</div>';
    }
  }

  onSearch(q: string): void {
    this.searchQuery = q.toLowerCase();
    this.applyFilters();
  }

  onTypeFilter(t: string): void {
    this.typeFilter = t;
    this.applyFilters();
  }

  private applyFilters(): void {
    this.filteredVendors = this.vendors.filter(v => {
      const matchesSearch = !this.searchQuery
        || v.vendor_name.toLowerCase().includes(this.searchQuery)
        || v.vendor_code.toLowerCase().includes(this.searchQuery)
        || (v.gstin || '').toLowerCase().includes(this.searchQuery);
      const matchesType = !this.typeFilter || v.vendor_type === this.typeFilter;
      return matchesSearch && matchesType;
    });
    this.renderList();
  }

  private typeColor(t: string): string {
    const map: Record<string, string> = {
      PRODUCT: '#3b82f6', SERVICE: '#10b981', BOTH: '#8b5cf6', SOLAR: '#f59e0b'
    };
    return map[t] || '#64748b';
  }

  private renderList(): void {
    const listEl = document.getElementById('vendorList');
    if (!listEl) return;
    if (this.filteredVendors.length === 0) {
      listEl.innerHTML = '<div style="text-align:center;padding:40px;color:#64748b;">No vendors found</div>';
      return;
    }
    listEl.innerHTML = this.filteredVendors.map(v => `
      <div onclick="window._vendorsPage.openDetail(${v.id})"
        style="background:#1e293b;border-radius:10px;padding:14px;margin-bottom:10px;cursor:pointer;border:1px solid #334155;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
          <div style="font-weight:600;font-size:14px;color:#f8fafc;flex:1;margin-right:8px;">${this.esc(v.vendor_name)}</div>
          <span style="font-size:11px;padding:2px 8px;border-radius:20px;background:${this.typeColor(v.vendor_type)}22;color:${this.typeColor(v.vendor_type)};white-space:nowrap;">
            ${v.vendor_type}
          </span>
        </div>
        <div style="font-size:12px;color:#64748b;font-family:monospace;">${this.esc(v.vendor_code)}</div>
        ${v.gstin ? `<div style="font-size:12px;color:#94a3b8;margin-top:4px;">GST: ${this.esc(v.gstin)}</div>` : ''}
        ${v.phone ? `<div style="font-size:12px;color:#94a3b8;">📞 ${this.esc(v.phone)}</div>` : ''}
        <div style="display:flex;align-items:center;gap:6px;margin-top:6px;">
          <span style="width:6px;height:6px;border-radius:50%;background:${v.is_active ? '#10b981' : '#ef4444'};"></span>
          <span style="font-size:11px;color:${v.is_active ? '#10b981' : '#ef4444'};">${v.is_active ? 'Active' : 'Inactive'}</span>
        </div>
      </div>
    `).join('');
  }

  openDetail(id: number): void {
    const v = this.vendors.find(x => x.id === id);
    if (!v) return;
    this.editingVendor = v;
    const modal = document.getElementById('vendorModal');
    const title = document.getElementById('vendorModalTitle');
    const body = document.getElementById('vendorModalBody');
    if (!modal || !title || !body) return;
    title.textContent = v.vendor_name;
    body.innerHTML = `
      ${this.renderVendorForm(v)}
      <div style="display:flex;gap:8px;margin-top:16px;">
        <button onclick="window._vendorsPage.submitEdit(${v.id})"
          style="flex:1;padding:12px;background:#3b82f6;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">
          Save Changes
        </button>
        <button onclick="window._vendorsPage.toggleActive(${v.id}, ${!v.is_active})"
          style="padding:12px;background:${v.is_active ? '#ef444422' : '#10b98122'};color:${v.is_active ? '#ef4444' : '#10b981'};border:1px solid ${v.is_active ? '#ef4444' : '#10b981'};border-radius:8px;font-size:13px;cursor:pointer;">
          ${v.is_active ? 'Deactivate' : 'Activate'}
        </button>
      </div>
    `;
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
  }

  closeModal(): void {
    const modal = document.getElementById('vendorModal');
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
    this.editingVendor = null;
  }

  openCreateModal(): void {
    const modal = document.getElementById('createModal');
    if (modal) modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
  }

  closeCreateModal(): void {
    const modal = document.getElementById('createModal');
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  async submitCreate(): Promise<void> {
    const token = authService.getToken();
    const data = this.collectFormData();
    if (!data) return;
    try {
      const resp = await apiService.post('/api/v1/accounts/vendors', data, token || '');
      const json = await resp.json().catch(() => ({}));
      if (resp.ok && json.success !== false) {
        alert('Vendor created successfully');
        this.closeCreateModal();
        await this.loadVendors();
      } else {
        alert(json.detail?.message || json.detail || json.message || 'Failed to create vendor');
      }
    } catch (e) {
      console.error('Create vendor error:', e);
      alert('Network error — failed to create vendor');
    }
  }

  async submitEdit(id: number): Promise<void> {
    const token = authService.getToken();
    const data = this.collectFormData();
    if (!data) return;
    try {
      const resp = await apiService.put(`/api/v1/accounts/vendors/${id}`, data, token || '');
      const json = await resp.json().catch(() => ({}));
      if (resp.ok && json.success !== false) {
        alert('Vendor updated successfully');
        this.closeModal();
        await this.loadVendors();
      } else {
        alert(json.detail?.message || json.detail || json.message || 'Failed to update vendor');
      }
    } catch (e) {
      console.error('Update vendor error:', e);
      alert('Network error — failed to update vendor');
    }
  }

  async toggleActive(id: number, newState: boolean): Promise<void> {
    const token = authService.getToken();
    if (!confirm(`${newState ? 'Activate' : 'Deactivate'} this vendor?`)) return;
    try {
      const resp = await apiService.put(`/api/v1/accounts/vendors/${id}`, { is_active: newState }, token || '');
      const json = await resp.json().catch(() => ({}));
      if (resp.ok && json.success !== false) {
        this.closeModal();
        await this.loadVendors();
      } else {
        alert(json.detail?.message || json.detail || json.message || 'Failed to update vendor');
      }
    } catch (e) {
      alert('Network error');
    }
  }

  private esc(s: string): string {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  destroy(): void {
    delete (window as any)._vendorsPage;
    document.body.style.overflow = '';
  }
}
