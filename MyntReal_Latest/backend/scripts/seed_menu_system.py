"""
Developer Menu System Seeding Script
Populates pdf_canonical_routes, staff_menu_registry, staff_menu_master,
and staff_employee_menu_settings into local development database (myntreal.db).
"""

import sys
import os
import re

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine
from app.models.base import Base
from app.models.staff import StaffMenuMaster, StaffMenuRegistry, StaffEmployeeMenuSettings, DEFAULT_STAFF_MENUS, StaffEmployee
from sqlalchemy import text


def seed_menu_system():
    print("[MENU-SEED] Starting menu system seeding...")
    sql_file = os.path.join(backend_dir, "..", "database_backup (1).sql")
    routes_sql_file = os.path.join(backend_dir, "..", "frontend", "public", "production_canonical_routes.sql")

    session = SessionLocal()
    try:
        # Ensure base tables exist
        Base.metadata.create_all(bind=engine)

        # 0. Ensure pdf_canonical_routes table exists
        print("[MENU-SEED] Creating pdf_canonical_routes table if not present...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS pdf_canonical_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_path TEXT NOT NULL UNIQUE,
                section_id TEXT NOT NULL,
                section_title TEXT,
                section_order INTEGER DEFAULT 1,
                subsection_title TEXT,
                is_submenu BOOLEAN DEFAULT 0,
                parent_section TEXT,
                menu_name TEXT,
                menu_icon TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        session.commit()

        # Seed pdf_canonical_routes from production_canonical_routes.sql if empty
        route_cnt = session.execute(text("SELECT COUNT(*) FROM pdf_canonical_routes")).scalar()
        if route_cnt == 0 and os.path.exists(routes_sql_file):
            print(f"[MENU-SEED] Seeding pdf_canonical_routes from {routes_sql_file}...")
            with open(routes_sql_file, "r", encoding="utf-8") as f:
                sql_content = f.read()
            # Split and execute INSERT statements
            statements = [s.strip() for s in sql_content.split(";") if s.strip() and "INSERT INTO" in s]
            for stmt in statements:
                try:
                    session.execute(text(stmt))
                except Exception as ex:
                    print(f"  [!] SQL warning during route insert: {ex}")
            session.commit()
            print(f"  [+] pdf_canonical_routes count now: {session.execute(text('SELECT COUNT(*) FROM pdf_canonical_routes')).scalar()}")
        else:
            print(f"  [=] pdf_canonical_routes count: {route_cnt}")

        def parse_table_data(table_name):
            if not os.path.exists(sql_file):
                return [], []
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

        # 1. Seed staff_menu_registry from SQL backup
        _, reg_rows = parse_table_data("staff_menu_registry")
        print(f"[MENU-SEED] Found {len(reg_rows)} staff_menu_registry records in backup.")
        existing_reg_codes = {r.menu_code for r in session.query(StaffMenuRegistry.menu_code).all()}
        existing_reg_routes = {r.route_path for r in session.query(StaffMenuRegistry.route_path).filter(StaffMenuRegistry.route_path.isnot(None)).all()}
        
        reg_to_add = []
        for r in reg_rows:
            m_code = r.get("menu_code")
            r_path = None if r.get("route_path") == r"\N" else r.get("route_path")
            if not m_code or m_code in existing_reg_codes:
                continue
            if r_path and r_path in existing_reg_routes:
                continue
            
            def parse_bool(v):
                return str(v).lower() in ('t', 'true', '1')

            def parse_int(v):
                try: return int(v)
                except Exception: return 0

            reg_item = StaffMenuRegistry(
                menu_code=m_code,
                menu_name=r.get("menu_name") or m_code,
                menu_description=None if r.get("menu_description") == r"\N" else r.get("menu_description"),
                route_path=r_path or f"/staff/{m_code}",
                menu_category=None if r.get("menu_category") == r"\N" else r.get("menu_category"),
                menu_icon=None if r.get("menu_icon") == r"\N" else r.get("menu_icon"),
                display_order=parse_int(r.get("display_order")),
                audience_scope=r.get("audience_scope") if r.get("audience_scope") != r"\N" else "staff",
                is_default_visible=parse_bool(r.get("is_default_visible")),
                is_default_accessible=parse_bool(r.get("is_default_accessible")),
                is_active=parse_bool(r.get("is_active")),
                is_system_default=parse_bool(r.get("is_system_default")),
                sidebar_section=None if r.get("sidebar_section") == r"\N" else r.get("sidebar_section"),
                sidebar_section_title=None if r.get("sidebar_section_title") == r"\N" else r.get("sidebar_section_title"),
                sidebar_section_order=parse_int(r.get("sidebar_section_order")),
                menu_type=r.get("menu_type") if r.get("menu_type") != r"\N" else "STAFF",
                parent_section=None if r.get("parent_section") == r"\N" else r.get("parent_section"),
                is_submenu=parse_bool(r.get("is_submenu")),
            )
            reg_to_add.append(reg_item)
            existing_reg_codes.add(m_code)
            if r_path: existing_reg_routes.add(r_path)

        # Also seed from DEFAULT_STAFF_MENUS Python catalog
        for d_menu in DEFAULT_STAFF_MENUS:
            m_code = d_menu.get("menu_code")
            r_path = d_menu.get("route_path")
            if m_code and m_code not in existing_reg_codes and (not r_path or r_path not in existing_reg_routes):
                reg_item = StaffMenuRegistry(
                    menu_code=m_code,
                    menu_name=d_menu.get("menu_name") or m_code,
                    route_path=r_path or f"/staff/{m_code}",
                    menu_category=d_menu.get("menu_category"),
                    menu_icon=d_menu.get("menu_icon"),
                    display_order=d_menu.get("display_order", 0),
                    audience_scope=d_menu.get("audience_scope", "staff"),
                    is_default_visible=d_menu.get("is_default_visible", True),
                    is_default_accessible=d_menu.get("is_default_accessible", True),
                    is_active=True,
                    sidebar_section=d_menu.get("sidebar_section"),
                    sidebar_section_title=d_menu.get("sidebar_section_title"),
                    sidebar_section_order=d_menu.get("sidebar_section_order", 0),
                )
                reg_to_add.append(reg_item)
                existing_reg_codes.add(m_code)
                if r_path: existing_reg_routes.add(r_path)

        if reg_to_add:
            session.bulk_save_objects(reg_to_add)
            session.commit()
            print(f"  [+] Added {len(reg_to_add)} staff_menu_registry records.")
        else:
            print("  [=] staff_menu_registry already populated.")

        # 2. Seed staff_menu_master from SQL backup
        _, master_rows = parse_table_data("staff_menu_master")
        print(f"[MENU-SEED] Found {len(master_rows)} staff_menu_master records in backup.")
        existing_master_ids = {m.id for m in session.query(StaffMenuMaster.id).all()}
        existing_master_codes_by_company = {
            (m.company_id, m.menu_code) for m in session.query(StaffMenuMaster.company_id, StaffMenuMaster.menu_code).all()
        }
        
        master_to_add = []
        for m in master_rows:
            m_id = int(m.get("id"))
            if m_id in existing_master_ids:
                continue
            
            def parse_bool(v):
                return str(v).lower() in ('t', 'true', '1')

            def parse_int(v):
                try: return int(v)
                except Exception: return None

            cid = int(m.get("company_id") or 1)
            code = m.get("menu_code")
            master_item = StaffMenuMaster(
                id=m_id,
                company_id=cid,
                menu_code=code,
                menu_name=m.get("menu_name") or code,
                menu_description=None if m.get("menu_description") == r"\N" else m.get("menu_description"),
                route_path=None if m.get("route_path") == r"\N" else m.get("route_path"),
                parent_id=parse_int(m.get("parent_id")),
                menu_category=None if m.get("menu_category") == r"\N" else m.get("menu_category"),
                menu_icon=None if m.get("menu_icon") == r"\N" else m.get("menu_icon"),
                display_order=parse_int(m.get("display_order")) or 0,
                audience_scope=m.get("audience_scope") if m.get("audience_scope") != r"\N" else "staff",
                is_active=parse_bool(m.get("is_active")),
                is_default_visible=parse_bool(m.get("is_default_visible")),
                is_default_accessible=parse_bool(m.get("is_default_accessible")),
            )
            master_to_add.append(master_item)
            existing_master_ids.add(m_id)
            existing_master_codes_by_company.add((cid, code))

        # Also seed missing master menus for company_ids 1..5 from DEFAULT_STAFF_MENUS
        for cid in range(1, 6):
            for d_menu in DEFAULT_STAFF_MENUS:
                code = d_menu.get("menu_code")
                if code and (cid, code) not in existing_master_codes_by_company:
                    master_item = StaffMenuMaster(
                        company_id=cid,
                        menu_code=code,
                        menu_name=d_menu.get("menu_name") or code,
                        route_path=d_menu.get("route_path"),
                        menu_category=d_menu.get("menu_category"),
                        menu_icon=d_menu.get("menu_icon"),
                        display_order=d_menu.get("display_order", 0),
                        audience_scope=d_menu.get("audience_scope", "staff"),
                        is_active=True,
                        is_default_visible=d_menu.get("is_default_visible", True),
                        is_default_accessible=d_menu.get("is_default_accessible", True),
                    )
                    master_to_add.append(master_item)
                    existing_master_codes_by_company.add((cid, code))

        if master_to_add:
            session.bulk_save_objects(master_to_add)
            session.commit()
            print(f"  [+] Added {len(master_to_add)} staff_menu_master records.")
        else:
            print("  [=] staff_menu_master already populated.")

        # 3. Grant default menu settings for dev staff employees (MR10022, MR10001, MN10016, VIEWTEST)
        print("[MENU-SEED] Auto-granting menu settings to dev staff accounts...")
        dev_staff = session.query(StaffEmployee).all()
        all_master_menus = session.query(StaffMenuMaster).all()

        added_settings = 0
        for emp in dev_staff:
            existing_menu_ids = {
                s.menu_id for s in session.query(StaffEmployeeMenuSettings.menu_id).filter_by(employee_id=emp.id).all()
            }
            new_settings = []
            for menu in all_master_menus:
                if menu.id not in existing_menu_ids:
                    # Grant can_view=True for all active menus
                    setting = StaffEmployeeMenuSettings(
                        company_id=menu.company_id,
                        employee_id=emp.id,
                        menu_id=menu.id,
                        can_view=True,
                        can_edit=True,
                        is_overridden=False
                    )
                    new_settings.append(setting)
                    existing_menu_ids.add(menu.id)
            if new_settings:
                session.bulk_save_objects(new_settings)
                session.commit()
                added_settings += len(new_settings)
                print(f"  [+] Granted {len(new_settings)} menu settings for {emp.emp_code} ({emp.full_name})")

        print("[MENU-SEED] Menu system seeding completed successfully!")
    except Exception as e:
        session.rollback()
        print(f"[MENU-SEED] ERROR during menu seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_menu_system()
