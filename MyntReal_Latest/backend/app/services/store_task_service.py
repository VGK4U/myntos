"""
Store Task Service — DC Protocol Compliant

Architecture:
- ONE parent StaffTask per doc_type ('po'/'pr') per company, tagged 'store-system-po'/'store-system-pr'
- Each PO raised → 1 new phase (title = PO number) added to the store PO parent task
- Each PR raised → 1 phase per category (clubbed while pending; new phase once in_progress)
- Status sync: PO/PR status changes → corresponding phase status auto-updated
- Non-editable: tasks tagged 'store-system' are read-only in task CRUD endpoints

WVV: All operations isolated in try/except — PO/PR creation NEVER fails due to this service.
DC:  company_id propagated; advisory lock not needed (append-only phases, no conflict risk).
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PO_TASK_TAG = 'store-system-po'
PR_TASK_TAG = 'store-system-pr'
SYSTEM_TAG  = 'store-system'

# ── Status mappings ──────────────────────────────────────────────────────────

PO_STATUS_TO_PHASE = {
    'confirmed':         'pending',
    'payment_pending':   'pending',
    'payment_received':  'pending',
    'accepted':          'pending',
    'hold':              'on_hold',
    'procurement':       'in_progress',
    'in_progress':       'in_progress',
    'under_procurement': 'in_progress',
    'dispatched':        'in_progress',
    'partial_dispatch':  'in_progress',
    'received':          'in_progress',
    'completed':         'completed',
    'cancelled':         'cancelled',
}

PR_STATUS_TO_PHASE = {
    'pending':               'pending',
    'confirmed':             'pending',
    'payment_received':      'pending',
    'accepted':              'pending',
    'hold':                  'on_hold',
    'procurement':           'in_progress',
    'in_progress':           'in_progress',
    'under_procurement':     'in_progress',
    'ordered':               'in_progress',
    'received':              'in_progress',
    'quality_check_pending': 'in_progress',
    'quality_confirmed':     'in_progress',
    'quality_failed':        'in_progress',
    'added_to_stock':        'completed',
    'completed':             'completed',
    'cancelled':             'cancelled',
}

# ── Internal helpers ─────────────────────────────────────────────────────────

def _find_primary_assignee(db, company_id):
    """
    Find best available assignee for store system tasks.
    Priority: Store dept active employee → EA role employee → any active employee.
    """
    from app.models.staff import StaffEmployee, StaffDepartment, StaffRole

    store_dept = db.query(StaffDepartment).filter(
        StaffDepartment.name.ilike('%store%')
    ).first()

    if store_dept:
        emp = db.query(StaffEmployee).filter(
            StaffEmployee.department_id == store_dept.id,
            StaffEmployee.status == 'active',
        ).first()
        if emp:
            return emp

    ea_role = db.query(StaffRole).filter_by(role_code='ea').first()
    if ea_role:
        emp = db.query(StaffEmployee).filter(
            StaffEmployee.role_id == ea_role.id,
            StaffEmployee.status == 'active',
        ).first()
        if emp:
            return emp

    return db.query(StaffEmployee).filter(StaffEmployee.status == 'active').first()


def _get_or_create_store_parent_task(db, doc_type, primary_emp):
    """
    Find the existing store system parent task for this doc_type, or create one.
    Uses JSONB contains filter on tags column.
    Returns StaffTask or None.
    """
    from app.models.staff_tasks import StaffTask, generate_task_code

    tag = PO_TASK_TAG if doc_type == 'po' else PR_TASK_TAG

    existing = db.query(StaffTask).filter(
        StaffTask.is_deleted == False,
        StaffTask.tags.contains([tag]),
    ).first()

    if existing:
        return existing

    if not primary_emp:
        logger.warning(f'[StoreTask] Cannot create parent task — no assignee found')
        return None

    title = 'Store \u2014 Purchase Orders' if doc_type == 'po' else 'Store \u2014 Procurement Requests'
    task_code = generate_task_code(db)

    task = StaffTask(
        task_code=task_code,
        title=title,
        description=f'System-managed task tracking all store {doc_type.upper()} lifecycle phases.',
        category='admin',
        priority='high',
        status='in_progress',
        created_by=primary_emp.id,
        primary_assignee_id=primary_emp.id,
        tags=[SYSTEM_TAG, tag],
        progress=0,
        manager_review_status='pending_review',
        is_deleted=False,
    )
    db.add(task)
    db.flush()
    logger.info(f'[StoreTask] Created store parent task {task_code} for doc_type={doc_type}')
    return task


def _next_phase_number(db, parent_task_id):
    """Return next available phase_number for this parent task."""
    from app.models.staff_tasks import StaffTaskPhase

    max_phase = db.query(StaffTaskPhase).filter(
        StaffTaskPhase.parent_task_id == parent_task_id,
        StaffTaskPhase.is_deleted == False,
    ).order_by(StaffTaskPhase.phase_number.desc()).first()

    return (max_phase.phase_number + 1) if max_phase else 1


# ── Public API ───────────────────────────────────────────────────────────────

def add_po_phase(db, po, company_id):
    """
    Called after a PO is flushed to DB.
    Adds one phase (title = PO number) to the store PO parent task.
    DC: Wrapped in try/except + begin_nested SAVEPOINT — caller is never blocked
    and the main transaction is never corrupted on inner failure.
    """
    try:
        from app.models.staff_tasks import StaffTaskPhase

        with db.begin_nested():  # SAVEPOINT: inner failure rolls back only this block
            primary_emp = _find_primary_assignee(db, company_id)
            if not primary_emp:
                logger.warning(f'[StoreTask] add_po_phase: no assignee, skipping po_id={po.id}')
                return

            parent_task = _get_or_create_store_parent_task(db, 'po', primary_emp)
            if not parent_task:
                return

            phase_num = _next_phase_number(db, parent_task.id)
            total_val = float(po.total_value or 0)
            _cust = po.customer_name or 'N/A'
            _rupee = '\u20b9'

            phase = StaffTaskPhase(
                parent_task_id=parent_task.id,
                child_task_id=None,
                phase_number=phase_num,
                phase_title=po.po_number,
                phase_description=(
                    f'[src:po:{po.id}] '
                    f'Items: {po.total_items} | '
                    f'Qty: {po.total_ordered_qty} | '
                    f'Value: {_rupee}{total_val:,.2f} | '
                    f'Customer: {_cust}'
                ),
                phase_assignee_id=primary_emp.id,
                phase_status='pending',
                ordering_token=po.id,
                created_by=primary_emp.id,
            )
            db.add(phase)
            db.flush()
            logger.info(f'[StoreTask] PO phase {phase_num} added for {po.po_number} (po_id={po.id})')

    except Exception as exc:
        logger.error(f'[StoreTask] add_po_phase failed for po_id={getattr(po, "id", None)}: {exc}')


def add_pr_phase(db, proc, company_id):
    """
    Called after a PR is flushed to DB.
    Phases are category-grouped:
      - If a pending phase already exists for this category → club (append to description).
      - Otherwise (or if category phase is in_progress/completed/cancelled) → new phase.
    DC: Wrapped in try/except + begin_nested SAVEPOINT — caller is never blocked
    and the main transaction is never corrupted on inner failure.
    """
    try:
        from app.models.staff_tasks import StaffTaskPhase
        from app.models.marketplace import MarketplacePOItem

        with db.begin_nested():  # SAVEPOINT: inner failure rolls back only this block
            # Resolve category from po_item or fallback to product name prefix
            category = None
            if proc.po_item_id:
                poi = db.query(MarketplacePOItem).filter_by(id=proc.po_item_id).first()
                if poi:
                    category = (poi.category_name or '').strip() or None
            if not category:
                category = 'Uncategorised'

            primary_emp = _find_primary_assignee(db, company_id)
            if not primary_emp:
                logger.warning(f'[StoreTask] add_pr_phase: no assignee, skipping proc_id={proc.id}')
                return

            parent_task = _get_or_create_store_parent_task(db, 'pr', primary_emp)
            if not parent_task:
                return

            # Clubbing: find existing PENDING phase for same category
            existing_phase = db.query(StaffTaskPhase).filter(
                StaffTaskPhase.parent_task_id == parent_task.id,
                StaffTaskPhase.phase_title == category,
                StaffTaskPhase.phase_status == 'pending',
                StaffTaskPhase.is_deleted == False,
            ).first()

            if existing_phase:
                # Club this PR into the existing pending phase
                suffix = (
                    f'\n[src:pr:{proc.id}] '
                    f'SKU: {proc.sku} | '
                    f'Qty: {proc.shortfall_qty} | '
                    f'{proc.product_name}'
                )
                existing_phase.phase_description = (existing_phase.phase_description or '') + suffix
                existing_phase.updated_at = datetime.utcnow()
                db.flush()
                logger.info(
                    f'[StoreTask] PR {proc.procurement_number} clubbed into '
                    f'category phase "{category}" (phase_id={existing_phase.id})'
                )
            else:
                # New phase for this category (procurement already started for existing, or first time)
                phase_num = _next_phase_number(db, parent_task.id)
                phase = StaffTaskPhase(
                    parent_task_id=parent_task.id,
                    child_task_id=None,
                    phase_number=phase_num,
                    phase_title=category,
                    phase_description=(
                        f'[src:pr:{proc.id}] '
                        f'SKU: {proc.sku} | '
                        f'Qty: {proc.shortfall_qty} | '
                        f'{proc.product_name}'
                    ),
                    phase_assignee_id=primary_emp.id,
                    phase_status='pending',
                    ordering_token=proc.id,
                    created_by=primary_emp.id,
                )
                db.add(phase)
                db.flush()
                logger.info(
                    f'[StoreTask] PR phase {phase_num} created for category '
                    f'"{category}" (proc_id={proc.id})'
                )

    except Exception as exc:
        logger.error(f'[StoreTask] add_pr_phase failed for proc_id={getattr(proc, "id", None)}: {exc}')


def sync_po_phase_status(db, po_id, new_po_status, company_id):
    """
    Sync the store PO phase status when a PO status changes.
    Finds phase by ordering_token == po_id inside the store-system-po parent task.
    DC: Wrapped in try/except — PO status update is never blocked.
    """
    try:
        from app.models.staff_tasks import StaffTask, StaffTaskPhase

        phase_status = PO_STATUS_TO_PHASE.get(new_po_status)
        if not phase_status:
            return

        parent_task = db.query(StaffTask).filter(
            StaffTask.is_deleted == False,
            StaffTask.tags.contains([PO_TASK_TAG]),
        ).first()
        if not parent_task:
            return

        phase = db.query(StaffTaskPhase).filter(
            StaffTaskPhase.parent_task_id == parent_task.id,
            StaffTaskPhase.ordering_token == po_id,
            StaffTaskPhase.is_deleted == False,
        ).first()

        if phase and phase.phase_status != phase_status:
            phase.phase_status = phase_status
            if phase_status == 'completed':
                phase.completed_at = datetime.utcnow()
            phase.updated_at = datetime.utcnow()
            db.flush()
            logger.info(f'[StoreTask] PO phase status synced to {phase_status} for po_id={po_id}')

    except Exception as exc:
        logger.error(f'[StoreTask] sync_po_phase_status failed for po_id={po_id}: {exc}')


def sync_pr_phase_status(db, proc_id, category_name, new_pr_status, company_id):
    """
    Sync the store PR category phase status when a PR status changes.
    Finds phase by ordering_token (proc_id of first PR) or by phase_title (category).
    When PR moves to 'procurement'/'in_progress' → phase becomes in_progress → clubbing stops.
    category_name may be None — the function resolves it from the PR record if needed.
    DC: Wrapped in try/except — PR status update is never blocked.
    """
    try:
        from app.models.staff_tasks import StaffTask, StaffTaskPhase

        phase_status = PR_STATUS_TO_PHASE.get(new_pr_status)
        if not phase_status:
            return

        parent_task = db.query(StaffTask).filter(
            StaffTask.is_deleted == False,
            StaffTask.tags.contains([PR_TASK_TAG]),
        ).first()
        if not parent_task:
            return

        # First try to find phase by ordering_token (exact proc match — first PR in category)
        phase = db.query(StaffTaskPhase).filter(
            StaffTaskPhase.parent_task_id == parent_task.id,
            StaffTaskPhase.ordering_token == proc_id,
            StaffTaskPhase.is_deleted == False,
        ).first()

        # If not found, resolve category_name from DB and search by phase_title
        if not phase:
            if not category_name:
                # Look up category from the procurement record's po_item
                from app.models.marketplace import MarketplaceProcurementRequest, MarketplacePOItem
                proc_obj = db.query(MarketplaceProcurementRequest).filter_by(id=proc_id).first()
                if proc_obj and proc_obj.po_item_id:
                    poi = db.query(MarketplacePOItem).filter_by(id=proc_obj.po_item_id).first()
                    if poi:
                        category_name = (poi.category_name or '').strip() or None

            if category_name:
                phase = db.query(StaffTaskPhase).filter(
                    StaffTaskPhase.parent_task_id == parent_task.id,
                    StaffTaskPhase.phase_title == category_name,
                    StaffTaskPhase.is_deleted == False,
                ).order_by(StaffTaskPhase.phase_number.desc()).first()

        if phase and phase.phase_status != phase_status:
            phase.phase_status = phase_status
            if phase_status == 'completed':
                phase.completed_at = datetime.utcnow()
            phase.updated_at = datetime.utcnow()
            db.flush()
            logger.info(
                f'[StoreTask] PR phase status synced to {phase_status} '
                f'for proc_id={proc_id} category="{category_name}"'
            )

    except Exception as exc:
        logger.error(
            f'[StoreTask] sync_pr_phase_status failed for proc_id={proc_id}: {exc}'
        )
