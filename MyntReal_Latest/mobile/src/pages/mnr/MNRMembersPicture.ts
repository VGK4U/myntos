/**
 * MNR Members Picture View (Binary Tree) - Web Parity
 * DC Protocol: DC_MOBILE_MNR_MEMBERS_PICTURE_005
 * Improved tree visualization with better connections and spacing
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface TreeNode {
  mnr_id: string;
  name: string;
  package: string;
  status: string;
  registration_date: string | null;
  activation_date: string | null;
  coupon_status: string;
  left_child?: TreeNode | null;
  right_child?: TreeNode | null;
}

interface TreeData {
  root: TreeNode;
  left_child?: TreeNode | null;
  right_child?: TreeNode | null;
  left_count?: number;
  right_count?: number;
  left_active_count?: number;
  right_active_count?: number;
}

export class MNRMembersPicture {
  private container: HTMLElement;
  private treeData: TreeData | null = null;
  private loading: boolean = true;
  private currentUserId: string = '';
  private initialUserId: string = '';
  private totalMembers: number = 0;
  private navigationHistory: string[] = [];
  private currentDepth: number = 0;
  private readonly MAX_NAVIGATION_DEPTH: number = 7;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadTree();
    this.initialUserId = this.currentUserId;
    this.currentDepth = 0;
  }

  private async loadTree(userId?: string): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const endpoint = userId 
        ? `/users/team/binary-tree?user_id=${encodeURIComponent(userId)}`
        : '/users/team/binary-tree';
      
      const response = await apiService.get<any>(endpoint);
      if (response.success && response.data) {
        this.treeData = response.data;
        this.currentUserId = response.data.root?.mnr_id || '';
        this.totalMembers = this.countAllNodes(response.data);
      }
    } catch (error) {
      console.error('[MNRMembersPicture] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private countAllNodes(data: TreeData): number {
    let count = 0;
    if (data.root) count++;
    if (data.left_child) count++;
    if (data.right_child) count++;
    if (data.left_child?.left_child) count++;
    if (data.left_child?.right_child) count++;
    if (data.right_child?.left_child) count++;
    if (data.right_child?.right_child) count++;
    return count;
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .picture-page { padding: 16px; min-height: 100vh; background: #0d1b2a; }
        
        .page-banner {
          background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .page-banner h2 { margin: 0 0 4px; font-size: 16px; }
        .page-banner p { margin: 0; font-size: 11px; opacity: 0.9; }
        
        .nav-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 12px;
          padding: 12px 16px;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .btn-back {
          padding: 8px 16px;
          border-radius: 8px;
          border: none;
          background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
          color: white;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
        }
        .nav-info {
          color: #93c5fd;
          font-size: 12px;
        }
        
        .count-badges {
          display: flex;
          gap: 8px;
        }
        .count-badge {
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .count-badge.left {
          background: rgba(147, 51, 234, 0.3);
          color: #c4b5fd;
        }
        .count-badge.right {
          background: rgba(236, 72, 153, 0.3);
          color: #fbcfe8;
        }
        
        .tree-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 12px;
          overflow: hidden;
        }
        .tree-header {
          background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
          padding: 14px 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .tree-header h5 { margin: 0; color: white; font-size: 14px; }
        .tree-header .badge {
          background: rgba(255,255,255,0.2);
          color: white;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
        }
        
        .tree-container {
          padding: 30px 16px;
          overflow-x: auto;
          background: linear-gradient(180deg, rgba(13,27,42,0.5) 0%, rgba(22,33,62,0.3) 100%);
        }
        .tree-wrapper {
          min-width: 620px;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        
        /* ========== TREE STRUCTURE ========== */
        
        /* ROOT LEVEL */
        .level-root {
          display: flex;
          justify-content: center;
          margin-bottom: 0;
        }
        
        /* Vertical line from root */
        .connector-root-down {
          width: 4px;
          height: 35px;
          background: linear-gradient(to bottom, #10b981, #059669);
          margin: 0 auto;
          border-radius: 2px;
        }
        
        /* Horizontal split bar */
        .connector-split {
          width: 280px;
          height: 4px;
          background: linear-gradient(to right, #9333ea 0%, #10b981 50%, #ec4899 100%);
          margin: 0 auto;
          border-radius: 2px;
          position: relative;
        }
        .connector-split::before,
        .connector-split::after {
          content: '';
          position: absolute;
          width: 4px;
          height: 35px;
          top: 4px;
          border-radius: 2px;
        }
        .connector-split::before {
          left: 0;
          background: linear-gradient(to bottom, #9333ea, #7c3aed);
        }
        .connector-split::after {
          right: 0;
          background: linear-gradient(to bottom, #ec4899, #db2777);
        }
        
        /* LEVEL 1: Children */
        .level-children {
          display: flex;
          justify-content: center;
          gap: 160px;
          margin-top: 35px;
        }
        
        /* Connectors from Level 1 to Level 2 */
        .level-1-connectors {
          display: flex;
          justify-content: center;
          gap: 160px;
          margin-top: 20px;
        }
        .branch-connector {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .connector-down-small {
          width: 4px;
          height: 25px;
          border-radius: 2px;
        }
        .connector-down-small.left { background: linear-gradient(to bottom, #9333ea, #7c3aed); }
        .connector-down-small.right { background: linear-gradient(to bottom, #ec4899, #db2777); }
        
        .connector-branch-split {
          width: 120px;
          height: 4px;
          border-radius: 2px;
          position: relative;
        }
        .connector-branch-split.left { background: linear-gradient(to right, #a855f7, #9333ea, #a855f7); }
        .connector-branch-split.right { background: linear-gradient(to right, #f472b6, #ec4899, #f472b6); }
        .connector-branch-split::before,
        .connector-branch-split::after {
          content: '';
          position: absolute;
          width: 4px;
          height: 25px;
          top: 4px;
          border-radius: 2px;
        }
        .connector-branch-split.left::before,
        .connector-branch-split.left::after { background: #9333ea; }
        .connector-branch-split.right::before,
        .connector-branch-split.right::after { background: #ec4899; }
        .connector-branch-split::before { left: 0; }
        .connector-branch-split::after { right: 0; }
        
        /* LEVEL 2: Grandchildren */
        .level-grandchildren {
          display: flex;
          justify-content: center;
          gap: 40px;
          margin-top: 25px;
        }
        .grandchild-group {
          display: flex;
          gap: 16px;
        }
        .grandchild-spacer {
          width: 90px;
        }
        
        /* ========== NODE STYLES ========== */
        .tree-node {
          width: 125px;
          background: white;
          border-radius: 14px;
          padding: 14px 10px 12px;
          text-align: center;
          box-shadow: 0 6px 20px rgba(0,0,0,0.25);
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
          border: 3px solid transparent;
          position: relative;
        }
        .tree-node:active { transform: scale(0.96); box-shadow: 0 3px 10px rgba(0,0,0,0.2); }
        .tree-node.active {
          background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        }
        .tree-node.inactive { background: #f3f4f6; }
        .tree-node.root { border-color: #10b981; box-shadow: 0 6px 25px rgba(16,185,129,0.35); }
        .tree-node.left { border-color: #9333ea; box-shadow: 0 6px 20px rgba(147,51,234,0.3); }
        .tree-node.right { border-color: #ec4899; box-shadow: 0 6px 20px rgba(236,72,153,0.3); }
        
        .node-name {
          font-weight: 700;
          font-size: 11px;
          margin-bottom: 3px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .tree-node.active .node-name { color: white; }
        .tree-node:not(.active) .node-name { color: #1f2937; }
        
        .node-id { font-size: 9px; margin-bottom: 6px; font-weight: 600; }
        .tree-node.root .node-id { color: #059669; }
        .tree-node.left .node-id { color: #9333ea; }
        .tree-node.right .node-id { color: #ec4899; }
        .tree-node.active .node-id { color: rgba(255,255,255,0.9); }
        
        .status-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 8px;
          font-weight: 700;
          margin-bottom: 6px;
          text-transform: uppercase;
        }
        .status-badge.active { background: #10b981; color: white; }
        .status-badge.inactive { background: #9ca3af; color: white; }
        
        .node-package {
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 8px;
          font-weight: 700;
          color: white;
          text-transform: uppercase;
        }
        .tree-node.root .node-package { background: #059669; }
        .tree-node.left .node-package { background: #9333ea; }
        .tree-node.right .node-package { background: #ec4899; }
        
        .node-position {
          margin-top: 5px;
          font-size: 8px;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .tree-node.root .node-position { color: #059669; }
        .tree-node.left .node-position { color: #9333ea; }
        .tree-node.right .node-position { color: #ec4899; }
        .tree-node.active .node-position { color: rgba(255,255,255,0.8); }
        
        /* Empty Slot */
        .empty-slot {
          width: 125px;
          border: 3px dashed #4b5563;
          border-radius: 14px;
          padding: 18px 10px;
          text-align: center;
          background: rgba(75, 85, 99, 0.15);
        }
        .empty-slot .icon { font-size: 20px; margin-bottom: 4px; }
        .empty-slot .label { font-size: 9px; color: #9ca3af; font-weight: 500; }
        .empty-slot .position { font-size: 8px; font-weight: 700; margin-top: 3px; }
        .empty-slot.left { border-color: rgba(147,51,234,0.4); }
        .empty-slot.right { border-color: rgba(236,72,153,0.4); }
        .empty-slot.left .position { color: #a855f7; }
        .empty-slot.right .position { color: #f472b6; }
        
        /* Legend */
        .tree-legend {
          display: flex;
          justify-content: center;
          gap: 20px;
          margin-top: 30px;
          padding: 16px;
          background: rgba(13,27,42,0.5);
          border-radius: 10px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 10px;
          color: #94a3b8;
          font-weight: 500;
        }
        .legend-dot {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          border: 2px solid;
        }
        .legend-dot.root { background: #10b981; border-color: #059669; }
        .legend-dot.left { background: #9333ea; border-color: #7c3aed; }
        .legend-dot.right { background: #ec4899; border-color: #db2777; }
        
        .loading-state, .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #8892b0;
        }
        .empty-state .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .empty-state h3 { color: #e6f1ff; margin: 0 0 8px; font-size: 16px; }
        .empty-state p { margin: 0; font-size: 13px; }
      </style>
      ${PageHeader.render({ title: '🌳 Connections Gallery', showBack: true })}
      <div class="picture-page" id="pageContent">
        <div class="loading-state">Loading tree structure...</div>
      </div>
    `;

    PageHeader.attachListeners({ title: '🌳 Connections Gallery', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading tree structure...</div>';
      return;
    }

    const canGoBack = this.navigationHistory.length > 0;

    content.innerHTML = `
      <div class="page-banner">
        <h2>🌳 Connections Gallery</h2>
        <p>Tap any team member to navigate their tree</p>
      </div>

      ${canGoBack ? `
        <div class="nav-card">
          <button class="btn-back" id="btnGoBack">⬅ Go Back</button>
          <span class="nav-info">Viewing: ${this.currentUserId}</span>
        </div>
      ` : ''}

      ${this.treeData && this.treeData.root ? this.renderTreeView() : this.renderEmptyState()}
    `;

    this.attachListeners();
  }

  private renderTreeView(): string {
    if (!this.treeData) return '';

    const root = this.treeData.root;
    const leftChild = this.treeData.left_child;
    const rightChild = this.treeData.right_child;
    const hasChildren = leftChild || rightChild;
    const hasGrandchildren = leftChild?.left_child || leftChild?.right_child || rightChild?.left_child || rightChild?.right_child;
    
    const leftTotal = this.treeData.left_count || 0;
    const rightTotal = this.treeData.right_count || 0;
    const leftActive = this.treeData.left_active_count || 0;
    const rightActive = this.treeData.right_active_count || 0;

    return `
      <div class="tree-card">
        <div class="tree-header">
          <h5>📊 Binary Tree Structure</h5>
          <div class="count-badges">
            <span class="count-badge left">L: ${leftTotal} (${leftActive})</span>
            <span class="count-badge right">R: ${rightTotal} (${rightActive})</span>
          </div>
        </div>
        <div class="tree-container">
          <div class="tree-wrapper">
            
            <!-- LEVEL 0: ROOT -->
            <div class="level-root">
              ${this.renderNode(root, 'root')}
            </div>
            
            ${hasChildren ? `
              <!-- Connector: Root to Children -->
              <div class="connector-root-down"></div>
              <div class="connector-split"></div>
              
              <!-- LEVEL 1: LEFT & RIGHT CHILDREN -->
              <div class="level-children">
                ${leftChild ? this.renderNode(leftChild, 'left') : this.renderEmptySlot('Left', 'left')}
                ${rightChild ? this.renderNode(rightChild, 'right') : this.renderEmptySlot('Right', 'right')}
              </div>
            ` : ''}
            
            ${hasGrandchildren ? `
              <!-- Connectors: Children to Grandchildren -->
              <div class="level-1-connectors">
                <div class="branch-connector">
                  <div class="connector-down-small left"></div>
                  <div class="connector-branch-split left"></div>
                </div>
                <div class="branch-connector">
                  <div class="connector-down-small right"></div>
                  <div class="connector-branch-split right"></div>
                </div>
              </div>
              
              <!-- LEVEL 2: GRANDCHILDREN -->
              <div class="level-grandchildren">
                <div class="grandchild-group">
                  ${leftChild?.left_child ? this.renderNode(leftChild.left_child, 'left') : this.renderEmptySlot('LL', 'left')}
                  ${leftChild?.right_child ? this.renderNode(leftChild.right_child, 'left') : this.renderEmptySlot('LR', 'left')}
                </div>
                <div class="grandchild-spacer"></div>
                <div class="grandchild-group">
                  ${rightChild?.left_child ? this.renderNode(rightChild.left_child, 'right') : this.renderEmptySlot('RL', 'right')}
                  ${rightChild?.right_child ? this.renderNode(rightChild.right_child, 'right') : this.renderEmptySlot('RR', 'right')}
                </div>
              </div>
            ` : ''}
            
            <!-- Legend -->
            <div class="tree-legend">
              <div class="legend-item"><div class="legend-dot root"></div> Root</div>
              <div class="legend-item"><div class="legend-dot left"></div> Left Branch</div>
              <div class="legend-item"><div class="legend-dot right"></div> Right Branch</div>
            </div>
            
          </div>
        </div>
      </div>
    `;
  }

  private renderNode(node: TreeNode, position: 'root' | 'left' | 'right'): string {
    const isActive = node.status === 'Active';
    const statusClass = isActive ? 'active' : 'inactive';
    const positionLabel = position === 'left' ? 'LEFT' : position === 'right' ? 'RIGHT' : 'ROOT';
    const shortName = node.name.length > 11 ? node.name.substring(0, 9) + '..' : node.name;

    return `
      <div class="tree-node ${statusClass} ${position}" data-mnr-id="${this.escapeHtml(node.mnr_id)}" onclick="window.viewUserTree && window.viewUserTree('${this.escapeHtml(node.mnr_id)}')">
        <div class="node-name">${this.escapeHtml(shortName)}</div>
        <div class="node-id">${this.escapeHtml(node.mnr_id)}</div>
        <span class="status-badge ${statusClass}">${isActive ? 'Active' : 'Inactive'}</span>
        <div class="node-package">${this.escapeHtml(node.package || 'N/A')}</div>
        <div class="node-position">${positionLabel}</div>
      </div>
    `;
  }

  private renderEmptySlot(label: string, side: 'left' | 'right'): string {
    return `
      <div class="empty-slot ${side}">
        <div class="icon">➕</div>
        <div class="label">Empty Slot</div>
        <div class="position">${label}</div>
      </div>
    `;
  }

  private renderEmptyState(): string {
    return `
      <div class="tree-card">
        <div class="tree-header">
          <h5>📊 Binary Tree Structure</h5>
          <span class="badge">0 members</span>
        </div>
        <div class="empty-state">
          <div class="icon">🌳</div>
          <h3>No Team Structure Found</h3>
          <p>This user has no team members yet.</p>
        </div>
      </div>
    `;
  }

  private attachListeners(): void {
    (window as any).viewUserTree = (mnrId: string) => {
      if (!mnrId) return;
      if (mnrId === this.currentUserId) return;
      
      if (this.currentDepth >= this.MAX_NAVIGATION_DEPTH) {
        alert(`Maximum navigation depth (${this.MAX_NAVIGATION_DEPTH} levels) reached. Cannot navigate further.`);
        return;
      }
      
      this.navigationHistory.push(this.currentUserId);
      this.currentDepth++;
      this.loadTree(mnrId);
    };

    document.getElementById('btnGoBack')?.addEventListener('click', () => {
      const previousUserId = this.navigationHistory.pop();
      if (previousUserId) {
        this.currentDepth = Math.max(0, this.currentDepth - 1);
        this.loadTree(previousUserId);
      }
    });
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }
}
