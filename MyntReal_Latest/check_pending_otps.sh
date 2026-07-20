#!/bin/bash
# Run this from Replit Shell to see all pending VGK registration OTPs
# Usage: bash check_pending_otps.sh
python3.11 -c "
import os, psycopg2
prod_url = os.environ.get('PROD_DATABASE_URL', '').rstrip('.')
conn = psycopg2.connect(prod_url)
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT phone, otp_code, created_at,
           CASE WHEN expires_at > NOW() THEN 'VALID ✅' ELSE 'EXPIRED ❌' END as status
    FROM phone_otp_verifications
    WHERE verified = FALSE
      AND created_at > NOW() - INTERVAL '24 hours'
    ORDER BY created_at DESC
\"\"\")
rows = cur.fetchall()
print(f'Pending OTPs in production: {len(rows)}')
print()
for r in rows:
    phone, otp, created, status = r
    print(f'  Phone: {phone}  |  OTP: {otp}  |  {status}  |  Requested at: {created.strftime(\"%I:%M %p\")}')
cur.close()
conn.close()
"
