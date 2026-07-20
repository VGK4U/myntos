# Real Dreams - Real Estate Marketplace

## Status: APPROVED - READY FOR DEVELOPMENT
## Last Updated: December 08, 2025

---

## Overview

Real Dreams is a Real Estate marketplace where **Official Partners (Dealers/Distributors)** and **MNR Members** can list properties (Flats, Plots, Agricultural Lands, Commercial Lands), and **any customer/MNR member** can browse and inquire. **RVZ** has ultimate approval authority.

---

## DC Protocol Integration

### Company-Wise Data Segregation
- All Real Dreams tables include `company_id` foreign key to `associated_companies`
- All queries filter by `company_id` to prevent cross-company data mixing
- RVZ access spans all companies with proper filtering

### Existing Systems Integration

| Existing Table | Real Dreams Usage |
|---------------|-------------------|
| `official_partners` | Real Estate Partners (Dealers/Distributors) - **REUSE** via `partner_id` FK |
| `user` (MNR Members) | Property listers & buyers - **REUSE** via `mnr_user_id` FK |
| `associated_companies` | Company segregation - **REUSE** via `company_id` FK |
| `staff_employees` | Approval/Assignment - **REUSE** via employee FKs |

---

## Confirmed Requirements

| Feature | Specification |
|---------|---------------|
| Display Format | Announcement-style cards with media grid |
| Images | Up to 10 per property |
| Location | Google Maps copy-paste + embedded map with navigation |
| Partner Onboarding | Links to existing OfficialPartner + Real Estate specific docs (RERA, etc.) |
| Commission | Record for now (future SFMS integration) |
| CRM/Leads | New system with employee assignment |

---

## Database Structure (DC Protocol Compliant)

### 1. rd_property_types (RVZ Configurable Master)
```sql
id SERIAL PRIMARY KEY,
company_id INT NOT NULL REFERENCES associated_companies(id),
name VARCHAR(100) NOT NULL,
slug VARCHAR(50) NOT NULL,
description TEXT,
icon VARCHAR(50),
is_active BOOLEAN DEFAULT TRUE,
display_order INT DEFAULT 0,
created_by_id INT REFERENCES staff_employees(id),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),

UNIQUE(company_id, slug)
```

### 2. rd_amenities (RVZ Master List)
```sql
id SERIAL PRIMARY KEY,
company_id INT NOT NULL REFERENCES associated_companies(id),
category VARCHAR(50) NOT NULL,  -- 'SECURITY', 'LIFESTYLE', 'UTILITIES', 'PARKING', etc.
name VARCHAR(100) NOT NULL,
icon VARCHAR(50),
is_active BOOLEAN DEFAULT TRUE,
display_order INT DEFAULT 0,
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),

UNIQUE(company_id, category, name)
```

### 3. rd_banner_config (Promotional Banner)
```sql
id SERIAL PRIMARY KEY,
company_id INT NOT NULL REFERENCES associated_companies(id),
banner_text VARCHAR(200) NOT NULL,
banner_subtext VARCHAR(300),
banner_image_url VARCHAR(500),
background_color VARCHAR(20) DEFAULT '#10B981',
text_color VARCHAR(20) DEFAULT '#FFFFFF',
offer_details TEXT,
terms_conditions TEXT,
is_active BOOLEAN DEFAULT TRUE,
created_by_id INT REFERENCES staff_employees(id),
updated_by_id INT REFERENCES staff_employees(id),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW()
```

### 4. rd_partner_profiles (Real Estate Extension for Official Partners)
```sql
id SERIAL PRIMARY KEY,
company_id INT NOT NULL REFERENCES associated_companies(id),
partner_id INT NOT NULL REFERENCES official_partners(id),  -- Links to existing partner

-- Real Estate Specific Details
partner_type VARCHAR(30) NOT NULL,  -- 'REAL_ESTATE_DEALER', 'BUILDER', 'AGENT'
specialization JSONB,  -- ['RESIDENTIAL', 'COMMERCIAL', 'AGRICULTURAL', 'PLOTS']
service_areas JSONB,  -- ['Bangalore', 'Mysore', 'Hubli']

-- Additional Documents (beyond what official_partners has)
rera_registration_number VARCHAR(50),
rera_certificate_url VARCHAR(500),
dealership_agreement_url VARCHAR(500),
rental_agreement_url VARCHAR(500),
other_documents_json JSONB,

-- NDA Signing (specific to Real Dreams)
nda_signed BOOLEAN DEFAULT FALSE,
nda_signed_at TIMESTAMP,
nda_document_url VARCHAR(500),

-- Status
status VARCHAR(30) DEFAULT 'PENDING',  -- 'DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED'
rvz_notes TEXT,
reviewed_by_id INT REFERENCES staff_employees(id),
reviewed_at TIMESTAMP,

created_by_id INT REFERENCES staff_employees(id),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),

UNIQUE(company_id, partner_id)
```

### 5. rd_properties (Property Listings)
```sql
id SERIAL PRIMARY KEY,
company_id INT NOT NULL REFERENCES associated_companies(id),
property_code VARCHAR(20) NOT NULL,  -- Auto: RD-BLR-0001

-- Lister Info (Either Partner OR MNR Member)
partner_profile_id INT REFERENCES rd_partner_profiles(id),
mnr_user_id VARCHAR(12) REFERENCES user(id),

property_type_id INT NOT NULL REFERENCES rd_property_types(id),

-- Basic Info
title VARCHAR(256) NOT NULL,
description TEXT,

-- Location (Google Maps)
address TEXT,
landmark VARCHAR(200),
city VARCHAR(100),
state VARCHAR(100),
pincode VARCHAR(10),
google_maps_link VARCHAR(500),
latitude DECIMAL(10, 8),
longitude DECIMAL(11, 8),

-- Dimensions
total_area DECIMAL(15, 2),
area_unit VARCHAR(20) DEFAULT 'SQ_FT',  -- 'SQ_FT', 'SQ_M', 'ACRES', 'GUNTHA', 'HECTARES'
length DECIMAL(10, 2),
width DECIMAL(10, 2),
built_up_area DECIMAL(15, 2),
carpet_area DECIMAL(15, 2),
plot_dimensions VARCHAR(100),
facing VARCHAR(20),  -- 'EAST', 'WEST', 'NORTH', 'SOUTH', 'NORTH_EAST', etc.
road_width VARCHAR(50),
floor_number INT,
total_floors INT,

-- Pricing
listed_price DECIMAL(15, 2),
price_per_unit DECIMAL(15, 2),
price_unit VARCHAR(20),
discount_percent DECIMAL(5, 2),
discounted_price DECIMAL(15, 2),
booking_amount DECIMAL(15, 2),
is_negotiable BOOLEAN DEFAULT FALSE,
price_on_request BOOLEAN DEFAULT FALSE,

-- Media (up to 10)
images_json JSONB,  -- [{url, caption, is_primary, order}]
video_url VARCHAR(500),
virtual_tour_url VARCHAR(500),
brochure_url VARCHAR(500),

-- Additional Details
bedrooms INT,
bathrooms INT,
balconies INT,
age_of_property VARCHAR(50),
possession_status VARCHAR(30),  -- 'READY', 'UNDER_CONSTRUCTION', 'UPCOMING'
possession_date DATE,
rera_number VARCHAR(50),

-- Status & Approval
status VARCHAR(30) DEFAULT 'DRAFT',  -- 'DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'SOLD', 'EXPIRED'
is_featured BOOLEAN DEFAULT FALSE,
is_premium BOOLEAN DEFAULT FALSE,
view_count INT DEFAULT 0,
rvz_notes TEXT,
approved_by_id INT REFERENCES staff_employees(id),
approved_at TIMESTAMP,

created_by_id INT REFERENCES staff_employees(id),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),

UNIQUE(company_id, property_code)
```

### 6. rd_property_amenities (Junction Table)
```sql
id SERIAL PRIMARY KEY,
property_id INT NOT NULL REFERENCES rd_properties(id) ON DELETE CASCADE,
amenity_id INT NOT NULL REFERENCES rd_amenities(id),
created_at TIMESTAMP DEFAULT NOW(),

UNIQUE(property_id, amenity_id)
```

### 7. rd_leads (CRM)
```sql
id SERIAL PRIMARY KEY,
company_id INT NOT NULL REFERENCES associated_companies(id),
lead_code VARCHAR(20) NOT NULL,  -- Auto: RDL-0001

property_id INT REFERENCES rd_properties(id),
partner_profile_id INT REFERENCES rd_partner_profiles(id),
assigned_to_employee_id INT REFERENCES staff_employees(id),

-- Lead Info
lead_type VARCHAR(30) NOT NULL,  -- 'PROPERTY_INQUIRY', 'GENERAL', 'PARTNER_REFERRAL'
lead_source VARCHAR(30) NOT NULL,  -- 'WEBSITE', 'WALK_IN', 'REFERRAL', 'SOCIAL_MEDIA', 'CALL', 'WHATSAPP'
lead_date DATE NOT NULL,

-- Customer Info
customer_name VARCHAR(200) NOT NULL,
mobile_1 VARCHAR(20) NOT NULL,
mobile_2 VARCHAR(20),
email VARCHAR(200),
address TEXT,
city VARCHAR(100),
state VARCHAR(100),

-- MNR Member (if inquiry from member)
mnr_user_id VARCHAR(12) REFERENCES user(id),

-- Inquiry Details
enquiry_for TEXT,
budget_min DECIMAL(15, 2),
budget_max DECIMAL(15, 2),
preferred_location VARCHAR(200),
requirements_notes TEXT,

-- Status Tracking
status VARCHAR(30) DEFAULT 'PENDING',  -- 'PENDING', 'IN_PROGRESS', 'CONTACTED', 'NEGOTIATION', 'SITE_VISIT', 'DEAL_CLOSED', 'DEAL_LOST', 'HOLD'
last_contacted_at TIMESTAMP,
last_pitch_notes TEXT,
next_followup_date DATE,
next_followup_notes TEXT,

-- Access Control
visible_to_employees_json JSONB,
visible_to_partner BOOLEAN DEFAULT FALSE,

-- Deal Info (when closed)
deal_amount DECIMAL(15, 2),
deal_notes TEXT,
deal_closed_at TIMESTAMP,

created_by_id INT REFERENCES staff_employees(id),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),

UNIQUE(company_id, lead_code)
```

### 8. rd_lead_followups (Follow-up History)
```sql
id SERIAL PRIMARY KEY,
lead_id INT NOT NULL REFERENCES rd_leads(id) ON DELETE CASCADE,
followup_date DATE NOT NULL,
followup_type VARCHAR(30) NOT NULL,  -- 'CALL', 'WHATSAPP', 'EMAIL', 'SITE_VISIT', 'MEETING'
notes TEXT,
outcome VARCHAR(50),
next_action TEXT,
created_by_id INT REFERENCES staff_employees(id),
created_at TIMESTAMP DEFAULT NOW()
```

### 9. rd_deals (Closed Deals Record)
```sql
id SERIAL PRIMARY KEY,
company_id INT NOT NULL REFERENCES associated_companies(id),
deal_code VARCHAR(20) NOT NULL,  -- Auto: RDD-0001

property_id INT NOT NULL REFERENCES rd_properties(id),
lead_id INT REFERENCES rd_leads(id),
partner_profile_id INT REFERENCES rd_partner_profiles(id),

-- Buyer Info
buyer_name VARCHAR(200) NOT NULL,
buyer_phone VARCHAR(20) NOT NULL,
buyer_email VARCHAR(200),
buyer_address TEXT,
buyer_mnr_id VARCHAR(12) REFERENCES user(id),

-- Deal Info
deal_amount DECIMAL(15, 2) NOT NULL,
booking_amount_paid DECIMAL(15, 2),
payment_mode VARCHAR(30),
deal_date DATE NOT NULL,
deal_notes TEXT,

-- Commission (for future SFMS integration)
commission_amount DECIMAL(15, 2),
commission_status VARCHAR(30) DEFAULT 'PENDING',

-- RVZ Approval
status VARCHAR(30) DEFAULT 'PENDING_RVZ',  -- 'PENDING_RVZ', 'APPROVED', 'COMPLETED', 'CANCELLED'
rvz_notes TEXT,
rvz_approved_by_id INT REFERENCES staff_employees(id),
rvz_approved_at TIMESTAMP,

-- Documents
agreement_url VARCHAR(500),
receipt_url VARCHAR(500),
other_docs_json JSONB,

created_by_id INT REFERENCES staff_employees(id),
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),

UNIQUE(company_id, deal_code)
```

---

## Frontend Pages (By Phase)

### PHASE 1: RVZ Configuration Dashboard
| Page | Purpose | Route |
|------|---------|-------|
| RVZ Dashboard | Stats overview | /rvz/real-dreams/dashboard |
| Property Types | Add/Edit/Disable property types | /rvz/real-dreams/property-types |
| Amenities | Manage amenities master list | /rvz/real-dreams/amenities |
| Banner Config | Configure promotional banner | /rvz/real-dreams/banner |

### PHASE 2: Partner Onboarding
| Page | Purpose | Route |
|------|---------|-------|
| Partner Apply | Partner application form (links to OfficialPartner + RE docs) | /real-dreams/partner/apply |
| Partner Review | Review & approve partner applications | /rvz/real-dreams/partners |
| Partner Dashboard | Partner's property management | /real-dreams/partner/dashboard |

### PHASE 3: Property Listings
| Page | Purpose | Route |
|------|---------|-------|
| List Property | Add property form (Partner/Member) | /real-dreams/list-property |
| My Listings | View my listings | /real-dreams/my-listings |
| Property Review | Approve/reject listings | /rvz/real-dreams/properties |

### PHASE 4: Public Marketplace
| Page | Purpose | Route |
|------|---------|-------|
| Browse Properties | All approved properties | /real-dreams |
| Property Detail | Detail + map + inquiry form | /real-dreams/property/{id} |

### PHASE 5: CRM & Lead Management
| Page | Purpose | Route |
|------|---------|-------|
| Lead List | Leads for sales team | /real-dreams/leads |
| Lead Detail | Lead + follow-up history | /real-dreams/leads/{id} |
| All Leads | RVZ overview | /rvz/real-dreams/leads |
| Deal Management | Deal closure | /rvz/real-dreams/deals |

---

## Property Card UI (Announcement Format)

```
+-------------------------------------------------------------+
| BOOK THIS & GET FREE E-BIKE! (Terms Apply)                  | <- Promo Banner
+-------------------------------------------------------------+
| [Main Image]                                                 |
| [Thumbnail Grid - up to 10 images]                          |
|                                                              |
| Premium 3BHK Villa with Garden                              | <- Title
| Whitefield, Bangalore, Karnataka                            | <- Location
|                                                              |
| DIMENSIONS                                                   |
| Total Area: 2,400 sq.ft | Plot: 30x40 ft                    |
| Built-up: 1,800 sq.ft | East Facing | 30ft Road             |
|                                                              |
| PRICING                                                      |
| Listed Price:      Rs 1,25,00,000                           |
| Per Sq.ft:         Rs 5,208                                 |
| Discount:          12% OFF                                   |
| YOUR PRICE:        Rs 1,10,00,000                           |
| Booking Amount:    Rs 5,00,000                              |
|                                                              |
| Pool | Parking | Gym | Garden | Gated                       | <- Amenities
|                                                              |
| [View on Google Maps]                                       |
|                                                              |
| [View Details]  [Enquire Now]  [Save]                       |
+-------------------------------------------------------------+
```

---

## Access Control (DC Protocol)

| Role | Access |
|------|--------|
| Guest | Browse marketplace, submit inquiry |
| MNR Member | Apply as partner, list properties, save favorites |
| Official Partner (RE) | Dashboard, list properties, view assigned leads |
| Sales Employee | View assigned leads, update status, add follow-ups |
| RVZ | Full access - configure, approve, assign, close deals |

---

## API Endpoints Structure

### RVZ Configuration
- `GET/POST /api/v1/real-dreams/config/property-types`
- `GET/POST /api/v1/real-dreams/config/amenities`
- `GET/PUT /api/v1/real-dreams/config/banner`

### Partner
- `POST /api/v1/real-dreams/partner/apply`
- `GET /api/v1/real-dreams/partner/profile`
- `GET/PUT /api/v1/real-dreams/rvz/partners`
- `PUT /api/v1/real-dreams/rvz/partners/{id}/approve`

### Properties
- `POST /api/v1/real-dreams/properties`
- `GET /api/v1/real-dreams/properties` (public browse)
- `GET /api/v1/real-dreams/properties/{id}`
- `PUT /api/v1/real-dreams/rvz/properties/{id}/approve`

### Leads
- `POST /api/v1/real-dreams/leads` (inquiry submission)
- `GET /api/v1/real-dreams/leads`
- `PUT /api/v1/real-dreams/leads/{id}`
- `POST /api/v1/real-dreams/leads/{id}/followups`

### Deals
- `POST /api/v1/real-dreams/deals`
- `PUT /api/v1/real-dreams/rvz/deals/{id}/approve`

---

## Development Phases

| Phase | Features | Est. Duration |
|-------|----------|---------------|
| **Phase 1** | Database + RVZ Config (Types, Amenities, Banner) | 2-3 days |
| **Phase 2** | Partner Onboarding (Apply, NDA, Approval) | 2-3 days |
| **Phase 3** | Property Listings (Add, Edit, Approve) | 3-4 days |
| **Phase 4** | Public Marketplace (Browse, Detail, Inquiry) | 2-3 days |
| **Phase 5** | CRM & Leads (Follow-ups, Deals) | 3-4 days |

**Total Estimated: 12-17 days**

---

## Integration Points

### With Official Partners (SFMS)
- `rd_partner_profiles.partner_id` -> `official_partners.id`
- Inherits: GST, PAN, bank details, contact info
- Adds: RERA, Real Estate specific docs

### With MNR Users
- `rd_properties.mnr_user_id` -> `user.id`
- `rd_leads.mnr_user_id` -> `user.id`
- `rd_deals.buyer_mnr_id` -> `user.id`

### With Staff Employees
- All approval FKs -> `staff_employees.id`
- Lead assignment -> `staff_employees.id`

### Future SFMS Integration
- Commission tracking in `rd_deals`
- Party ledger entries for deals
- Invoice generation for commissions

---

## Approval Checklist

- [x] Database structure follows DC Protocol
- [x] Integrates with existing official_partners
- [x] Links to MNR user system
- [x] Company-wise segregation on all tables
- [x] Phase-wise development order
- [x] API structure defined
- [x] Access control matrix defined

---

## Ready to Begin Phase 1
