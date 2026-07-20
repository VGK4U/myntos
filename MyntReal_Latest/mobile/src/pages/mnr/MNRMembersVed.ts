/**
 * MNR Ved Team Members Page - Web Table Parity
 * DC Protocol: DC_MOBILE_MNR_MEMBERS_VED_003
 * Exact web table replication: Name, MNR ID, Package, Position, Level, Reg Date, Act Date, Status
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface VedMember {
  mnr_id: string;
  name: string;
  package: string;
  position: string;
  level: number;
  registration_date: string | null;
  activation_date: string | null;
  status: string;
}

interface VedHead {
  mnr_id: string;
  name: string;
  package: string;
  status: string;
  activation_date: string | null;
}

interface FilterState {
  name: string;
  status_filter: string;
  package: string;
  position: string;
  level: string;
  start_date: string;
  end_date: string;
}

export class MNRMembersVed {
  private container: HTMLElement;
  private members: VedMember[] = [];
  private vedHead: VedHead | null = null;
  private loading: boolean = true;
  private showFilters: boolean = false;
  private sortColumn: string = 'level';
  private sortDirection: 'asc' | 'desc' = 'asc';
  private filters: FilterState = {
    name: '',
    status_filter: '',
    package: '',
    position: '',
    level: '',
    start_date: '',
    end_date: ''
  };

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadMembers();
  }

  private async loadMembers(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      if (this.filters.name) params.append('name', this.filters.name);
      if (this.filters.status_filter) params.append('status_filter', this.filters.status_filter);
      if (this.filters.package) params.append('package', this.filters.package);
      if (this.filters.position) params.append('position', this.filters.position);
      if (this.filters.level) params.append('level', this.filters.level);
      if (this.filters.start_date) params.append('start_date', this.filters.start_date);
      if (this.filters.end_date) params.append('end_date', this.filters.end_date);

      const response = await apiService.get<any>(`/users/team/ved-members?${params}`);
      if (response.success && response.data) {
        if (response.data.ved_head) {
          this.vedHead = {
            mnr_id: response.data.ved_head.mnr_id || response.data.ved_head.user_id || '',
            name: response.data.ved_head.name || '',
            package: response.data.ved_head.package || response.data.ved_head.package_type || 'None',
            status: response.data.ved_head.is_active ? 'Active' : 'Inactive',
            activation_date: response.data.ved_head.activation_date
          };
        }
        const allMembers = response.data.all_ved_members || response.data.ved_members || [];
        this.members = allMembers.map((m: any) => ({
          mnr_id: m.mnr_id || m.user_id || '',
          name: m.name || '',
          package: m.package || m.package_type || 'None',
          position: m.side || m.position || '',
          level: m.level || 0,
          registration_date: m.registration_date,
          activation_date: m.activation_date,
          status: m.activation_date ? 'Active' : 'Inactive'
        }));
      }
    } catch (error) {
      console.error('[MNRMembersVed] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .mnr-ved-page { padding: 16px; }
        .ved-head-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .ved-head-card h4 { margin: 0 0 8px; font-size: 14px; opacity: 0.9; }
        .ved-head-card .name { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
        .ved-head-card .details { display: flex; gap: 16px; font-size: 13px; opacity: 0.9; }
        .filter-toggle-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: rgba(100, 210, 255, 0.1);
          border: 1px solid rgba(100, 210, 255, 0.3);
          border-radius: 8px;
          color: #64d2ff;
          font-size: 14px;
          cursor: pointer;
          margin-bottom: 12px;
        }
        .filter-count {
          background: #ef4444;
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          display: none;
        }
        .filters-panel {
          display: none;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .filters-panel.show { display: block; }
        .filter-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }
        .filter-group label {
          display: block;
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .filter-group input, .filter-group select {
          width: 100%;
          padding: 8px 12px;
          background: rgba(13, 27, 42, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 6px;
          color: #e6f1ff;
          font-size: 13px;
        }
        .filter-actions {
          display: flex;
          gap: 12px;
          margin-top: 16px;
        }
        .filter-actions button {
          flex: 1;
          padding: 10px;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
        }
        .btn-apply {
          background: #64d2ff;
          border: none;
          color: #0d1b2a;
          font-weight: 600;
        }
        .btn-clear {
          background: transparent;
          border: 1px solid rgba(255,255,255,0.2);
          color: #8892b0;
        }
      </style>
      ${PageHeader.render({ title: '👑 Leadership Group (VED)', showBack: true })}
      <div class="mnr-ved-page">
        <div id="vedHeadSection"></div>
        
        <button class="filter-toggle-btn" id="toggleFiltersBtn">
          <span>🔍 Filter Options</span>
          <span class="filter-count" id="filterCount">0</span>
        </button>
        
        <div class="filters-panel" id="filtersPanel">
          <div class="filter-grid">
            <div class="filter-group">
              <label>Name</label>
              <input type="text" id="filterName" placeholder="Search name" value="${this.filters.name}">
            </div>
            <div class="filter-group">
              <label>Status</label>
              <select id="filterStatus">
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Package</label>
              <select id="filterPackage">
                <option value="">All Packages</option>
                <option value="Platinum">Platinum</option>
                <option value="Diamond">Diamond</option>
                <option value="Star">Star</option>
                <option value="Loyal">Loyal</option>
                <option value="Blue">Blue</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Group</label>
              <select id="filterPosition">
                <option value="">All Groups</option>
                <option value="left">Group A</option>
                <option value="right">Group B</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Level</label>
              <select id="filterLevel">
                <option value="">All Levels</option>
                ${[1,2,3,4,5,6,7,8,9,10].map(l => `<option value="${l}">Level ${l}</option>`).join('')}
              </select>
            </div>
            <div class="filter-group">
              <label>Start Date</label>
              <input type="date" id="filterStartDate" value="${this.filters.start_date}">
            </div>
          </div>
          <div class="filter-actions">
            <button class="btn-apply" id="applyFiltersBtn">Apply Filters</button>
            <button class="btn-clear" id="clearFiltersBtn">Clear</button>
          </div>
        </div>

        <div id="pageContent"></div>
      </div>
    `;
    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: '👑 Leadership Group (VED)', showBack: true });

    document.getElementById('toggleFiltersBtn')?.addEventListener('click', () => {
      this.showFilters = !this.showFilters;
      document.getElementById('filtersPanel')?.classList.toggle('show', this.showFilters);
    });

    document.getElementById('applyFiltersBtn')?.addEventListener('click', () => {
      this.collectFilters();
      this.loadMembers();
    });

    document.getElementById('clearFiltersBtn')?.addEventListener('click', () => {
      this.filters = { name: '', status_filter: '', package: '', position: '', level: '', start_date: '', end_date: '' };
      this.render();
      this.loadMembers();
    });
  }

  private collectFilters(): void {
    this.filters.name = (document.getElementById('filterName') as HTMLInputElement)?.value || '';
    this.filters.status_filter = (document.getElementById('filterStatus') as HTMLSelectElement)?.value || '';
    this.filters.package = (document.getElementById('filterPackage') as HTMLSelectElement)?.value || '';
    this.filters.position = (document.getElementById('filterPosition') as HTMLSelectElement)?.value || '';
    this.filters.level = (document.getElementById('filterLevel') as HTMLSelectElement)?.value || '';
    this.filters.start_date = (document.getElementById('filterStartDate') as HTMLInputElement)?.value || '';
    
    const count = Object.values(this.filters).filter(v => v).length;
    const countEl = document.getElementById('filterCount');
    if (countEl) {
      countEl.textContent = count.toString();
      countEl.style.display = count > 0 ? 'inline-flex' : 'none';
    }
  }

  private handleSort(column: string): void {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'asc';
    }
    this.sortMembers();
    this.updateContent();
  }

  private sortMembers(): void {
    this.members.sort((a, b) => {
      let valA: any, valB: any;
      switch (this.sortColumn) {
        case 'name': valA = a.name.toLowerCase(); valB = b.name.toLowerCase(); break;
        case 'mnr_id': valA = a.mnr_id; valB = b.mnr_id; break;
        case 'level': valA = a.level; valB = b.level; break;
        case 'registration_date':
          valA = a.registration_date ? new Date(a.registration_date).getTime() : 0;
          valB = b.registration_date ? new Date(b.registration_date).getTime() : 0;
          break;
        case 'activation_date':
          valA = a.activation_date ? new Date(a.activation_date).getTime() : 0;
          valB = b.activation_date ? new Date(b.activation_date).getTime() : 0;
          break;
        case 'status': valA = a.status === 'Active' ? 1 : 0; valB = b.status === 'Active' ? 1 : 0; break;
        default: return 0;
      }
      if (valA < valB) return this.sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return this.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }

  private updateContent(): void {
    const vedHeadSection = document.getElementById('vedHeadSection');
    if (vedHeadSection && this.vedHead) {
      vedHeadSection.innerHTML = `
        <div class="ved-head-card">
          <h4>Ved Head</h4>
          <div class="name">${this.vedHead.name}</div>
          <div class="details">
            <span>${this.vedHead.mnr_id}</span>
            <span>${this.vedHead.package}</span>
            <span>${this.vedHead.status}</span>
          </div>
        </div>
      `;
    }

    const content = document.getElementById('pageContent');
    if (!content) return;

    const table = new MobileTable({
      columns: [
        { key: 'name', label: 'Name', sortable: true, render: (v) => `<strong>${v}</strong>` },
        { key: 'mnr_id', label: 'MNR ID', sortable: true },
        { key: 'package', label: 'Package', sortable: true, render: (v) => this.getPackageBadge(v) },
        { key: 'position', label: 'Group', sortable: true, render: (v) => { const p = (v || '').toLowerCase(); return p === 'left' ? 'Group A' : p === 'right' ? 'Group B' : v || '-'; } },
        { key: 'level', label: 'Level', sortable: true, render: (v) => `L${v}` },
        { key: 'registration_date', label: 'Reg Date', sortable: true, render: (v) => this.formatDate(v) },
        { key: 'activation_date', label: 'Act Date', sortable: true, render: (v) => this.formatDate(v) },
        { key: 'status', label: 'Status', sortable: true, render: (v) => this.getStatusBadge(v) }
      ],
      data: this.members,
      sortColumn: this.sortColumn,
      sortDirection: this.sortDirection,
      loading: this.loading,
      emptyMessage: 'No Ved members found'
    });

    content.innerHTML = `
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.members.length}</span> Ved members</span>
      </div>
      ${table.render()}
    `;

    MobileTable.attachSortListeners(content, (col) => this.handleSort(col));
  }

  private getPackageBadge(pkg: string): string {
    const classes: Record<string, string> = {
      'Platinum': 'badge-platinum',
      'Diamond': 'badge-diamond',
      'Star': 'badge-warning',
      'Loyal': 'badge-info',
      'Blue': 'badge-primary'
    };
    return `<span class="badge ${classes[pkg] || 'badge-secondary'}">${pkg}</span>`;
  }

  private getStatusBadge(status: string): string {
    return status === 'Active' 
      ? '<span class="badge badge-success">Active</span>'
      : '<span class="badge badge-secondary">Inactive</span>';
  }

  private formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
}
