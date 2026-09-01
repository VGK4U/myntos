# VGK4U — AWS S3 Persistent File Storage Architecture, Audit & Zero-Loss Migration

## ROLE

Act as a senior AWS cloud architect, storage architect, backend engineer, DevOps engineer, security engineer, migration specialist, and QA engineer.

You have the complete VGK4U application context. Use the actual codebase, configuration, deployment setup, database references, existing S3 implementation, and runtime behavior as the source of truth.

**Do not hallucinate or assume. Inspect first.**

This document is specifically for the **file/document/media storage architecture**. Do not use this task as an excuse to make unrelated frontend, backend, database, authentication, or UI changes.

---

# 1. CURRENT CONTEXT

The application is currently approximately:

- Frontend: HTML/CSS/JavaScript, with Node.js involvement uncertain and requiring verification
- Backend: FastAPI / Python
- Database: PostgreSQL on AWS RDS
- Storage: AWS S3 and potentially legacy local backend storage
- Hosting: AWS Elastic Beanstalk + Docker
- Integrations: Razorpay, WhatsApp API, and any others discovered

The application contains potentially important persistent files such as:

- Solar lead documents
- PDFs
- Receipts
- Signatures
- Stamps
- Images
- Attachments
- Generated documents
- Reports
- Other uploaded/generated media

There has been a concern that files may currently be stored under something such as:

`backend/storage/`

and may therefore become part of the application/deployment filesystem or deployment ZIP.

The application also appears to have an existing S3 abstraction/service, potentially including:

`S3StorageService`

and/or:

`backend/app/services/object_storage.py`

**Do not assume this is correctly or completely wired. Audit it.**

---

# 2. FIRST ACTION — DEEP AUDIT ONLY

**DO NOT modify, delete, migrate, overwrite, rename, or clean up files yet.**

First perform a forensic audit.

Determine exactly:

1. Where every persistent file is physically stored today.
2. Whether files are stored in:
   - S3
   - `backend/storage/`
   - another local filesystem location
   - database
   - generated dynamically
   - another service
   - a hybrid of these.
3. Which code actually uploads files.
4. Which code actually downloads/views files.
5. Which code deletes/replaces files.
6. Which code generates persistent files.
7. Which frontend pages consume files.
8. Which APIs serve files.
9. Which database fields store file references.
10. Whether those references point to local paths, URLs, S3 keys, or another mechanism.

Most importantly answer, with code evidence:

> **When a user currently views or downloads a document, where is that file actually coming from? S3, backend storage, or something else?**

Do not guess.

---

# 3. DETERMINE WHETHER THE PROBLEM ACTUALLY EXISTS

The reported problem is:

- uploaded files may live in the application/server filesystem
- `backend/storage/` may be included in deployment packages
- deployment packages may become unnecessarily large
- deployments may become slower as documents accumulate
- persistent user data may be tied to an Elastic Beanstalk/EC2 instance
- scaling/replacement/redeployment may create file persistence problems

Verify each claim.

Inspect:

- `.ebignore`
- `.gitignore`
- Docker configuration
- Dockerfiles
- Elastic Beanstalk configuration
- deployment scripts
- CI/CD configuration
- build scripts
- ZIP/package creation
- `backend/storage/`
- all file-upload code
- all file-generation code
- S3 code
- environment variables
- startup scripts
- file-serving routes
- static-file configuration

Determine whether `backend/storage/` or equivalent storage is actually included in the deployment artifact.

If possible, determine the actual deployment artifact size and the contribution from persistent files.

Then explicitly report:

### Is the problem present?
YES / NO / PARTIAL

### Is it a real architectural/production concern?
YES / NO / DEPENDS

### Is S3 the correct solution?
YES / NO / BETTER ALTERNATIVE

### Is the existing S3 implementation sufficient?
YES / NO / PARTIAL

If the problem does not actually exist, say so clearly and do not perform an unnecessary migration.

---

# 4. INVENTORY EVERY FILE TYPE

Create a complete inventory.

For every persistent file category record:

| File Type | Current Source | Physical Storage | Upload Path | Retrieval Path | Delete/Replace Path | DB Reference | S3 Already Used? |
|---|---|---|---|---|---|---|---|

Include every category discovered from the codebase.

Do not rely on the examples above as the complete list.

---

# 5. INVENTORY EXISTING FILES

Before migration, determine the actual inventory from the environment/source available to you.

Measure:

- total file count
- total storage size
- file types
- paths
- object keys if already in S3
- database references
- duplicate files
- orphaned files
- missing files
- files with invalid references
- naming collisions
- files already in S3

A previously mentioned estimate was approximately **1,290 documents and 400+ MB**, but this is only a reference point.

**Do not assume those numbers are still correct. Verify them.**

---

# 6. DATABASE ↔ FILE CONSISTENCY

For every relevant database/file relationship, determine:

- database record
- file reference
- physical file/object
- expected path/key
- existence
- accessibility
- metadata where relevant

Identify:

1. DB record with a missing file
2. File with no DB record
3. Duplicate references
4. Duplicate objects
5. Broken URLs
6. Invalid paths
7. Wrong S3 keys
8. Naming collisions

Produce a reconciliation report.

---

# 7. TARGET ARCHITECTURE

If the audit confirms S3 is appropriate, target this conceptual separation:

```text
                    USERS / STAFF
                         |
                         v
                  Application/API
                         |
              +----------+----------+
              |                     |
              v                     v
       Elastic Beanstalk           S3
       Application/Runtime      Persistent Files
              |
              v
             RDS
       Structured Data
```

Conceptually:

**Elastic Beanstalk = application/code/runtime**

**RDS = structured application data**

**S3 = persistent documents/files/media**

The exact implementation must be based on the audited application.

---

# 8. EXISTING FILE MIGRATION

If migration is required, use a **zero-loss, non-destructive, idempotent, resumable** process.

Never do:

```text
copy → immediately delete originals
```

Use:

```text
Inventory
   ↓
Safety/backup check
   ↓
Upload to S3
   ↓
Verify every object
   ↓
Verify DB ↔ S3 mapping
   ↓
Test application reads/writes
   ↓
Test all file categories
   ↓
Confirm migration completeness
   ↓
Only then consider legacy cleanup
```

The migration must be safe to rerun.

It must handle:

- already migrated files
- duplicates
- collisions
- interrupted runs
- failed uploads
- partial uploads
- retries
- verification failures
- missing source files
- invalid DB references

---

# 9. FILE INTEGRITY

For migrated files, verify integrity using appropriate metadata/checksums or equivalent reliable mechanisms.

Do not consider:

> "Upload returned successfully"

as sufficient verification.

The final report must distinguish:

- discovered
- uploaded
- already present
- verified
- failed
- missing
- mismatched
- skipped

---

# 10. FUTURE UPLOADS — MANDATORY ARCHITECTURE

This rule is critical.

Once the new architecture is implemented, **the same rule must apply to every future upload**.

New persistent files must go to S3.

Desired flow:

```text
User/Staff
   ↓
Application / FastAPI
   ↓
S3
   ↓
Persistent file
```

NOT:

```text
User/Staff
   ↓
FastAPI
   ↓
backend/storage/
   ↓
Elastic Beanstalk filesystem
```

The backend may temporarily use memory or temporary filesystem storage when technically necessary for processing, but:

**Temporary files must not become the permanent storage layer and must be cleaned up after successful processing/upload.**

This must apply to:

- new uploads
- re-uploads
- replacements
- generated persistent documents
- reports
- receipts
- signatures
- stamps
- images
- attachments
- every other persistent file discovered

---

# 11. PREVENT REGRESSION TO LOCAL STORAGE

Search the entire codebase for every path/mechanism that could create permanent local file storage.

Inspect:

- `backend/storage`
- file writes
- upload handlers
- generated files
- temporary directories
- static-file configuration
- file-copy utilities
- background jobs
- scheduled jobs
- scripts
- document-generation services

Ensure future code cannot silently revert to local persistent storage.

Where appropriate, centralize storage through the existing storage abstraction/service.

---

# 12. EXISTING S3 SERVICE

Audit `S3StorageService` and/or `object_storage.py` if present.

Determine:

- whether it is used
- where it is used
- whether it is complete
- whether it supports upload
- download
- delete
- replace
- existence checks
- metadata
- correct object-key generation
- error handling
- retries
- authentication
- authorization
- private access
- signed URLs/proxy access if applicable

Prefer improving an existing sound abstraction rather than creating duplicate storage implementations.

---

# 13. FILE ACCESS AND SECURITY

Do not make the bucket public simply to make implementation easier.

Determine whether files should be:

- private
- accessed through authenticated backend endpoints
- accessed through signed URLs
- otherwise securely proxied

Preserve existing authorization.

A user/staff member who cannot access a document today must not gain access simply because the file moved to S3.

Review:

- IAM
- bucket policy
- object access
- credentials
- environment variables
- CORS where relevant
- URL exposure
- authorization
- logging
- sensitive document handling

---

# 14. FILE RETRIEVAL

Audit every existing retrieval path.

For each category determine:

```text
Frontend
  ↓
API
  ↓
FastAPI
  ↓
S3
  ↓
Object
```

or the actual architecture if different.

Ensure:

- PDF viewing works
- image viewing works
- downloads work
- previews work
- authorization works
- old references remain compatible where required
- generated URLs are correct
- MIME types are correct
- range/streaming behavior is preserved where relevant

---

# 15. DEPLOYMENT ZIP / ELASTIC BEANSTALK

After migration, ensure persistent user files are NOT unnecessarily packaged with the application deployment.

The deployment artifact should contain:

- application code
- required dependencies
- required runtime assets

It should NOT contain accumulated persistent user-uploaded files.

Verify the actual deployment package rather than assuming `.ebignore` or `.gitignore` is sufficient.

The desired conceptual result:

```text
Application deployment
→ code/runtime only

S3
→ persistent user/application files
```

---

# 16. SCALING AND INSTANCE REPLACEMENT

The architecture must not depend on a specific EC2/Elastic Beanstalk instance's local filesystem for persistent files.

The same S3 data should be accessible if:

- an instance restarts
- an instance is replaced
- Elastic Beanstalk redeploys
- multiple instances are running
- scaling occurs

Do not claim "zero data loss" without appropriate verification and AWS-level durability/backup considerations.

---

# 17. LOCAL DEVELOPMENT

Ensure the new storage architecture does not unnecessarily break local development.

Determine how local development should work.

Possible approach:

```text
Local development
→ configured S3 bucket/environment
```

or another controlled approach.

Do not introduce a hidden local-production storage fallback.

Clearly distinguish development/staging/production storage configuration.

---

# 18. ROLLBACK

Design a rollback strategy before destructive cleanup.

A rollback must explain:

- how application code can revert
- how file references remain recoverable
- how old files remain available during transition
- how S3 objects are preserved
- how local legacy storage is handled
- how failed migration is recovered

Do not delete the old storage until rollback safety is established.

---

# 19. TESTING

Test:

### Existing files
Representative files from every category.

### New uploads
New file → S3 → database/reference → retrieval.

### Download
Verify complete file download.

### Preview
Verify PDFs/images/documents.

### Replacement
Replace existing file and verify references.

### Delete
Verify deletion behavior.

### Authentication
Unauthorized users cannot access protected documents.

### Multiple users/roles
Verify correct access boundaries.

### Restart
Files remain available after application restart.

### Redeployment
Files remain available after deployment.

### Multiple instances
Files remain accessible across instances.

### Failure handling
Test:
- S3 unavailable
- missing object
- invalid key
- permission failure
- interrupted upload
- failed upload
- invalid DB reference

---

# 20. FINAL VALIDATION

Before declaring success, provide:

## Problem
Is the original storage/deployment problem actually present?

## Architecture
What was the actual architecture before and after?

## File source
Clearly state:

```text
Existing uploads → ______
Existing downloads → ______
New uploads → ______
Generated files → ______
Future persistent files → ______
```

## Migration numbers

```text
Discovered: X
Uploaded: X
Already present: X
Verified: X
Failed: X
Missing: X
Mismatched: X
```

Use real verified numbers.

## Database consistency
Explain DB ↔ file consistency.

## Deployment
Explain whether persistent files are excluded from deployment artifacts.

## Security
Explain how access is controlled.

## Tests
List tests and results.

## Remaining risks
Be honest.

## Rollback
Provide exact rollback procedure.

---

# 21. WHAT YOU NEED FROM ME

After the audit and before actions requiring my input, tell me exactly what you need from me.

Examples:

- AWS account/access
- S3 bucket information
- AWS region
- IAM permissions
- environment variables
- production/staging confirmation
- migration approval
- deployment approval
- cleanup approval
- backup confirmation
- any business decisions

Do not ask me for information that you can determine from the application.

Investigate first.

---

# 22. ABSOLUTE SAFETY RULES

- Do not delete files before verification.
- Do not overwrite production data blindly.
- Do not change database schema unnecessarily.
- Do not expose private files publicly.
- Do not silently skip migration failures.
- Do not ignore orphaned or missing files.
- Do not claim migration success without verification.
- Do not create duplicate storage systems without justification.
- Do not break existing URLs unnecessarily.
- Do not break authentication/authorization.
- Do not modify unrelated application behavior.
- Do not deploy production changes without approval.
- Do not permanently store future uploads in local application storage.

---

# 23. FIRST ACTION

**START WITH DEEP AUDIT ONLY.**

Do not modify anything.

Return:

1. Current storage architecture
2. Exact source of current files
3. All file types
4. All upload/retrieval paths
5. Existing S3 implementation assessment
6. Whether the deployment ZIP problem actually exists
7. Existing file inventory
8. DB ↔ file consistency
9. Risks
10. Recommended architecture
11. Migration plan
12. Future-upload architecture
13. Rollback plan
14. Tests required
15. What you need from me

Use actual evidence from the codebase.

Do not proceed to migration until the audit is complete and any required decisions/access from me have been identified.
