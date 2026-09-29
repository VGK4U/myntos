"""
Developer Seed Script for CRM Leads
Imports all 4,126 CRM leads and signup categories from database_backup (1).sql into local SQLite database (myntreal.db).
Maps production telecaller_id=25 / handler_id=25 to local dev employee ID for Ms. Anusha Moyyi (MR10022).
"""

import sys
import os

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine
from app.models.base import Base
from app.models.staff import StaffEmployee
from app.models.signup_category import SignupCategory
from app.models.crm import CRMLead
from sqlalchemy import text


def seed_crm_leads():
    print("[CRM-LEAD-SEED] Starting CRM leads import from database backup...")
    sql_file = os.path.join(backend_dir, "..", "database_backup (1).sql")
    if not os.path.exists(sql_file):
        print(f"[CRM-LEAD-SEED] ERROR: SQL backup file not found at {sql_file}")
        return

    session = SessionLocal()
    try:
        # Ensure base tables exist
        Base.metadata.create_all(bind=engine)

        # Get local Anusha employee record
        anusha_emp = session.query(StaffEmployee).filter_by(emp_code="MR10022").first()
        anusha_local_id = anusha_emp.id if anusha_emp else 1
        print(f"[CRM-LEAD-SEED] Anusha local ID: {anusha_local_id} (emp_code: MR10022)")

        def parse_table_data(table_name):
            in_table = False
            cols = []
            rows = []
            with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if f"COPY public.{table_name} (" in line:
                        in_table = True
                        cols = [c.strip(' ",\n') for c in line.split("(", 1)[1].rsplit(")", 1)[0].split(",")]
                        continue
                    if in_table:
                        if line.startswith(r"\."):
                            break
                        parts = [p.strip() for p in line.split("\t")]
                        if len(parts) >= len(cols):
                            rows.append(dict(zip(cols, parts)))
            return cols, rows

        # 1. Seed signup_categories
        _, cat_rows = parse_table_data("signup_categories")
        print(f"[CRM-LEAD-SEED] Found {len(cat_rows)} signup_categories in backup.")
        existing_cat_ids = {c.id for c in session.query(SignupCategory.id).all()}
        
        cats_to_add = []
        for r in cat_rows:
            c_id = int(r.get("id"))
            if c_id in existing_cat_ids:
                continue
            
            cat_obj = SignupCategory(
                id=c_id,
                name=r.get("name") or f"Category {c_id}",
                code=r.get("code") or f"CAT_{c_id}",
                description=None if r.get("description") == r"\N" else r.get("description"),
                is_active=str(r.get("is_active")).lower() in ('t', 'true', '1')
            )
            cats_to_add.append(cat_obj)
            existing_cat_ids.add(c_id)

        if cats_to_add:
            session.bulk_save_objects(cats_to_add)
            session.commit()
            print(f"  [+] Seeded {len(cats_to_add)} signup_categories.")
        else:
            print("  [=] signup_categories already populated.")

        # 2. Seed crm_leads
        _, lead_rows = parse_table_data("crm_leads")
        print(f"[CRM-LEAD-SEED] Found {len(lead_rows)} crm_leads in backup.")
        existing_lead_ids = {l.id for l in session.query(CRMLead.id).all()}

        leads_to_add = []
        anusha_assigned_count = 0

        for r in lead_rows:
            l_id = int(r.get("id"))
            if l_id in existing_lead_ids:
                continue

            def parse_bool(v):
                return str(v).lower() in ('t', 'true', '1')

            def parse_float(v):
                try: return float(v)
                except Exception: return 0.0

            def parse_int(v):
                try: return int(v)
                except Exception: return None

            def clean_str(v):
                return None if v == r"\N" or not v else v

            # Handle telecaller / handler mappings for Anusha (ID 25 in prod -> anusha_local_id in dev)
            prod_telecaller = clean_str(r.get("telecaller_id"))
            prod_handler = clean_str(r.get("handler_id"))

            mapped_telecaller = None
            if prod_telecaller:
                if str(prod_telecaller) == "25":
                    mapped_telecaller = str(anusha_local_id)
                    anusha_assigned_count += 1
                else:
                    mapped_telecaller = str(prod_telecaller)

            mapped_handler = None
            if prod_handler:
                if str(prod_handler) in ("25", "MR10022"):
                    mapped_handler = "MR10022"
                else:
                    mapped_handler = str(prod_handler)

            lead_item = CRMLead(
                id=l_id,
                company_id=parse_int(r.get("company_id")) or 1,
                name=clean_str(r.get("name")) or "Unnamed Lead",
                email=clean_str(r.get("email")),
                phone=clean_str(r.get("phone")),
                phone_primary_whatsapp=parse_bool(r.get("phone_primary_whatsapp")),
                alternate_phone=clean_str(r.get("alternate_phone")),
                phone_secondary_whatsapp=parse_bool(r.get("phone_secondary_whatsapp")),
                category_id=parse_int(r.get("category_id")),
                source=clean_str(r.get("source")) or "Direct",
                source_details=clean_str(r.get("source_details")),
                status=clean_str(r.get("status")) or "new",
                priority=clean_str(r.get("priority")) or "medium",
                handler_type=clean_str(r.get("handler_type")) or "unassigned",
                handler_id=mapped_handler,
                telecaller_id=mapped_telecaller,
                field_staff_id=clean_str(r.get("field_staff_id")),
                description=clean_str(r.get("description")),
                requirements=clean_str(r.get("requirements")),
                looking_for=clean_str(r.get("looking_for")),
                recent_comments=clean_str(r.get("recent_comments")),
                budget_min=parse_float(r.get("budget_min")),
                budget_max=parse_float(r.get("budget_max")),
                address=clean_str(r.get("address")),
                area=clean_str(r.get("area")),
                city=clean_str(r.get("city")),
                state=clean_str(r.get("state")),
                pincode=clean_str(r.get("pincode")),
                deal_value=parse_float(r.get("deal_value")),
                deal_value_total=parse_float(r.get("deal_value_total")),
                deal_value_excl_tax=parse_float(r.get("deal_value_excl_tax")),
                deal_tax_rate=parse_float(r.get("deal_tax_rate")),
                deal_value_received=parse_float(r.get("deal_value_received")),
                deal_value_balance=parse_float(r.get("deal_value_balance")),
                lost_reason=clean_str(r.get("lost_reason")),
                tags=clean_str(r.get("tags")),
            )
            leads_to_add.append(lead_item)
            existing_lead_ids.add(l_id)

        if leads_to_add:
            session.bulk_save_objects(leads_to_add)
            session.commit()
            print(f"  [+] Imported {len(leads_to_add)} CRM leads into SQLite!")
            print(f"  [+] {anusha_assigned_count} leads mapped directly to Ms. Anusha Moyyi (MR10022 / ID {anusha_local_id}).")
        else:
            print("  [=] crm_leads already populated.")

        print("[CRM-LEAD-SEED] CRM leads import completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"[CRM-LEAD-SEED] ERROR during CRM lead seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_crm_leads()
