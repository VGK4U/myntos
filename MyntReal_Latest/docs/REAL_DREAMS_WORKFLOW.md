# Real Dreams - Complete End-to-End Workflow

## Overview
Real Dreams is a comprehensive Real Estate marketplace module within the MNR Reference Program. It enables property listings, partner management, and property sales with role-based access control (RBAC), multi-company data segregation (DC Protocol), and staff token-based authentication (WVV Protocol).

---

## 1. System Architecture

### 1.1 Key Models
| Model | Purpose | Table |
|-------|---------|-------|
| `RDCompanyConfig` | Company-wise Real Dreams configuration | `rd_company_config` |
| `RDPartnerProfile` | Real Dreams partner profiles (extends OfficialPartner) | `rd_partner_profiles` |
| `RDProperty` | Property listings | `rd_properties` |
| `RDPropertyType` | Property type configuration | `rd_property_types` |
| `RDAmenity` | Amenities configuration | `rd_amenities` |
| `RDPropertyAudit` | Audit trail for property status changes | `rd_property_audit` |

### 1.2 User Roles
| Role | Access Level | Capabilities |
|------|--------------|--------------|
| **RVZ Supreme Admin** | Full Access | Enable/disable Real Dreams, approve/reject partners & properties, manage configurations |
| **VGK4U Admin** | Administrative | Manage partners, approve/reject properties, view all data |
| **Staff/Employee** | Limited | Create properties on behalf of company, view assigned properties |
| **Real Dream Partner** | Partner Portal | List properties, manage own listings, view own data |
| **MNR User** | Public Access | View approved properties, contact partners |

---

## 2. Partner Registration Workflow

### 2.1 Phase 1: Official Partner Creation

**Route:** `/staff/partners/master`  
**Role:** VGK4U Admin, RVZ Admin, Staff with hierarchy >= 85

```
┌─────────────────────────────────────────────────────────────┐
│                    PARTNER MASTER                            │
├─────────────────────────────────────────────────────────────┤
│  Categories: ALL | DEALER | DISTRIBUTOR | VENDOR |          │
│              REAL_DREAM_PARTNER                              │
└─────────────────────────────────────────────────────────────┘
```

**Steps:**
1. Navigate to Partner Master (`/staff/partners/master`)
2. Click "Add Partner" button
3. Select category: **REAL_DREAM_PARTNER**
4. Fill required fields:
   - Partner Code (auto-generated or manual)
   - Partner Name
   - Contact Person
   - Phone (10 digits validation)
   - Email (regex validation)
   - GST Number (15 chars)
   - PAN Number (AAAAA9999A format)
   - Address, City, State, Pincode
5. For REAL_DREAM_PARTNER, additional vendor-specific fields:
   - Partner Type (SALES/SERVICE/BOTH)
   - Additional Contacts (1 & 2)
   - Map Links (Office/Warehouse)
   - Bank Details
6. Select Company Segments
7. Submit

**Backend Flow:**
```
POST /api/v1/partner/partners
├── Validate partner code uniqueness
├── Create OfficialPartner record
├── Create PartnerCompanySegment records
├── IF category == REAL_DREAM_PARTNER:
│   └── Auto-create RDPartnerProfile with status='DRAFT'
└── Return success with partner details
```

### 2.2 Phase 2: Real Dreams Partner Profile

**Route:** `/rvz/real-dreams/partners`  
**Role:** RVZ Admin, VGK4U Admin

```
┌─────────────────────────────────────────────────────────────┐
│              REAL DREAMS PARTNER PROFILES                    │
├─────────────────────────────────────────────────────────────┤
│  Stats: Total Partners | Draft | Pending | Approved          │
├─────────────────────────────────────────────────────────────┤
│  Actions: Register Partner | View | Edit | Approve/Reject    │
└─────────────────────────────────────────────────────────────┘
```

**Partner Registration Steps:**
1. Click "Register Partner" button
2. Select Official Partner (dropdown shows unregistered partners)
3. Select Partner Type:
   - REAL_ESTATE_DEALER
   - BUILDER
   - AGENT
   - DEVELOPER
4. Add Specializations (tags)
5. Add Service Areas (tags)
6. Add RERA Registration Number (optional)
7. Submit

**Backend Flow:**
```
POST /api/v1/real-dreams/partners
├── Verify Real Dreams enabled for company
├── Verify partner not already registered
├── Create RDPartnerProfile with status='DRAFT'
└── Return success
```

### 2.3 Phase 3: Partner Profile Submission

**Partner Profile Status Lifecycle:**
```
┌──────────┐     ┌─────────┐     ┌──────────┐
│  DRAFT   │────▶│ PENDING │────▶│ APPROVED │
└──────────┘     └─────────┘     └──────────┘
                      │               ▲
                      │               │
                      ▼               │
                 ┌──────────┐        │
                 │ REJECTED │────────┘
                 └──────────┘
```

**Requirements for Submission:**
- NDA must be signed
- All required documents uploaded

**Backend Endpoints:**
```
POST /api/v1/real-dreams/partners/{profile_id}/submit
├── Verify status == 'DRAFT'
├── Verify NDA signed
├── Update status to 'PENDING'
└── Return success

POST /api/v1/real-dreams/partners/{profile_id}/approve
├── RVZ/VGK4U role required
├── Verify status == 'PENDING'
├── Update status to 'APPROVED'
├── Record reviewer info
└── Return success

POST /api/v1/real-dreams/partners/{profile_id}/reject
├── RVZ/VGK4U role required
├── Verify status == 'PENDING'
├── Require rejection notes
├── Update status to 'REJECTED'
└── Return success
```

---

## 3. Property Listing Workflow

### 3.1 Phase 1: Property Creation

**Route:** `/rvz/real-dreams/properties`  
**Role:** Staff, VGK4U Admin, RVZ Admin, Approved Partners

**Steps:**
1. Navigate to Properties page
2. Click "Add Property" button
3. Fill property details:

**Basic Information:**
- Property Type (from configured types)
- Title (min 10 characters)
- Description

**Location:**
- Address
- Landmark
- City (required)
- State
- Pincode
- Google Maps Link
- Latitude/Longitude

**Dimensions:**
- Total Area
- Area Unit (SQ_FT/SQ_M/ACRE/HECTARE)
- Built-up Area
- Carpet Area
- Facing Direction
- Floor Number / Total Floors

**Pricing:**
- Listed Price
- Price Per Unit
- Booking Amount
- Is Negotiable (yes/no)
- Price on Request (yes/no)

**Features:**
- Bedrooms
- Bathrooms
- Balconies
- Age of Property
- Possession Status
- RERA Number

**Amenities:**
- Select from configured amenities (multi-select chips)

**Media:**
- Images (JSON array)
- Video URL
- Virtual Tour URL

4. Submit

**Backend Flow:**
```
POST /api/v1/real-dreams/properties?company_id={id}
├── Verify Real Dreams enabled
├── Verify employee/partner listings allowed
├── Validate property type exists
├── Validate title length >= 10
├── Validate city required
├── Generate property code
├── Create RDProperty with status='DRAFT'
├── Link amenities
├── Create audit trail entry
└── Return success
```

### 3.2 Phase 2: Property Submission

**Property Status Lifecycle:**
```
┌──────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐
│  DRAFT   │────▶│ PENDING │────▶│ APPROVED │────▶│  SOLD  │
└──────────┘     └─────────┘     └──────────┘     └────────┘
     ▲                │               │
     │                │               ▼
     │                ▼          ┌─────────┐
     │           ┌──────────┐   │ EXPIRED │
     └───────────│ REJECTED │   └─────────┘
                 └──────────┘
```

**Submission Requirements:**
- City is required
- Price OR "Price on Request" is required

**Auto-Approval:**
- If `auto_approve_employee_properties` is enabled in company config
- Only for employee-submitted properties (not partner)

**Backend Endpoints:**
```
POST /api/v1/real-dreams/properties/{property_id}/submit?company_id={id}
├── Verify status in ['DRAFT', 'REJECTED']
├── Validate city exists
├── Validate price or price_on_request
├── Update status to 'PENDING'
├── Check auto-approval config
├── Create audit trail entry
└── Return success

POST /api/v1/real-dreams/properties/{property_id}/approve?company_id={id}
├── RVZ/Staff role required
├── Verify status == 'PENDING'
├── Update status to 'APPROVED'
├── Record approver info
├── Create audit trail entry
└── Return success

POST /api/v1/real-dreams/properties/{property_id}/reject?company_id={id}
├── RVZ/Staff role required
├── Verify status == 'PENDING'
├── Require rejection notes
├── Update status to 'REJECTED'
├── Create audit trail entry
└── Return success
```

---

## 4. Configuration Management

### 4.1 Company Configuration

**Route:** `/rvz/real-dreams` (Dashboard)

**Settings:**
| Setting | Description | Default |
|---------|-------------|---------|
| `is_enabled` | Enable/disable Real Dreams for company | false |
| `allow_partner_listings` | Allow partners to list properties | true |
| `allow_employee_listings` | Allow employees to list properties | true |
| `auto_approve_employee_properties` | Auto-approve employee submissions | false |

### 4.2 Property Types Configuration

**Seed Default Types:**
- Residential Apartment
- Independent House/Villa
- Commercial Shop
- Commercial Office
- Agricultural Land
- Industrial Plot
- Residential Plot

**API Endpoints:**
```
GET  /api/v1/real-dreams/config/property-types?company_id={id}
POST /api/v1/real-dreams/config/property-types
PUT  /api/v1/real-dreams/config/property-types/{type_id}
DELETE /api/v1/real-dreams/config/property-types/{type_id}
```

### 4.3 Amenities Configuration

**Seed Default Categories:**
- Basic (Electricity, Water Supply, Road Access)
- Parking (Covered Parking, Open Parking)
- Security (24/7 Security, CCTV)
- Recreation (Swimming Pool, Gym, Children's Play Area)
- Utilities (Power Backup, Sewage Treatment)

**API Endpoints:**
```
GET  /api/v1/real-dreams/config/amenities?company_id={id}
POST /api/v1/real-dreams/config/amenities
PUT  /api/v1/real-dreams/config/amenities/{amenity_id}
DELETE /api/v1/real-dreams/config/amenities/{amenity_id}
```

---

## 5. Frontend Pages

### 5.1 RVZ/Admin Pages

| Page | Route | Purpose |
|------|-------|---------|
| Real Dreams Dashboard | `/rvz/real-dreams` | Configuration, stats, property types, amenities |
| Properties Management | `/rvz/real-dreams/properties` | List, create, approve/reject properties |
| Partner Management | `/rvz/real-dreams/partners` | Register, approve/reject partners |

### 5.2 Staff Pages

| Page | Route | Purpose |
|------|-------|---------|
| Partner Master | `/staff/partners/master` | Create/manage all partner types |
| Staff Dashboard | `/staff/dashboard` | Staff overview |

### 5.3 Public Pages

| Page | Route | Purpose |
|------|-------|---------|
| Public Marketplace | `/real-dreams/marketplace` | View approved properties |
| Property Details | `/real-dreams/property/{id}` | View single property |

---

## 6. API Endpoints Summary

### 6.1 Configuration Endpoints
```
GET    /api/v1/real-dreams/config/companies
GET    /api/v1/real-dreams/dashboard/stats?company_id={id}
POST   /api/v1/real-dreams/config/enable?company_id={id}
POST   /api/v1/real-dreams/config/disable?company_id={id}
POST   /api/v1/real-dreams/config/seed-defaults?company_id={id}
```

### 6.2 Property Type Endpoints
```
GET    /api/v1/real-dreams/config/property-types?company_id={id}
POST   /api/v1/real-dreams/config/property-types
PUT    /api/v1/real-dreams/config/property-types/{type_id}
DELETE /api/v1/real-dreams/config/property-types/{type_id}
```

### 6.3 Amenity Endpoints
```
GET    /api/v1/real-dreams/config/amenities?company_id={id}
POST   /api/v1/real-dreams/config/amenities
PUT    /api/v1/real-dreams/config/amenities/{amenity_id}
DELETE /api/v1/real-dreams/config/amenities/{amenity_id}
```

### 6.4 Partner Endpoints
```
GET    /api/v1/real-dreams/partners?company_id={id}
GET    /api/v1/real-dreams/partners/available?company_id={id}
GET    /api/v1/real-dreams/partners/{profile_id}
POST   /api/v1/real-dreams/partners
PUT    /api/v1/real-dreams/partners/{profile_id}
POST   /api/v1/real-dreams/partners/{profile_id}/submit
POST   /api/v1/real-dreams/partners/{profile_id}/approve
POST   /api/v1/real-dreams/partners/{profile_id}/reject
```

### 6.5 Property Endpoints
```
GET    /api/v1/real-dreams/properties?company_id={id}
GET    /api/v1/real-dreams/properties/{property_id}
POST   /api/v1/real-dreams/properties?company_id={id}
PUT    /api/v1/real-dreams/properties/{property_id}?company_id={id}
POST   /api/v1/real-dreams/properties/{property_id}/submit?company_id={id}
POST   /api/v1/real-dreams/properties/{property_id}/approve?company_id={id}
POST   /api/v1/real-dreams/properties/{property_id}/reject?company_id={id}
```

### 6.6 Public Endpoints
```
GET    /api/v1/real-dreams/public/properties
GET    /api/v1/real-dreams/public/property/{property_id}
GET    /api/v1/real-dreams/public/property-types
```

---

## 7. DC Protocol Compliance

All endpoints enforce company-wise data segregation:

1. **Query Parameter:** `company_id` required on all requests
2. **Database Filtering:** All queries include `filter_by(company_id=company_id)`
3. **Response Isolation:** Data from one company never leaks to another
4. **Audit Trail:** All actions logged with company_id

---

## 8. WVV Protocol Compliance

Authentication flow:

1. **Staff Login:** Employee ID + Password → JWT Token
2. **Token Storage:** `localStorage.staff_token`
3. **Request Interception:** `staff-token-manager.js` adds Authorization header
4. **Token Refresh:** Auto-scheduled before expiry
5. **Session Timeout:** 15 minutes inactivity → Logout

---

## 9. Frontend Validation

### 9.1 Partner Form Validation
- **Phone:** 10 digits only
- **Email:** Valid email format
- **GST:** 15 characters (alphanumeric)
- **PAN:** Format AAAAA9999A

### 9.2 Property Form Validation
- **Title:** Minimum 10 characters
- **City:** Required field
- **Price:** Required unless "Price on Request" checked

---

## 10. Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REAL DREAMS WORKFLOW                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 1: ENABLE REAL DREAMS                                               │
│ Route: /rvz/real-dreams                                                  │
│ Action: Click "Enable Real Dreams" for company                           │
│ Result: rd_company_config created with is_enabled=true                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 2: SEED DEFAULTS                                                    │
│ Route: /rvz/real-dreams                                                  │
│ Action: Click "Seed Default Data"                                        │
│ Result: Property types & amenities created                               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 3: CREATE REAL DREAM PARTNER                                        │
│ Route: /staff/partners/master                                            │
│ Action: Add Partner with category=REAL_DREAM_PARTNER                     │
│ Result: official_partners + rd_partner_profiles (DRAFT) created          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 4: PARTNER PROFILE SETUP                                            │
│ Route: /rvz/real-dreams/partners                                         │
│ Action: Edit profile, sign NDA, upload documents                         │
│ Result: Profile ready for submission                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 5: SUBMIT PARTNER PROFILE                                           │
│ Action: Click "Submit for Review"                                        │
│ Result: Status changes DRAFT → PENDING                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 6: APPROVE PARTNER PROFILE                                          │
│ Route: /rvz/real-dreams/partners                                         │
│ Action: RVZ clicks "Approve"                                             │
│ Result: Status changes PENDING → APPROVED                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 7: CREATE PROPERTY LISTING                                          │
│ Route: /rvz/real-dreams/properties                                       │
│ Action: Click "Add Property", fill details, select amenities             │
│ Result: rd_properties created with status=DRAFT                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 8: SUBMIT PROPERTY                                                  │
│ Action: Click "Submit for Approval"                                      │
│ Result: Status changes DRAFT → PENDING                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 9: APPROVE PROPERTY                                                 │
│ Action: RVZ clicks "Approve"                                             │
│ Result: Status changes PENDING → APPROVED                                │
│         Property visible on public marketplace                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STEP 10: PROPERTY SALE                                                   │
│ Action: Mark property as SOLD                                            │
│ Result: Status changes APPROVED → SOLD                                   │
│         Property hidden from marketplace                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Files Modified (Dec 2025)

| File | Changes |
|------|---------|
| `backend/app/models/staff_accounts.py` | Added REAL_DREAM_PARTNER to PartnerCategory enum |
| `backend/app/services/partner_order_service.py` | Auto-create RDPartnerProfile when REAL_DREAM_PARTNER created |
| `backend/app/api/v1/endpoints/real_dreams.py` | Fixed `partner.mobile_1` → `partner.phone` |
| `frontend/partner_master.html` | Added REAL_DREAM_PARTNER tab, isVendorOrRealDream logic |
| `frontend/rvz_real_dreams_properties.html` | Fixed API endpoint paths |
| `frontend/rvz_real_dreams_dashboard.html` | Fixed navigation links |

---

*Document Version: 1.0*  
*Last Updated: December 9, 2025*
