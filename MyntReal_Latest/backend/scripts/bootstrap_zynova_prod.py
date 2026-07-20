#!/usr/bin/env python3.11
"""
DC-VGK-INCOME-UNIFIED-001: Production Bootstrap Script
Idempotent — run against PROD_DATABASE_URL to seed all required VGK ledger
masters for Zynova (2), MNR (3), MyntReal (4), plus inter-company marketing
support ledger pairs and all schema guards.

Usage:
    PROD_DATABASE_URL=<url> python3.11 backend/scripts/bootstrap_zynova_prod.py
"""
import os
import sys
import psycopg2

SCHEMA_DDL = """
ALTER TABLE vgk_cash_income_entries
  ADD COLUMN IF NOT EXISTS kind                 VARCHAR(20) NOT NULL DEFAULT 'COMMISSION',
  ADD COLUMN IF NOT EXISTS paid_by_id           INTEGER,
  ADD COLUMN IF NOT EXISTS paid_at              TIMESTAMP,
  ADD COLUMN IF NOT EXISTS payment_utr          VARCHAR(80),
  ADD COLUMN IF NOT EXISTS payment_mode         VARCHAR(20),
  ADD COLUMN IF NOT EXISTS paid_bank_ledger_id  INTEGER,
  ADD COLUMN IF NOT EXISTS paid_cash_staff_id   INTEGER,
  ADD COLUMN IF NOT EXISTS skip_reason          TEXT,
  ADD COLUMN IF NOT EXISTS ledger_posted        BOOLEAN NOT NULL DEFAULT FALSE;
"""

DROP_CONSTRAINTS = [
    "ALTER TABLE vgk_cash_income_entries DROP CONSTRAINT IF EXISTS vgk_cash_income_status_check",
    "ALTER TABLE vgk_cash_income_entries DROP CONSTRAINT IF EXISTS vgk_cash_income_kind_check",
    "ALTER TABLE vgk_cash_income_entries DROP CONSTRAINT IF EXISTS vgk_cash_income_paymode_check",
]
ADD_CONSTRAINTS = [
    "ALTER TABLE vgk_cash_income_entries ADD CONSTRAINT vgk_cash_income_status_check  CHECK (status IN ('DRAFT','PENDING','RELEASED','PAID','CANCELLED'))",
    "ALTER TABLE vgk_cash_income_entries ADD CONSTRAINT vgk_cash_income_kind_check    CHECK (kind IN ('COMMISSION','ADVANCE'))",
    "ALTER TABLE vgk_cash_income_entries ADD CONSTRAINT vgk_cash_income_paymode_check CHECK (payment_mode IS NULL OR payment_mode IN ('BANK','CASH'))",
]
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_vci_co_kind_status ON vgk_cash_income_entries (company_id, kind, status)",
    "CREATE INDEX IF NOT EXISTS idx_vci_co_status_paid  ON vgk_cash_income_entries (company_id, status, paid_at)",
]

VGK_LEDGERS = [
    ('ASSET',     'CGST Input',                          'GST-CGI',      'Current Assets/Tax Assets',                   'CGST input tax credit'),
    ('ASSET',     'SGST Input',                          'GST-SGI',      'Current Assets/Tax Assets',                   'SGST input tax credit'),
    ('ASSET',     'IGST Input',                          'GST-IGI',      'Current Assets/Tax Assets',                   'IGST input tax credit'),
    ('ASSET',     'Loans & Advances',                    'LA-MISC',      'Current Assets/Loans & Advances (Asset)',      'General loans and advances'),
    ('ASSET',     'Commission Advance to Members',       'VCI-ADV',      'Current Assets/Loans & Advances (Asset)',      'Solar CIBIL & welcome advance to VGK members'),
    ('ASSET',     'TDS Receivable \u2014 Member Commissions', 'VCI-TDS-REC', 'Current Assets/Loans & Advances (Asset)', 'TDS withheld on member commission payouts'),
    ('LIABILITY', 'CGST Output',                         'GST-CGO',      'Current Liabilities/Duties & Taxes',          'CGST output tax liability'),
    ('LIABILITY', 'SGST Output',                         'GST-SGO',      'Current Liabilities/Duties & Taxes',          'SGST output tax liability'),
    ('LIABILITY', 'IGST Output',                         'GST-IGO',      'Current Liabilities/Duties & Taxes',          'IGST output tax liability'),
    ('LIABILITY', 'TDS Payable',                         'TDS-PAY',      'Current Liabilities/Duties & Taxes',          'TDS payable to government'),
    ('LIABILITY', 'Commission Payable to Members',       'VCI-PAY',      'Current Liabilities/Provisions',              'Net commission payable to VGK members'),
    ('LIABILITY', 'TDS Payable on Member Commission',    'VCI-TDS-PAY',  'Current Liabilities/Duties & Taxes',          'TDS withheld @ 2% on member commission'),
    ('INCOME',    'Commission Income \u2014 VGK',        'VCI-INC',      'Income/Commission Income',                    'VGK programme commission income'),
    ('INCOME',    'Admin Charges Recovery',              'VCI-ADM',      'Income/Other Income',                         'Admin charges 8% recovered from member commission'),
    ('EXPENSE',   'Commission Expense',                  'VCI-EXP',      'Expenses/Indirect Expenses',                  'Gross commission expense to VGK members'),
]

TARGET_CO_KEYWORDS = ('zynova', 'mnr', 'mega natural', 'myntreal')


def seed_ledgers(cur, target_companies, all_company_map):
    inserted = 0

    for (cid, cname) in target_companies:
        for (acct_type, acct_name, acct_code, parent_group, desc) in VGK_LEDGERS:
            cur.execute("""
                INSERT INTO account_ledger_masters
                  (company_id, account_type, account_name, account_code, parent_group,
                   description, opening_balance, opening_balance_type, is_active, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,0,'DEBIT',TRUE,NOW(),NOW())
                ON CONFLICT (company_id, account_type, account_name) DO NOTHING
            """, (cid, acct_type, acct_name, f'{acct_code}-{cid}', parent_group, desc))
            inserted += cur.rowcount
        print(f'     ✓ co#{cid} ({cname}): core + GST ledgers processed')

    for (prod_id, prod_name) in target_companies:
        for (mem_id, mem_name) in target_companies:
            if prod_id == mem_id:
                continue
            cur.execute("""
                INSERT INTO account_ledger_masters
                  (company_id, account_type, account_name, account_code, parent_group,
                   description, opening_balance, opening_balance_type, is_active, created_at, updated_at)
                VALUES (%s,'LIABILITY',%s,%s,'Current Liabilities/Provisions',%s,0,'DEBIT',TRUE,NOW(),NOW())
                ON CONFLICT (company_id, account_type, account_name) DO NOTHING
            """, (
                prod_id,
                f'Marketing Support Payable \u2014 {mem_name}',
                f'MSP-{mem_id}',
                f'Marketing support fee payable to {mem_name} (VGK commission channel)',
            ))
            inserted += cur.rowcount
            cur.execute("""
                INSERT INTO account_ledger_masters
                  (company_id, account_type, account_name, account_code, parent_group,
                   description, opening_balance, opening_balance_type, is_active, created_at, updated_at)
                VALUES (%s,'ASSET',%s,%s,'Current Assets/Loans & Advances (Asset)',%s,0,'DEBIT',TRUE,NOW(),NOW())
                ON CONFLICT (company_id, account_type, account_name) DO NOTHING
            """, (
                mem_id,
                f'Marketing Support Receivable \u2014 {prod_name}',
                f'MSR-{prod_id}',
                f'Marketing support fee receivable from {prod_name} (VGK commission channel)',
            ))
            inserted += cur.rowcount

    return inserted


def verify(cur, target_companies):
    for (cid, cname) in target_companies:
        cur.execute("""
            SELECT COUNT(*) FROM account_ledger_masters
            WHERE company_id=%s AND (
              account_name IN (
                'Commission Advance to Members','Commission Payable to Members',
                'TDS Payable on Member Commission','Admin Charges Recovery',
                'Commission Expense','Commission Income \u2014 VGK',
                'TDS Receivable \u2014 Member Commissions',
                'CGST Input','SGST Input','CGST Output','SGST Output'
              )
            )
        """, (cid,))
        n = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM account_ledger_masters WHERE company_id=%s AND account_name LIKE 'Marketing Support%%'", (cid,))
        ms = cur.fetchone()[0]
        print(f'     co#{cid} ({cname}): {n}/11 VGK ledgers ✓  |  {ms} inter-company pairs')


def main():
    db_url = os.environ.get('PROD_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not db_url:
        print('ERROR: PROD_DATABASE_URL not set', file=sys.stderr)
        sys.exit(2)

    print('=== DC-VGK-INCOME-UNIFIED-001 Production Bootstrap ===')
    print(f'    DB: {db_url[:50]}...')

    conn = psycopg2.connect(db_url, connect_timeout=10)
    conn.autocommit = False
    cur = conn.cursor()

    print('[1/4] Schema guards (ADD COLUMN IF NOT EXISTS, constraints, indexes)...')
    cur.execute(SCHEMA_DDL)
    for sql in DROP_CONSTRAINTS + ADD_CONSTRAINTS + INDEXES:
        cur.execute(sql)
    conn.commit()
    print('      schema OK')

    print('[2/4] Resolving target companies...')
    cur.execute("SELECT id, company_name FROM associated_companies ORDER BY id")
    all_rows = cur.fetchall()
    all_map  = {cid: name for cid, name in all_rows}
    targets  = [(cid, name) for cid, name in all_rows
                if any(kw in (name or '').lower() for kw in TARGET_CO_KEYWORDS)]
    for cid, name in all_rows:
        mark = '✓' if any(kw in (name or '').lower() for kw in TARGET_CO_KEYWORDS) else ' '
        print(f'      {mark} #{cid}: {name}')
    if not targets:
        print('ERROR: No target companies matched — aborting', file=sys.stderr)
        sys.exit(3)

    print('[3/4] Seeding ledgers (idempotent)...')
    n = seed_ledgers(cur, targets, all_map)
    conn.commit()
    print(f'      {n} new rows inserted (existing rows untouched)')

    print('[4/4] Verification...')
    verify(cur, targets)

    cur.close()
    conn.close()
    print('\n=== Bootstrap complete ===')


if __name__ == '__main__':
    main()
