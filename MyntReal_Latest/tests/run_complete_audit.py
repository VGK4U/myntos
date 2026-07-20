#!/usr/bin/env python3
"""
COMPLETE SYSTEMATIC AUDIT - ALL ROLES INCLUDING USER
Tests all 5 roles: User, VGK Admin, Finance Admin, Admin, Super Admin
"""

import sys
sys.path.insert(0, '.')
from systematic_audit_framework import SystematicAudit
import json
from datetime import datetime

if __name__ == "__main__":
    auditor = SystematicAudit()
    
    print("\n" + "="*80)
    print("🚀 COMPLETE SYSTEMATIC AUDIT - ALL ROLES")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Testing: User + VGK Admin + Finance Admin + Admin + Super Admin")
    print("="*80)
    
    all_results = {}
    
    # 1. User Pages Audit
    print("\n\n" + "█"*80)
    print("█ PHASE 1: REGULAR USER AUDIT")
    print("█"*80)
    user_results = auditor.audit_user_pages()
    all_results['user'] = user_results
    
    # 2. VGK Admin Audit (already done, but re-run for completeness)
    print("\n\n" + "█"*80)
    print("█ PHASE 2: VGK ADMIN AUDIT")
    print("█"*80)
    vgk_results = auditor.audit_vgk_admin()
    all_results['vgk_admin'] = vgk_results
    
    # 3. Finance Admin Audit
    print("\n\n" + "█"*80)
    print("█ PHASE 3: FINANCE ADMIN AUDIT")
    print("█"*80)
    finance_results = auditor.audit_finance_admin()
    all_results['finance_admin'] = finance_results
    
    # 4. Admin Audit
    print("\n\n" + "█"*80)
    print("█ PHASE 4: ADMIN AUDIT")
    print("█"*80)
    admin_results = auditor.audit_admin()
    all_results['admin'] = admin_results
    
    # 5. Super Admin Audit
    print("\n\n" + "█"*80)
    print("█ PHASE 5: SUPER ADMIN AUDIT")
    print("█"*80)
    super_results = auditor.audit_super_admin()
    all_results['super_admin'] = super_results
    
    # Save complete results
    with open('/tmp/complete_audit_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n\n" + "="*80)
    print("🎯 COMPLETE AUDIT FINISHED")
    print("="*80)
    print(f"📝 Full results saved to: /tmp/complete_audit_results.json")
    print("\nNext: Review all errors and categorize by severity")

