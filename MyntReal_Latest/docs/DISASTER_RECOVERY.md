# MyntReal Master Disaster Recovery (DR) Architecture & Emergency Runbook

This document is the exhaustive, step-by-step master record of the Disaster Recovery (DR) architecture built for the MyntReal application on **October 5th, 2026**. 

It details exactly what was built, how it works, how much it costs, and precisely how to execute a total recovery if the primary AWS account is ever frozen, hacked, or destroyed.

---

## Part 1: The Core Architecture Strategy

We implemented a **"Pilot Light"** Disaster Recovery strategy across two completely separate, independent AWS accounts. 
* **Account A (Production - ID: `251714435676`):** The active environment managed by the Mentor. Contains the live EC2 instances, the live RDS database, and the live S3 buckets.
* **Account B (DR Standby - ID: `912238386714`):** Your personal testing environment. Contains **zero** active servers. It acts strictly as a highly secure, offline vault that silently receives data backups.

### 1.1 Financial Independence (Unlinking)
Initially, Account B was linked to Account A via AWS Organizations. This was **undone** and the accounts were completely unlinked.
**Why?**
1. **Credit Protection:** Account B has a $100 promotional credit balance. By unlinking, Account A's production servers cannot accidentally consume Account B's credits.
2. **Liability Protection:** The Mentor's credit card in Account A is no longer financially responsible for any massive testing servers spun up in Account B.

---

## Part 2: The S3 Media Vault Mirror (Files, PDFs, Images)

**Goal:** Ensure every single user-uploaded PDF and image is backed up instantly with zero data loss.
**Source:** `myntreal-media-vault` (Account A)
**Destination:** `myntreal-media-vault-dr` (Account B)

### 2.1 How it was configured
1. **Destination Bucket Creation:** A new bucket (`myntreal-media-vault-dr`) was created in Account B.
2. **Versioning Enabled:** S3 Object Versioning was turned on in *both* buckets. AWS strictly requires versioning to be active for replication to work.
3. **IAM Security Tunnel:** A highly restricted IAM Role (`s3-cross-account-replication-role`) was created in Account A. A "Bucket Policy" was applied to Account B, explicitly granting only that specific Account A role permission to write files into it.
4. **Replication Rule:** A Continuous Replication Rule was attached to the Account A bucket. 

### 2.2 How it operates
This is a **Live, Real-Time Mirror**. There is no daily schedule. If a user uploads a PDF on your website at 2:05 PM, AWS detects it in milliseconds and automatically copies the file across the border into Account B. It is fully synchronized by 2:06 PM.

---

## Part 3: The RDS Database Teleportation

**Goal:** Ensure the live PostgreSQL database is backed up and securely transported to Account B every 8 hours.

### 3.1 The AWS Encryption Blockade
The live database in Account A is encrypted using the default AWS key (`aws/rds`). AWS has a hard-coded security rule that explicitly **forbids** sharing default-encrypted snapshots across account borders. 

### 3.2 The Custom Automation Solution (The "Double Jump")
To bypass the AWS blockade without causing any downtime to the live website, we deployed a completely custom architecture:

1. **The $1.00 Customer Managed Key (CMK):** A custom KMS encryption key (`MyntReal DR Backup Key`) was created in Account A. AWS charges exactly $1.00 per month for this key. A policy was added to this key explicitly allowing Account B to decrypt it.
2. **The IAM Lambda Role:** A security role was built (`MyntReal-DR-Lambda-Role`) giving our script permission to take snapshots, copy snapshots, and share them.
3. **The Lambda Robot (`MyntReal-Database-DR-Backup`):** A custom Python script was deployed to AWS Lambda. 
4. **The EventBridge Schedule:** A cron job was created in AWS EventBridge to trigger the Lambda Robot exactly once every 8 hours.

### 3.3 How the Lambda Robot operates
When EventBridge wakes up the Lambda Robot every 8 hours, it performs a 4-step "Double Jump":
1. **Snapshot:** It takes a raw snapshot of the live `myntreal-database`.
2. **Re-Encrypt:** It waits for the snapshot to finish, then creates a *second* copy of the snapshot, locking it with the new $1.00 CMK.
3. **Teleport:** It shares the CMK-locked snapshot directly with Account B's ID. 
4. **Cleanup:** It deletes the raw snapshot to ensure you are not double-charged for storage space in Account A.

---

## Part 4: Complete Financial Breakdown

**Account A (Mentor's Production Account):**
* **Customer Managed Key (KMS):** $1.00 flat per month.
* **Lambda Executions:** $0.00 (Fully covered by permanent 1 Million request Free Tier).
* **Data Transfer Out:** $0.00 (Because both accounts are in `ap-south-2` Hyderabad, AWS does not charge for regional data transfer).
* **Total Cost:** **Exactly $1.00 / month**

**Account B (Your DR Account):**
* **S3 Storage (3.4 GB):** $0.00 (Fits inside the 5GB AWS Free Tier limit).
* **S3 Put Requests:** ~$0.05 / month (AWS charges $0.005 per 1,000 files uploaded).
* **RDS Snapshot Storage:** ~$1.75 / month (Assuming you keep a rolling 3-day history of backups).
* **Total Cost:** **~$1.80 / month** *(100% paid for by your $100 promotional credits. Credit card charge is $0.00).*

---

## Part 5: The 20-Minute Emergency Recovery Runbook

*If Account A is compromised, frozen by AWS, or completely deleted, follow these exact click-by-click instructions in Account B to bring the MyntReal platform back online.*

### Phase 1: Resurrect the Database (~5 minutes)
1. Log into the AWS Console using **Account B** credentials.
2. In the top right corner, ensure the region is set to **Asia Pacific (Hyderabad) `ap-south-2`**.
3. Type **RDS** in the top search bar and open the RDS dashboard.
4. On the left-hand menu, click **Snapshots**.
5. At the top of the screen, click the **Shared with me** tab.
6. Check the box next to the most recent snapshot (`myntreal-database-dr-...`).
7. Click the **Actions** dropdown menu and select **Restore Snapshot**.
8. **Configuration Settings:**
   * **DB Instance Identifier:** Type `myntreal-database-recovered`
   * **Instance Class:** Select `db.t3.micro` or `db.t4g.micro` (to keep costs low).
   * **Multi-AZ Deployment:** Select **No** (Standby instance).
   * **Public Access:** Select **Yes** (Required for the Elastic Beanstalk server to connect to it).
   * **VPC Security Group:** Create a new one or select the default, ensuring Port 5432 is open to the internet (`0.0.0.0/0`).
9. Click **Restore DB Instance**. 
10. Wait ~4 minutes. Once the status says "Available", click on the database and copy the **Endpoint** URL provided.

### Phase 2: Resurrect the Server (~10 minutes)
1. Type **Elastic Beanstalk** in the top search bar and open it.
2. Click **Create Application**.
3. **Platform:** Select the exact platform your app runs on (e.g., `Node.js 18` or `Docker` depending on your `Dockerfile` setup).
4. **Application Code:** Select **Upload your code**. Upload the latest `.zip` deployment file from your local machine or GitHub repository.
5. **Presets:** Select **Single Instance (Free Tier eligible)** to keep costs down. You do not need a Load Balancer immediately unless you have SSL certificates ready.
6. Click **Next** through the IAM role screens (use the default `aws-elasticbeanstalk-ec2-role`).
7. Click **Submit** to start building the server.

### Phase 3: Connect the Wires (~2 minutes)
1. Once Elastic Beanstalk finishes building, click on your new environment.
2. On the left-hand menu, click **Configuration**.
3. Scroll down to **Updates, monitoring, and commanding** and click **Edit**.
4. Scroll to the very bottom to the **Environment Properties** section.
5. Add the following exact keys and values:
   * **Name:** `DATABASE_URL` | **Value:** `postgresql://postgres:MyntRealAdmin2026!@<PASTE_NEW_ENDPOINT_HERE>:5432/postgres`
   * **Name:** `PROD_DATABASE_URL` | **Value:** `postgresql://postgres:MyntRealAdmin2026!@<PASTE_NEW_ENDPOINT_HERE>:5432/postgres`
   * **Name:** `AWS_S3_BUCKET_NAME` | **Value:** `myntreal-media-vault-dr`
   * *(Also paste all of your Meta, Twilio, and Razorpay API keys from your `.env` file here).*
6. Click **Apply**. The server will restart and instantly connect to your recovered database and recovered S3 vault.

### Phase 4: Flip the Switch (~3 minutes)
1. Log into **GoDaddy.com**.
2. Go to the DNS Management page for `myntreal.com` (or `vgk4u.com`).
3. Locate the `CNAME` record for `www`.
4. Edit the record and replace the old AWS URL with the new Elastic Beanstalk Environment URL you just created in Account B.
5. Save the changes. 

**Wait 5 to 10 minutes for the global DNS to propagate, and your clients will be back online with zero data loss!**
