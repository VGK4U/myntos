# KRA Review Dashboard - Filter Implementation Plan
## Comprehensive Analysis & Role-Based Architecture

**Date**: December 2, 2025  
**Status**: AWAITING YOUR APPROVAL  
**System**: WVV/DC Compliant KRA Review Dashboard

---

## 📋 CURRENT PAGE ANALYSIS

### What's Currently Working ✅
- **URL**: `/staff/kra-review`
- **Title**: "KRAs Pending Review"
- **Existing Filters**:
  - Search by employee name/ID (text input)
  - Filter by frequency (Daily, Weekly, Monthly, etc.)
- **Display Columns**:
  - Employee (name + ID avatar)
  - KRA Title
  - Frequency
  - Self Rating (star display)
  - Submitted Date
  - Action Buttons (View, Approve, Edit & Approve, Reject)
- **Statistics Pills**: Pending (130), Approved Today, Rejected Today

### Backend API Already Supports ✅
- Date range filtering (`date_from`, `date_to`)
- Employee ID filtering
- Automatic role-based filtering:
  - **Managers**: See only direct reports
  - **HR/Executive Assistant**: See all staff
  - **VGK4U Supreme** (level ≥150): See all
- Status filtering (completion_status, manager_review_status)

---

## 🎯 PROPOSED FILTER IMPLEMENTATION

### **SECTION 1: Date & Time Filters**
**Purpose**: WVV-PHASE1 WRITE - Narrow data scope before filtering
```
📅 Date Range Section (Collapsible)
├─ From Date: [Pick date]  →  Default: Today - 30 days
├─ To Date: [Pick date]     →  Default: Today
└─ Quick Options Buttons: [Last 7 Days] [Last 30 Days] [Current Month] [All]
```
**WVV Logic**:
- WRITE: User selects date range → Frontend stores in filter state
- VERIFY: Backend validates dates against assignment effective dates
- VALIDATE: Only display instances within valid date range

---

### **SECTION 2: Employee & Department Filters**
**Purpose**: DC Protocol - Ensure data belongs to viewing role's hierarchy

**For VGK4U Supreme (Level ≥150) & HR:**
```
👥 Employee Search & Department (Multi-select)
├─ Employee Multi-Select Dropdown: [Search by name/ID]
├─ Department Multi-Select: [HR] [Sales] [Ops] [Tech] [Finance]
├─ Role Filter (Optional): [Manager] [Team Lead] [Executive] [Staff]
└─ Manager Filter: [Show all managers] [Only my direct reports]
```

**For Managers (Level 60-149):**
```
👥 Employee Filters (Auto-Limited to Team)
├─ Team Members: [Dropdown of direct reports only]
├─ Department: [Disabled - Shows only their dept]
└─ Note: "You can only review KRAs for your direct reports"
```

**For Staff (Level <60):**
```
❌ NO ACCESS (403 Error) - Single Authority enforcement
```

**WVV Logic**:
- WRITE: Manager selects team members → Filter criteria stored
- VERIFY: Backend checks `reporting_manager_id` or `primary_spoc_employee_id`
- VALIDATE: Only employees with hierarchy match are returned

---

### **SECTION 3: KRA Status Filters**
**Purpose**: DC Protocol - Segment data by review lifecycle

```
📊 KRA Status (Multi-select Buttons)
├─ Completion Status:
│  ├─ [ ] Pending (not submitted yet)
│  ├─ [ ] In Progress (being worked on)
│  ├─ [ ] Completed (self-rated as done)
│  ├─ [ ] Partial (partially completed)
│  ├─ [ ] Skipped (intentionally skipped)
│  └─ [ ] NA (Not Applicable/Exempted)
│
└─ Manager Review Status:
   ├─ [ ] Pending Review ⏳ (NEW - needs action)
   ├─ [ ] Approved ✅ (already approved)
   ├─ [ ] Edited & Approved 📝 (manager edited & approved)
   └─ [ ] Rejected ❌ (sent back for revision)
```

**WVV Logic**:
- WRITE: Manager selects status checkboxes → Multiple status filter created
- VERIFY: Backend validates enum values against DB constraints
- VALIDATE: Count matching records and show in UI badges

---

### **SECTION 4: Performance & Frequency Filters**
**Purpose**: Segment by task characteristics

```
🎯 Frequency & Performance
├─ KRA Frequency: [Daily] [Weekly] [Monthly] [Quarterly] [Yearly] [All]
├─ Self Rating Range: 
│  └─ From [1⭐] To [5⭐] (Slider or Select)
└─ Manager Rating: [Not Rated] [1-2] [3] [4-5]
```

**WVV Logic**:
- WRITE: Select frequency → Filter applied to template data
- VERIFY: Backend validates frequency enum
- VALIDATE: Ensures frequency matches KRA assignment

---

### **SECTION 5: Advanced Filters (Collapsible)**
**Purpose**: Power-user filtering for deep analysis

```
🔧 Advanced Filters (Optional)
├─ Show Only Overdue KRAs
├─ Show Only High Priority (Manager Rating ≥4)
├─ Show Only With Manager Notes
├─ Instances With Completion % < 100
└─ Hide Already Processed (Not Pending)
```

---

## 🔐 ROLE-BASED FILTER VISIBILITY

| Component | VGK4U Supreme | HR/EA | Manager | Staff |
|-----------|--------------|-------|---------|-------|
| Date Range | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No Access |
| Employee Multi | ✅ All Staff | ✅ All Staff | ✅ Direct Reports Only | ❌ No Access |
| Department | ✅ All Depts | ✅ All Depts | ✅ Auto (their dept) | ❌ No Access |
| Status Filters | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No Access |
| Frequency | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No Access |
| Advanced | ✅ Yes | ✅ Yes | ⚠️ Partial | ❌ No Access |

---

## 🏗️ IMPLEMENTATION PLAN

### **Phase 1: Backend Enhancement (WVV/DC Compliant)**
**Endpoint**: Update `/api/v1/staff/kra/manager-review/pending`

**NEW FILTER PARAMETERS**:
```python
GET /api/v1/staff/kra/manager-review/pending?
    employee_id=123&                          # Single or multiple
    department_id=5&                          # Filter by department
    manager_id=45&                            # For admin viewing specific manager's team
    date_from=2025-12-01&
    date_to=2025-12-31&
    completion_status=completed,partial&     # Comma-separated
    manager_review_status=pending_review&
    frequency=daily,weekly&
    manager_rating_min=3&
    manager_rating_max=5&
    sort_by=instance_date&
    sort_order=desc
```

**WVV-DC Implementation**:
- **WRITE**: Validate all filter parameters against allowed enums
- **VERIFY**: Check user role hierarchy before applying filters
- **VALIDATE**: Ensure returned data matches user's data access level

### **Phase 2: Frontend UI Construction**
**File**: `frontend/staff_kra_review.html`

**Changes**:
1. **Expand Filter Bar** - Add collapsible sections for each filter group
2. **Add Filter State Manager** - Track all active filters
3. **Implement Filter Button Bar** - Show active filters as removable chips
4. **Update Table Display** - Add more columns (department, manager rating, etc.)
5. **Dynamic Statistics** - Update pills based on applied filters
6. **Reset Filters Button** - Clear all filters at once

### **Phase 3: Data Display & Performance**
**Optimizations**:
- Pagination: Keep 20 items per page (current)
- Lazy loading: Load departments/employees on demand
- Filter debouncing: 300ms delay on text search
- Export option: CSV/Excel export of filtered results

---

## 🔄 WVV PROTOCOL WORKFLOW

### For Each Filter Operation:

```
1️⃣ WRITE PHASE:
   └─ User selects filters → Frontend captures values
   └─ Validate filter types (date format, enum values)
   └─ Build query parameters

2️⃣ VERIFY PHASE:
   └─ Backend receives filter params
   └─ Check user's role and hierarchy level
   └─ Enforce access control (managers see only direct reports)
   └─ Validate date ranges against DB constraints

3️⃣ VALIDATE PHASE:
   └─ Execute filtered query
   └─ Count results and match to expected dataset
   └─ Return statistics with filtered count
   └─ Display results with source attribution
```

### DC Protocol Enforcement:

```
┌─ Employee Separation: All instances belong to specific employee
├─ Department Segregation: Departments auto-filtered per user role
├─ Manager Hierarchy: Managers see ONLY their reporting chain
├─ Timestamp Tracking: All filters logged with user_id + timestamp
└─ Audit Trail: All filter operations recorded in staff_kra_audit_log
```

---

## ✅ QUALITY ASSURANCE SAFEGUARDS

### Before Deployment:
1. **Zero Permission Leaks**: Verify staff cannot see other depts via URL params
2. **No Data Duplication**: Each KRA appears only once in filtered results
3. **Null Handling**: Properly handle NULL dates, departments, ratings
4. **Performance**: Filter sets <100ms for standard query
5. **Mobile Responsive**: All filters work on mobile/tablet
6. **Accessibility**: ARIA labels on all filter inputs (WCAG 2.1 AA)

### Testing Strategy:
```
✓ VGK4U Supreme: Can see all employees/depts/filters
✓ HR/EA: Can see all, limited to their dept configs
✓ Manager: Can see ONLY direct reports, date filters work
✓ Staff: Get 403 error (no access to this page at all)
```

---

## 📊 EXPECTED USER EXPERIENCE

### Scenario 1: VGK4U Supreme Reviewing Dec 1-7
```
1. Open KRA Review
2. Set Date: Dec 1-7
3. Select Department: Sales
4. Filter Status: Pending Review + Completed
5. Result: 45 KRAs matching all filters
6. Can approve/reject/edit any of them
```

### Scenario 2: Sales Manager Reviewing Team
```
1. Open KRA Review
2. Department: Auto-shows "Sales" (read-only)
3. Team Members: Shows [Emp1] [Emp2] [Emp3] [Emp4]
4. Select Date: Last 7 days
5. Result: 12 KRAs from direct reports only
6. Can approve/reject/edit any of their team's KRAs
```

---

## ⚠️ CRITICAL CONSTRAINTS

1. **DO NOT** Allow Staff access (403 error at endpoint level)
2. **DO NOT** Allow Managers to see other managers' teams
3. **DO NOT** Allow filtering by non-existent employees
4. **DO NOT** Return data that violates hierarchy rules
5. **DO NOT** Modify existing database structure
6. **DO** Maintain backward compatibility with existing code
7. **DO** Preserve all existing action buttons functionality
8. **DO** Keep performance under 500ms for all filter combinations

---

## 🚀 IMPLEMENTATION TIMELINE

**Estimated**: 1-2 hours for complete implementation

1. **Backend Filter Enhancement** (30 mins) - Add new query parameters
2. **Frontend Filter UI** (45 mins) - Build filter UI components
3. **Filter State Management** (15 mins) - Connect filters to API calls
4. **Testing & Verification** (30 mins) - Test all roles and scenarios

---

## 📝 FINAL CHECKLIST

- [ ] Backend: Add department filtering to endpoint
- [ ] Backend: Add manager_rating filters
- [ ] Backend: Add frequency multi-select support
- [ ] Frontend: Build collapsible filter sections
- [ ] Frontend: Add filter chips display
- [ ] Frontend: Connect filters to API calls
- [ ] Frontend: Update statistics based on filters
- [ ] Testing: VGK4U Supreme scenarios
- [ ] Testing: Manager team-only access
- [ ] Testing: Staff access denial
- [ ] Performance: Verify <500ms filter response

---

## ❓ QUESTIONS FOR YOUR APPROVAL

1. **Should I add an "Export Filtered Results" button** for CSV/Excel download?
2. **Should filter selections persist** when navigating away and returning?
3. **Should I add a "Saved Filters" feature** for recurring reports?
4. **Department field** - Should be single or multi-select?
5. **Performance threshold** - Is 500ms acceptable or need faster?

---

**AWAITING YOUR APPROVAL TO PROCEED** ✋

Please review this plan and confirm:
- ✅ Do you approve this filter implementation approach?
- ✅ Any changes to the filter structure?
- ✅ Ready to proceed with Phase 1 backend work?
