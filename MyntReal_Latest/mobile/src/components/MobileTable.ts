/**
 * MobileTable Component - Web Table Parity
 * DC Protocol: DC_MOBILE_TABLE_PARITY_001
 * Replicates exact web Bootstrap table format with horizontal scroll
 */

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  width?: string;
  render?: (value: any, row: any) => string;
}

export interface MobileTableConfig {
  columns: TableColumn[];
  data: any[];
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (column: string, direction: 'asc' | 'desc') => void;
  emptyMessage?: string;
  loading?: boolean;
}

export class MobileTable {
  private config: MobileTableConfig;
  
  constructor(config: MobileTableConfig) {
    this.config = config;
  }

  render(): string {
    if (this.config.loading) {
      return `
        <div class="table-loading">
          <div class="spinner"></div>
          <p>Loading...</p>
        </div>
      `;
    }

    if (!this.config.data || this.config.data.length === 0) {
      return `
        <div class="table-empty">
          <p>${this.config.emptyMessage || 'No data found'}</p>
        </div>
      `;
    }

    const getSortIcon = (column: string): string => {
      if (this.config.sortColumn === column) {
        return this.config.sortDirection === 'asc' ? ' ↑' : ' ↓';
      }
      return '';
    };

    const headerCells = this.config.columns.map(col => {
      const sortable = col.sortable !== false;
      const sortIcon = getSortIcon(col.key);
      const style = col.width ? `width: ${col.width};` : '';
      const sortAttr = sortable ? `data-sort-column="${col.key}"` : '';
      const cursorStyle = sortable ? 'cursor: pointer;' : '';
      return `<th style="${style}${cursorStyle}" ${sortAttr}>${col.label}${sortIcon}</th>`;
    }).join('');

    const rows = this.config.data.map(row => {
      const cells = this.config.columns.map(col => {
        const value = row[col.key];
        const rendered = col.render ? col.render(value, row) : (value ?? '-');
        return `<td>${rendered}</td>`;
      }).join('');
      return `<tr>${cells}</tr>`;
    }).join('');

    return `
      <div class="table-responsive-wrapper">
        <table class="mobile-data-table">
          <thead>
            <tr>${headerCells}</tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  }

  static getStyles(): string {
    return `
      .table-responsive-wrapper {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        margin-bottom: 16px;
        background: #0d1b2a;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
      }

      .mobile-data-table {
        width: 100%;
        min-width: 0;
        border-collapse: collapse;
        font-size: 11px;
        table-layout: auto;
      }

      .mobile-data-table thead {
        background: linear-gradient(135deg, #1b263b 0%, #0d1b2a 100%);
        position: sticky;
        top: 0;
        z-index: 10;
      }

      .mobile-data-table th {
        padding: 6px 4px;
        text-align: left;
        font-weight: 600;
        color: #8892b0;
        text-transform: uppercase;
        font-size: 9px;
        letter-spacing: 0.3px;
        border-bottom: 2px solid rgba(255,255,255,0.1);
        white-space: nowrap;
      }

      .mobile-data-table th[data-sort-column]:hover {
        color: #64d2ff;
        background: rgba(100, 210, 255, 0.1);
      }

      .mobile-data-table tbody tr {
        border-bottom: 1px solid rgba(255,255,255,0.05);
        transition: background 0.2s;
      }

      .mobile-data-table tbody tr:hover {
        background: rgba(255,255,255,0.03);
      }

      .mobile-data-table td {
        padding: 5px 4px;
        color: #e6f1ff;
        vertical-align: middle;
        white-space: nowrap;
        font-size: 11px;
      }

      .mobile-data-table .badge {
        display: inline-block;
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 9px;
        font-weight: 500;
      }

      .mobile-data-table .badge-success {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
      }

      .mobile-data-table .badge-warning {
        background: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
      }

      .mobile-data-table .badge-danger {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
      }

      .mobile-data-table .badge-info {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
      }

      .mobile-data-table .badge-secondary {
        background: rgba(107, 114, 128, 0.2);
        color: #9ca3af;
      }

      .mobile-data-table .badge-primary {
        background: rgba(99, 102, 241, 0.2);
        color: #818cf8;
      }

      .mobile-data-table .badge-platinum {
        background: rgba(217, 119, 6, 0.2);
        color: #fbbf24;
      }

      .mobile-data-table .badge-diamond {
        background: rgba(6, 182, 212, 0.2);
        color: #22d3ee;
      }

      .table-loading, .table-empty {
        padding: 40px 20px;
        text-align: center;
        color: #8892b0;
      }

      .table-loading .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid rgba(100, 210, 255, 0.2);
        border-top-color: #64d2ff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 12px;
      }

      @keyframes spin {
        to { transform: rotate(360deg); }
      }

      .table-summary-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background: rgba(22, 33, 62, 0.6);
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 11px;
        color: #8892b0;
      }

      .table-summary-bar .count {
        color: #64d2ff;
        font-weight: 600;
      }

      .table-pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        padding: 10px;
      }

      .table-pagination button {
        padding: 6px 12px;
        background: rgba(100, 210, 255, 0.1);
        border: 1px solid rgba(100, 210, 255, 0.3);
        border-radius: 6px;
        color: #64d2ff;
        font-size: 11px;
        cursor: pointer;
      }

      .table-pagination button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      .table-pagination .page-info {
        color: #8892b0;
        font-size: 11px;
      }
    `;
  }

  static attachSortListeners(container: HTMLElement, onSort: (column: string) => void): void {
    container.querySelectorAll('[data-sort-column]').forEach(th => {
      th.addEventListener('click', () => {
        const column = th.getAttribute('data-sort-column');
        if (column) onSort(column);
      });
    });
  }
}
