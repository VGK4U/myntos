# MYNTREAL ANDROID — GOOGLE PLAY STORE PUBLISHING PACKAGE

**Package Name:** `com.myntreal.mnr`  
**App Name:** `MyntReal - Workforce & CRM`  
**Target SDK:** `36` (Android 16 Ready) | **Compile SDK:** `36`  
**Version Code:** `1` | **Version Name:** `1.0`  
**Production API Base:** `https://www.myntreal.com/api/v1`  
**Organization:** `Mynt Real LLP` (GSTIN: `37ACFM9S86Q1Z0`)  

---

## 1. INCLUDED PACKAGE ARTIFACTS

1. **`mobile/`**:
   - Complete native Android project (`mobile/android/`) with Gradle configurations (`compileSdkVersion = 36`, `targetSdkVersion = 36`).
   - Web frontend SPA source & production dist synced to Android assets (`mobile/android/app/src/main/assets/public/`).
   - Capacitor container (`capacitor.config.ts`, `com.myntreal.mnr`).
   - Exported component security (`BackgroundLocationService` and `BootReceiver` marked `exported="false"`).
   - In-App Prominent Disclosures for Background Location & Call Log.
   - In-App Account Deletion flow with password verification & anonymization.
2. **`frontend/`**:
   - `privacy-policy.html`: Complete privacy policy covering staff call logs, background location, and account deletion.
   - `delete-account.html`: Public web intake portal for external account deletion requests.
3. **`backend/`**:
   - `account_deletion.py`: In-app automated deletion & anonymization, public request intake, and permanent Support ID preservation (`User.id`, `StaffEmployee.emp_code`, `OfficialPartner.partner_code`).
4. **`codemagic.yaml`**:
   - Automated cloud CI/CD pipeline for building signed release Android App Bundles (`.aab`).

---

## 2. GOOGLE PLAY STORE LISTING DETAILS

* **App Name (30 chars max):**
  `MyntReal - Workforce & CRM`

* **Short Description (80 chars max):**
  `Workforce management, field staff attendance, and CRM lead tracking for MyntReal.`

* **Full Description:**
  ```text
  MyntReal is the official workforce productivity and enterprise CRM application for MyntReal staff, sales agents, and authorized partners.

  Key Features:

  1. WORKFORCE ATTENDANCE & SHIFTS
  • Simplified clock-in and clock-out attendance tracking.
  • Working-hours location verification to record site visits and field travel mileage.
  • Automatic cessation of location tracking upon clock-out.

  2. SALES CRM & LEAD MANAGEMENT
  • Access assigned real estate, EV, and solar client leads in real time.
  • Update lead stages, add interaction notes, and schedule site follow-ups.
  • View team deal progress and status pipelines.

  3. WORKFORCE CALL ACTIVITY SYNC
  • Automatically records sales call duration and timestamps with CRM leads.
  • Matches outgoing client calls directly to CRM lead cards for transparent activity logs.
  • Eliminates manual call logging for field staff.

  4. PARTNER & FIELD OPERATIONS
  • Manage client inquiries, site visit requests, and project documentation.
  • Real-time updates on client verification and onboarding status.

  5. SECURITY & DATA PRIVACY
  • Role-based authentication ensuring staff access only authorized modules.
  • Transparent in-app controls for personal data and full account deletion support.

  Note: This application is intended for authorized MyntReal and partner workforce members. An authenticated staff or partner account is required to log in.
  ```

* **Category:** `Business` (Secondary: `Productivity`)
* **Tags:** `Workforce Management`, `CRM`, `Employee Attendance`, `Field Sales`, `Business Operations`
* **Target Audience:** `18 and older`
* **Contains Ads:** `No`
* **In-App Purchases:** `No`

---

## 3. GOOGLE PLAY SENSITIVE PERMISSION DECLARATIONS

### A. `READ_CALL_LOG` Declaration (Workforce CRM Exemption)
* **Core Functionality:** Enterprise CRM Customer Call Logging & Sales Activity Tracking.
* **Declaration Statement:**
  > "Sales representatives dial client leads directly using their mobile SIM card via the native Android phone dialer. The application reads CallLog.Calls upon call termination to capture exact call duration, timestamp, and match the client phone number with the assigned CRMLead record to auto-create sales activity notes. This cannot be accomplished via foreground UI alone because the call takes place in the native Android phone dialer. Personal calls outside CRM leads are never logged or shared."

### B. `ACCESS_BACKGROUND_LOCATION` Declaration (Staff Working-Hours Tracking)
* **Declared Feature:** `Staff Working-Hours Location Tracking`
* **Declaration Statement:**
  > "Sales and field verification employees travel between project sites throughout the working day with their phones in their pockets (app minimized or screen locked). Background location tracking records continuous route mileage for travel allowance calculation and site visit verification. Tracking is initiated only when the staff member explicitly taps Clock In (after affirmative Prominent In-App Disclosure) and ceases immediately upon Clock Out."

---

## 4. GOOGLE PLAY DATA SAFETY SUMMARY

| Data Category | Data Type | Collected | Shared | Purpose | Deletion Supported |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Personal Info** | Name, Email, Phone | Yes | No | Account management & CRM | Yes (In-App & Web) |
| **Location** | Precise & Background GPS | Yes | No | Staff attendance & travel mileage | Yes (Purged on deletion) |
| **Call Logs** | Phone number, Duration, Timestamp | Yes | No | CRM lead activity auto-matching | Yes (Disassociated on deletion) |
| **Photos** | Selfie Check-in & KYC Photo | Yes | No | Attendance identity verification | Yes (Purged on deletion) |
| **Financial Info** | Bank details, Payout history | Yes | No | Commission settlements | Anonymized (7-yr statutory ledger) |
| **Device Info** | Device Model, OS Version | Yes | No | Account security & session control | Yes |

---

## 5. PRODUCTION DEPLOYMENT PREREQUISITES

Before submitting to Google Play Console:
1. Deploy `frontend/privacy-policy.html` to `https://www.myntreal.com/privacy-policy.html`
2. Deploy `frontend/delete-account.html` to `https://www.myntreal.com/delete-account.html`
3. Provide Reviewer Demo Account in Google Play Console under **App Access**.
4. Upload Background Location demonstration video to YouTube (Unlisted) and paste the link into the Play Console Location Declaration form.

---

## 6. BUILD COMMANDS

To build the release bundle via Gradle on your build machine or CI/CD:

```bash
# 1. Build mobile web assets
cd mobile
npm install
npm run build
npx cap sync android

# 2. Build Release Android App Bundle (AAB)
cd android
./gradlew bundleRelease
```

The output signed `.aab` will be generated at:
`mobile/android/app/build/outputs/bundle/release/app-release.aab`
