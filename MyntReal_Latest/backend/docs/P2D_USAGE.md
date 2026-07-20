# p2d - Database Copy Tool

## Purpose
Copies complete database from Development to Production.

## Usage

### Step 1: Set Environment Variables
```bash
export DEV_DATABASE_URL="postgresql://user:pass@dev-host.neon.tech/dbname"
export PROD_DATABASE_URL="postgresql://user:pass@prod-host.neon.tech/dbname"
```

### Step 2: Run Script
```bash
cd backend
bash p2d.sh
```

### Step 3: Confirm
Type `YES` when prompted.

### Step 4: Restart Backend
After copy completes, restart the FastAPI Backend workflow.

## What Gets Copied
- ✅ ALL users (complete user table)
- ✅ ALL transactions (complete transaction table)
- ✅ ALL wallets (earning_wallet, withdrawable_wallet, upgrade_wallet)
- ✅ ALL awards (user_award_progress, bonanza_progress)
- ✅ ALL withdrawals (withdrawal_request table)
- ✅ ALL tables with foreign keys and constraints

## Safety Features
- Asks for confirmation before copying
- Shows file size after export
- Verifies user and transaction counts after import
- Auto-cleanup of temporary files

## Security
- ⚠️ Never commit database credentials to git
- ✅ Always use environment variables
- ✅ Rotate credentials after sharing

## Verification
Script shows:
- Users: [count]
- Transactions: [count]

Compare these with development to confirm complete copy.
