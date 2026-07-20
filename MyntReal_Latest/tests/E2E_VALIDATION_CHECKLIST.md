# Real Dreams E2E Validation Checklist

**Test Company ID:** 31 (Real Dreams Test Company)  
**Login Credentials:** MR10001 / Test@123 (VGK4U Admin)

---

## Pre-Requisites

- [ ] Backend running on port 8000
- [ ] Frontend running on port 5000
- [ ] Database seeded with test data (run: `cd backend && python -m scripts.real_dreams_seed`)

---

## 1. Staff Login & Authentication

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 1.1 | Navigate to `/staff/login` | Login page displays | |
| 1.2 | Enter Employee ID: `MR10001` | Field accepts input | |
| 1.3 | Enter Password: `Test@123` | Password field accepts input | |
| 1.4 | Click Login button | Redirects to staff dashboard | |
| 1.5 | Verify header shows username | User info displayed in header | |

---

## 2. Company Selection (DC Protocol)

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 2.1 | Navigate to company selector | Company dropdown visible | |
| 2.2 | Select "Real Dreams Test Company" (ID: 31) | Company selected, data filters | |
| 2.3 | Verify company context persists | All pages show filtered data | |

---

## 3. Partner Master Configuration

**URL:** `/staff/partners/master`

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 3.1 | Navigate to Partner Master | Page loads with company dropdown | |
| 3.2 | Select test company (ID: 31) | Partners list refreshes | |
| 3.3 | Verify 3 partners visible | Premium Real Estate, Skyline Builders, PropertyFirst Agents | |
| 3.4 | Click on partner row | Partner details expand/display | |

---

## 4. Real Dreams Company Configuration

**URL:** `/rvz/real-dreams/config`

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 4.1 | Navigate to RD Config | Configuration page loads | |
| 4.2 | Verify "Real Dreams Enabled" toggle | Toggle is ON for company 31 | |
| 4.3 | Check property types list | 5 types: Residential Flat, Villa, Commercial Plot, Agricultural Land, Row House | |
| 4.4 | Check amenities list | 8 amenities: Pool, Gym, Security, Parking, Power, Play Area, Clubhouse, Garden | |

---

## 5. Real Dreams Partners

**URL:** `/rvz/real-dreams/partners`

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 5.1 | Navigate to RD Partners | Partner profiles list loads | |
| 5.2 | Filter by status "APPROVED" | Shows 1 profile (Premium Real Estate) | |
| 5.3 | Filter by status "PENDING" | Shows 1 profile (Skyline Builders) | |
| 5.4 | Filter by status "DRAFT" | Shows 1 profile (PropertyFirst Agents) | |
| 5.5 | Click View on APPROVED partner | Profile details modal opens | |
| 5.6 | Verify profile fields | Agency name, contact info, experience, specializations | |

---

## 6. Real Dreams Properties

**URL:** `/rvz/real-dreams/properties`

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 6.1 | Navigate to RD Properties | Properties list loads | |
| 6.2 | Verify 3 properties displayed | Luxury 3BHK, Modern 2BHK, Independent Villa | |
| 6.3 | Filter by status "APPROVED" | Shows 1 property (Luxury 3BHK) | |
| 6.4 | Filter by status "PENDING" | Shows 1 property (Modern 2BHK) | |
| 6.5 | Filter by status "DRAFT" | Shows 1 property (Independent Villa) | |
| 6.6 | Click View on APPROVED property | Property details modal opens | |
| 6.7 | Verify property details | Title, price, location, bedrooms, amenities, images | |
| 6.8 | Approve a PENDING property | Status changes to APPROVED | |
| 6.9 | Reject a property with reason | Status changes to REJECTED with notes | |

---

## 7. CRM/Lead Management

**URL:** `/rvz/crm/leads`

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 7.1 | Navigate to CRM Leads | Leads list loads | |
| 7.2 | Verify 3 leads displayed | Vikram Mehta, Sneha Reddy, Arjun Singh | |
| 7.3 | Filter by status "SITE_VISIT" | Shows 1 lead (Vikram Mehta) | |
| 7.4 | Filter by status "NEGOTIATION" | Shows 1 lead (Sneha Reddy) | |
| 7.5 | Filter by status "DEAL_CLOSED" | Shows 1 lead (Arjun Singh) | |
| 7.6 | Click on a lead row | Lead details expand/modal opens | |
| 7.7 | View follow-up history | Follow-up entries displayed | |
| 7.8 | Add new follow-up | Follow-up created, list refreshes | |
| 7.9 | Update lead status | Status changes, UI reflects | |
| 7.10 | Assign lead to employee | Assignment updates | |

---

## 8. Deal Management

**URL:** `/rvz/real-dreams/deals`

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 8.1 | Navigate to Deals page | Deals list loads | |
| 8.2 | Verify 1 completed deal | Rs. 1,82,00,000 deal visible | |
| 8.3 | View deal details | Buyer info, amount, commission shown | |
| 8.4 | Check commission calculation | Rs. 4,55,000 commission displayed | |

---

## 9. Public Marketplace

**URL:** `/real-dreams/marketplace`

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 9.1 | Navigate to public marketplace | Page loads without auth | |
| 9.2 | Only APPROVED properties shown | Luxury 3BHK Sea View visible | |
| 9.3 | Search/filter by location | Filter works correctly | |
| 9.4 | Click on property card | Property detail page opens | |
| 9.5 | View property gallery | Images carousel works | |
| 9.6 | Submit inquiry form | Lead created in system | |

---

## 10. Universal Engagement System

| Step | Action | Expected Result | Status |
|------|--------|-----------------|--------|
| 10.1 | Rate a property (1-5 stars) | Rating saves and displays | |
| 10.2 | Add comment on property | Comment posts, shows in list | |
| 10.3 | Reply to a comment | Thread expands correctly | |
| 10.4 | Save/bookmark property | Property added to saved list | |
| 10.5 | Share property (copy link) | Share dialog opens, link copies | |

---

## 11. API Endpoint Validation

Use browser dev tools (Network tab) or curl to validate:

**Authenticated endpoints (require staff token):**
| Endpoint | Method | Expected | Status |
|----------|--------|----------|--------|
| `/api/v1/real-dreams/config/property-types?company_id=31` | GET | 5 types | |
| `/api/v1/real-dreams/config/amenities?company_id=31` | GET | 8 amenities | |
| `/api/v1/real-dreams/partners?company_id=31` | GET | 3 profiles | |
| `/api/v1/real-dreams/properties?company_id=31` | GET | 3 properties | |

**Public endpoints (no auth required):**
| Endpoint | Method | Expected | Status |
|----------|--------|----------|--------|
| `/api/v1/real-dreams/public/properties?company_id=31` | GET | 1 approved property | |
| `/api/v1/real-dreams/public/property-types?company_id=31` | GET | 5 types | |
| `/api/v1/real-dreams/public/config?company_id=31` | GET | Config data | |

---

## 12. Data Integrity Checks

Run these SQL queries to verify data consistency:

```sql
-- Verify company configuration
SELECT * FROM rd_company_configs WHERE company_id = 31;

-- Verify property types
SELECT * FROM rd_property_types WHERE company_id = 31;

-- Verify amenities
SELECT * FROM rd_amenities WHERE company_id = 31;

-- Verify partner profiles with official partner names
SELECT pp.*, op.partner_name 
FROM rd_partner_profiles pp
JOIN official_partners op ON pp.official_partner_id = op.id
WHERE pp.company_id = 31;

-- Verify properties with amenities
SELECT p.title, p.status, COUNT(pa.amenity_id) as amenity_count
FROM rd_properties p
LEFT JOIN rd_property_amenities pa ON p.id = pa.property_id
WHERE p.company_id = 31
GROUP BY p.id, p.title, p.status;

-- Verify leads
SELECT * FROM rd_leads WHERE company_id = 31;

-- Verify deals with buyer info
SELECT d.*, l.customer_name as lead_name
FROM rd_deals d
LEFT JOIN rd_leads l ON d.lead_id = l.id
WHERE d.company_id = 31;
```

---

## Issue Tracking

| Issue # | Description | Severity | Status | Resolution |
|---------|-------------|----------|--------|------------|
| | | | | |

---

## Sign-off

- [ ] All checklist items passed
- [ ] No critical issues found
- [ ] Data integrity verified
- [ ] Ready for user acceptance testing

**Tested By:** _______________  
**Date:** _______________  
**Environment:** Development
