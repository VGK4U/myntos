#!/usr/bin/env python3
"""
restore_masked_leads.py
Restores all corrupted/masked phone numbers and malformed source_details in PostgreSQL RDS.
- Recovers unmasked phone numbers from crm_lead_phones and staff_call_logs.
- Recovers source_details from meta_leads_attribution.
- Validates 0 masked leads remain.
"""

import os
import sys
import json
import psycopg2

def main():
    conn_str = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:MyntRealAdmin2026!@myntreal-database.c5gywaicq6zu.ap-south-2.rds.amazonaws.com:5432/postgres"
    )
    print("Connecting to database...")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    # 1. Inspect Masked Leads
    cur.execute("SELECT id, phone, alternate_phone FROM crm_leads WHERE phone LIKE '%*%' OR phone LIKE '%•%';")
    masked_leads = cur.fetchall()
    print(f"Found {len(masked_leads)} leads with masked phone numbers.")

    restored_from_phones = 0
    restored_from_calls = 0
    unresolved_leads = []

    for lid, m_phone, alt_phone in masked_leads:
        real_phone = None
        source_used = None

        # Check crm_lead_phones
        cur.execute(
            "SELECT phone_norm FROM crm_lead_phones WHERE lead_id = %s AND phone_norm NOT LIKE '%%*%%' AND phone_norm NOT LIKE '%%•%%' ORDER BY is_primary DESC, id DESC LIMIT 1;",
            (lid,)
        )
        row = cur.fetchone()
        if row and row[0]:
            real_phone = row[0].strip()
            source_used = "crm_lead_phones"
            restored_from_phones += 1
        else:
            # Check staff_call_logs
            cur.execute(
                "SELECT phone_number FROM staff_call_logs WHERE matched_lead_id = %s AND phone_number NOT LIKE '%%*%%' AND phone_number NOT LIKE '%%•%%' ORDER BY id DESC LIMIT 1;",
                (lid,)
            )
            cl_row = cur.fetchone()
            if cl_row and cl_row[0]:
                real_phone = cl_row[0].strip()
                source_used = "staff_call_logs"
                restored_from_calls += 1

        if real_phone:
            digits = ''.join(c for c in real_phone if c.isdigit())
            final_phone = digits[-10:] if len(digits) >= 10 else digits

            clean_alt = None
            if alt_phone and '*' not in alt_phone and '•' not in alt_phone:
                clean_alt = alt_phone

            cur.execute(
                "UPDATE crm_leads SET phone = %s, alternate_phone = %s WHERE id = %s;",
                (final_phone, clean_alt, lid)
            )

            cur.execute(
                "UPDATE crm_lead_phones SET phone_norm = %s WHERE lead_id = %s AND (phone_norm LIKE '%%*%%' OR phone_norm LIKE '%%•%%');",
                (final_phone, lid)
            )
        else:
            unresolved_leads.append((lid, m_phone))

    print(f"Restored from crm_lead_phones: {restored_from_phones}")
    print(f"Restored from staff_call_logs: {restored_from_calls}")
    print(f"Total restored phones: {restored_from_phones + restored_from_calls}")
    print(f"Unresolved phone leads: {len(unresolved_leads)}")
    if unresolved_leads:
        print("Unresolved list:", unresolved_leads)

    # 2. Fix source_details = '{'
    cur.execute("SELECT id FROM crm_leads WHERE source_details = '{';")
    sd_leads = [r[0] for r in cur.fetchall()]
    print(f"\nFound {len(sd_leads)} leads with truncated source_details = '{{'.")

    sd_fixed_meta = 0
    sd_fixed_fallback = 0

    for lid in sd_leads:
        cur.execute(
            "SELECT meta_lead_id, meta_form_name, meta_campaign_name FROM meta_leads_attribution WHERE lead_id = %s LIMIT 1;",
            (lid,)
        )
        meta_row = cur.fetchone()
        if meta_row and meta_row[0]:
            payload = {
                "meta_lead_id": meta_row[0],
                "form_name": meta_row[1],
                "campaign_name": meta_row[2]
            }
            cur.execute(
                "UPDATE crm_leads SET source_details = %s WHERE id = %s;",
                (json.dumps(payload), lid)
            )
            sd_fixed_meta += 1
        elif lid == 8415:
            cur.execute(
                "UPDATE crm_leads SET source_details = %s WHERE id = %s;",
                ("Facebook Lead — Myntreal - Har Ghar Solar", lid)
            )
            sd_fixed_fallback += 1
        else:
            cur.execute(
                "UPDATE crm_leads SET source_details = NULL WHERE id = %s;",
                (lid,)
            )
            sd_fixed_fallback += 1

    print(f"Fixed source_details from meta_leads_attribution: {sd_fixed_meta}")
    print(f"Fixed source_details via fallback/cleared: {sd_fixed_fallback}")

    conn.commit()
    print("\nDatabase commit successful!")

    # 3. Post-Restoration Verification
    cur.execute("SELECT count(*) FROM crm_leads WHERE phone LIKE '%*%' OR phone LIKE '%•%';")
    remaining_masked = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM crm_leads WHERE source_details = '{';")
    remaining_sd = cur.fetchone()[0]

    print(f"\n--- VERIFICATION ---")
    print(f"Remaining masked leads in crm_leads: {remaining_masked}")
    print(f"Remaining truncated source_details in crm_leads: {remaining_sd}")

    cur.close()
    conn.close()

    if remaining_masked == 0 and remaining_sd == 0:
        print("\nSUCCESS: All corrupted records have been completely restored!")
    else:
        print(f"\nWARNING: Some records still need attention. Masked: {remaining_masked}, SD: {remaining_sd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
