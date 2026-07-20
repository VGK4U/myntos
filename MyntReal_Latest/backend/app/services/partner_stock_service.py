"""
DC_PARTNER_STOCK_AUTOSYNC_001: Automatic partner stock synchronization.

Called from three places:
  1. Marketplace PO placed with dealer/partner code   → PURCHASE_IN
  2. Staff Sales Invoice confirmed with partner_id    → SALE_OUT
  3. Partner's own Sales Invoice confirmed            → SALE_OUT
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text as sq_text

logger = logging.getLogger(__name__)


def auto_partner_stock_sync(
    db: Session,
    partner_id: int,
    items: List[Dict[str, Any]],
    adj_type: str,
    ref_doc_type: str,
    ref_doc_id: Optional[int],
    ref_doc_number: str,
    reason: str,
    created_by: str = "system",
) -> int:
    """
    Idempotent-safe auto stock sync.  Non-fatal — never raises; logs errors.

    items keys (all optional except item_name + qty):
      item_name, item_code, stock_item_id, marketplace_sku, qty,
      unit_of_measure, selling_price, hsn_code

    adj_type: 'PURCHASE_IN' | 'SALE_OUT'
    Returns count of adjustments created.
    """
    adj_count = 0
    try:
        for item in items:
            item_name = (item.get("item_name") or "").strip()
            item_code = (item.get("item_code") or "").strip()
            stock_item_id = item.get("stock_item_id")
            marketplace_sku = (item.get("marketplace_sku") or item.get("sku") or "").strip()
            qty = float(item.get("qty", 0) or 0)
            uom = (item.get("unit_of_measure") or "PCS")[:20]
            selling_price = item.get("selling_price")
            hsn_code = (item.get("hsn_code") or "")[:20] or None

            if not item_name or qty <= 0:
                continue

            psi_id = _find_partner_stock_item(db, partner_id, stock_item_id, marketplace_sku, item_code, item_name)

            if not psi_id:
                item_type = "catalog" if stock_item_id else "marketplace" if marketplace_sku else "custom"
                row = db.execute(sq_text("""
                    INSERT INTO partner_stock_items
                        (partner_id, item_type, stock_item_id, item_name, item_code,
                         unit_of_measure, hsn_code, opening_qty, selling_price, is_active)
                    VALUES
                        (:pid, :itype, :sid, :iname, :icode,
                         :uom, :hsn, 0, :price, TRUE)
                    RETURNING id
                """), {
                    "pid": partner_id,
                    "itype": item_type,
                    "sid": stock_item_id,
                    "iname": item_name[:200],
                    "icode": (marketplace_sku or item_code or "")[:100],
                    "uom": uom,
                    "hsn": hsn_code,
                    "price": float(selling_price) if selling_price is not None else None,
                }).fetchone()
                if row:
                    psi_id = row[0]
                    db.flush()

            if not psi_id:
                logger.warning(
                    "[AUTO_STOCK_SYNC] Could not find/create stock item for "
                    f"partner={partner_id} item={item_name!r}"
                )
                continue

            db.execute(sq_text("""
                INSERT INTO partner_stock_adjustments
                    (partner_id, partner_stock_item_id, adj_type, qty, reason,
                     ref_doc_type, ref_doc_id, ref_doc_number, created_by, created_at)
                VALUES
                    (:pid, :psiid, :atype, :qty, :reason,
                     :rdtype, :rdid, :rdnum, :cby, NOW())
            """), {
                "pid": partner_id,
                "psiid": psi_id,
                "atype": adj_type,
                "qty": qty,
                "reason": (reason or "")[:200],
                "rdtype": (ref_doc_type or "")[:50],
                "rdid": ref_doc_id,
                "rdnum": (ref_doc_number or "")[:100],
                "cby": (created_by or "system")[:100],
            })
            adj_count += 1

        if adj_count:
            db.flush()
            logger.info(
                f"[AUTO_STOCK_SYNC] partner={partner_id} adj_type={adj_type} "
                f"doc={ref_doc_number} → {adj_count} adjustment(s)"
            )

    except Exception as exc:
        logger.error(f"[AUTO_STOCK_SYNC] Non-fatal error: {exc}", exc_info=True)

    return adj_count


def _find_partner_stock_item(
    db: Session,
    partner_id: int,
    stock_item_id: Optional[int],
    marketplace_sku: str,
    item_code: str,
    item_name: str,
) -> Optional[int]:
    if stock_item_id:
        row = db.execute(sq_text(
            "SELECT id FROM partner_stock_items WHERE partner_id=:pid AND stock_item_id=:sid AND is_active=TRUE"
        ), {"pid": partner_id, "sid": stock_item_id}).fetchone()
        if row:
            return row[0]

    lookup_code = marketplace_sku or item_code
    if lookup_code:
        row = db.execute(sq_text(
            "SELECT id FROM partner_stock_items WHERE partner_id=:pid AND item_code=:code AND is_active=TRUE"
        ), {"pid": partner_id, "code": lookup_code}).fetchone()
        if row:
            return row[0]

    row = db.execute(sq_text(
        "SELECT id FROM partner_stock_items WHERE partner_id=:pid AND LOWER(item_name)=LOWER(:name) AND is_active=TRUE"
    ), {"pid": partner_id, "name": item_name}).fetchone()
    return row[0] if row else None
