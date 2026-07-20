---
name: Training Videos sidebar sync pattern
description: Three-layer fix required for any new staff sidebar route — registry, menu-master.js, and force-enable block
---

## The Three Layers (all three required)

### Layer 1 — MENU_MASTER (menu-master.js)
**The real root cause for missing sidebar items.** The sidebar renders from `MENU_MASTER`
(a static JS constant in `frontend/public/js/menu-master.js`), not dynamically from the API.
The JS calls `/my-menus` to get `allowedMenuPaths`, then filters MENU_MASTER items by route_path.
Any route NOT in MENU_MASTER never appears in the sidebar, even if DB grants are perfect.

→ Add to the correct section in `menu-master.js`.

### Layer 2 — Sync service (sidebar_sync_service.py)
`sync_menu_registry_sections` Step 1 blanket-deactivates all staff-scope registry rows
NOT in `SIDEBAR_ROUTE_MAPPING`. New routes added via migration (source='system') get wiped
on every subsequent startup.

→ Add to `SIDEBAR_ROUTE_MAPPING` in `backend/app/services/sidebar_sync_service.py`.

### Layer 3 — Startup force-enable (main.py)
Step 3b of sync only sets `is_default_visible=true` for `source='canonical_seed'` entries.
Migration-added routes have `source='system'` so visibility is never propagated automatically.

→ Add a post-sync block (runs EVERY startup, outside `if not _tv_done`):
```python
UPDATE staff_menu_registry SET source='canonical_seed', is_active=true WHERE route_path=...
INSERT INTO staff_menu_master ... WHERE NOT EXISTS ...
UPDATE staff_menu_master SET is_default_visible=true WHERE route_path=...
```

## Key API facts
- Sidebar gate URL: `/api/v1/staff/accounts/training/status` (staff_accounts router prefix)
- `my-menus` auto-sync: creates `StaffEmployeeMenuSettings` rows for menus with
  `is_default_visible=True` in `staff_menu_master` when they're missing for a user
- Mobile SideDrawer has its own hardcoded list in `mobile/src/components/SideDrawer.ts`

**Why:** The sidebar was designed as a static template with DB-driven access control on top.
"Dynamic" in sidebar_js means filtering a static list, not generating from DB. Future new routes
must be added to all three layers or they silently don't appear.
