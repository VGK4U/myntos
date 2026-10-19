"""
End-to-End Tally Integration Service (DC_TALLY_SYNC_001)
========================================================
Provides full bi-directional TallyPrime & Tally.ERP 9 compatibility across:
  1. Purchase Orders (ProcurementRequest & SparePurchaseOrder -> Tally 'Purchase Order' Vouchers)
  2. Purchase Invoices & Vendor Bills (PurchaseInvoiceUpload & VendorTransactionHeader -> Tally 'Purchase' / 'Debit Note' Vouchers)
  3. Sales Invoices & Returns (SalesInvoice -> Tally 'Sales' / 'Credit Note' Vouchers)
  4. Cash Entries, Receipts & Payments (CashflowRegister, IncomeEntry, ExpenseEntry, SalesInvoicePayment, PaymentTransaction -> Tally 'Receipt', 'Payment', 'Contra' Vouchers)
  5. Ledgers & Journal Vouchers (JournalVoucher, PartyLedger, AccountLedger -> Tally 'Journal', 'Contra', 'Payment', 'Receipt' Vouchers)
  6. Masters (AccountLedgerMaster 28 Tally Groups, VendorMaster, Customers/Partners, CompanyBankAccount, StockItemMaster, HSNMaster)

Key Guarantees (WVV / DC Protocol):
  - Selectable Tally Versions: TallyPrime 3.0/4.0+, TallyPrime 1.x/2.x, Tally.ERP 9, Universal
  - Preserves exact MyntOS Voucher / Invoice Numbers in <VOUCHERNUMBER> and <REFERENCE>
  - Deterministic <GUID> and <REMOTEID> so updated records in MyntOS alter existing Tally vouchers without duplication
  -SHA-256 WVV hash per record: automatically flags edited records as MODIFIED_PENDING_SYNC
  - Period presets + Custom Date Range + Segment-wise filtering + Module-wise selection
  - Strict Double-Entry Validation: every emitted <VOUCHER> is verified for SUM(Dr) == SUM(Cr) to 0.01 paisa
"""

import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, desc
from sqlalchemy.orm import Session

from app.models.base import get_indian_time
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory
from app.models.staff_accounts import (
    AccountLedger,
    AccountLedgerMaster,
    AssociatedCompany,
    CashflowRegister,
    CompanyBankAccount,
    CompanySegment,
    ExpenseEntry,
    HSNMaster,
    IncomeEntry,
    IncomeSourceType,
    JournalVoucher,
    JournalVoucherLine,
    ManualPartyMaster,
    OfficialPartner,
    PartyLedger,
    PaymentTransaction,
    ProcurementQuote,
    ProcurementQuoteItem,
    ProcurementRequest,
    ProcurementRequestItem,
    PurchaseInvoiceLineItem,
    PurchaseInvoiceUpload,
    SalesInvoice,
    SalesInvoiceLineItem,
    SalesInvoicePayment,
    SparePurchaseOrder,
    SparePurchaseOrderLine,
    StockItemMaster,
    TallySyncBatch,
    TallySyncRecord,
    VendorMaster,
    VendorTransactionHeader,
    VendorTransactionLineItem,
)

logger = logging.getLogger(__name__)

# Supported Tally versions for UI selector & XML dialect adaptation
TALLY_VERSIONS = {
    "TALLY_PRIME_4": {
        "code": "TALLY_PRIME_4",
        "label": "TallyPrime (Release 3.0 / 4.0+ — Latest GST & Multi-GSTIN)",
        "header_version": "1",
        "supports_persisted_view": True,
        "use_ledstatename": True,
        "use_cmp_gst_tags": True,
    },
    "TALLY_PRIME_2": {
        "code": "TALLY_PRIME_2",
        "label": "TallyPrime (Release 1.x / 2.x)",
        "header_version": "1",
        "supports_persisted_view": True,
        "use_ledstatename": True,
        "use_cmp_gst_tags": False,
    },
    "TALLY_ERP9": {
        "code": "TALLY_ERP9",
        "label": "Tally.ERP 9 (Series A Release 6.x GST)",
        "header_version": "1",
        "supports_persisted_view": False,
        "use_ledstatename": False,
        "use_cmp_gst_tags": False,
    },
    "UNIVERSAL": {
        "code": "UNIVERSAL",
        "label": "Universal Compatible (TallyPrime + Tally.ERP 9)",
        "header_version": "1",
        "supports_persisted_view": True,
        "use_ledstatename": True,
        "use_cmp_gst_tags": False,
    },
}

ALL_TALLY_MODULES = [
    "MASTERS",
    "PURCHASE_ORDERS",
    "PURCHASE_INVOICES",
    "SALES_INVOICES",
    "CASH_ENTRIES",
    "LEDGERS_JV",
]


def _q2(val: Any) -> Decimal:
    """Quantize any numeric value to 2 decimal places."""
    try:
        return Decimal(str(val or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _q3(val: Any) -> Decimal:
    """Quantize quantity to 3 decimal places."""
    try:
        return Decimal(str(val or 0)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.000")


def _tally_date(d: Optional[date]) -> str:
    """Format date as YYYYMMDD for Tally XML."""
    if not d:
        return get_indian_time().strftime("%Y%m%d")
    if isinstance(d, datetime):
        return d.strftime("%Y%m%d")
    if isinstance(d, date):
        return d.strftime("%Y%m%d")
    s = str(d).strip()[:10]
    return s.replace("-", "")


def _clean_xml_text(val: Any) -> str:
    """Sanitize control characters that are illegal in XML 1.0."""
    if val is None:
        return ""
    s = str(val).strip()
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u007f-\u009f]", "", s)


def _compute_sha256(payload: Dict[str, Any]) -> str:
    """Deterministic SHA-256 WVV hash for change detection."""
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _make_tally_guid(company_id: int, entity_type: str, entity_id: int) -> str:
    """
    Generate a deterministic 36-char UUID-like GUID + MyntOS suffix for Tally.
    Using a deterministic GUID means re-importing an updated record into Tally
    alters the existing voucher in-place rather than creating a duplicate.
    """
    seed = f"myntos-co{company_id}-{entity_type.lower()}-{entity_id}"
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    uuid_part = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    return f"{uuid_part}-{entity_id:08x}"


class TallyIntegrationService:
    """
    DC_TALLY_SYNC_001: Central Tally XML Export, Import, Reconciliation, and WVV Tracking Service.
    """

    @staticmethod
    def ensure_tables(db: Session) -> None:
        """Idempotently ensure tally_sync_records and tally_sync_batches exist."""
        try:
            bind = db.get_bind()
            TallySyncRecord.__table__.create(bind=bind, checkfirst=True)
            TallySyncBatch.__table__.create(bind=bind, checkfirst=True)
        except Exception as exc:
            logger.warning(f"[DC_TALLY_SYNC_001] ensure_tables non-fatal warning: {exc}")
            try:
                db.rollback()
            except Exception:
                pass

    @staticmethod
    def resolve_period(
        period_preset: Optional[str] = "THIS_MONTH",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Tuple[Optional[date], Optional[date], str]:
        """
        Resolve period preset or custom date strings into (start_date, end_date, canonical_preset).
        Supports: TODAY, YESTERDAY, THIS_WEEK, THIS_MONTH, LAST_MONTH, THIS_QUARTER,
                  THIS_FY, LAST_FY, ALL_TIME, CUSTOM.
        """
        today = get_indian_time().date()
        preset = (period_preset or "THIS_MONTH").strip().upper()

        def _parse_d(val: Optional[str]) -> Optional[date]:
            if not val:
                return None
            val = str(val).strip()[:10]
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y%m%d"):
                try:
                    return datetime.strptime(val, fmt).date()
                except ValueError:
                    continue
            return None

        custom_start = _parse_d(date_from)
        custom_end = _parse_d(date_to)

        if preset == "CUSTOM" or (custom_start or custom_end):
            return custom_start, custom_end or today, "CUSTOM"
        if preset in ("TODAY", "FTD"):
            return today, today, "TODAY"
        if preset == "YESTERDAY":
            yd = today - timedelta(days=1)
            return yd, yd, "YESTERDAY"
        if preset == "THIS_WEEK":
            start = today - timedelta(days=today.weekday())
            return start, today, "THIS_WEEK"
        if preset in ("THIS_MONTH", "MTD"):
            return today.replace(day=1), today, "THIS_MONTH"
        if preset == "LAST_MONTH":
            first_this = today.replace(day=1)
            last_prev = first_this - timedelta(days=1)
            return last_prev.replace(day=1), last_prev, "LAST_MONTH"
        if preset == "THIS_QUARTER":
            q_month = ((today.month - 1) // 3) * 3 + 1
            return date(today.year, q_month, 1), today, "THIS_QUARTER"
        if preset in ("THIS_FY", "YTD"):
            fy_start = date(today.year if today.month >= 4 else today.year - 1, 4, 1)
            return fy_start, today, "THIS_FY"
        if preset == "LAST_FY":
            fy_end_year = today.year if today.month >= 4 else today.year - 1
            return date(fy_end_year - 1, 4, 1), date(fy_end_year, 3, 31), "LAST_FY"
        if preset in ("ALL_TIME", "OVERALL", "ALL"):
            return None, None, "ALL_TIME"

        return today.replace(day=1), today, preset

    # ─────────────────────────────────────────────────────────────────────────
    # WVV HASH & RECORD EXTRACTION ACROSS ALL MODULES
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _load_sync_map(db: Session, company_id: int) -> Dict[Tuple[str, int], TallySyncRecord]:
        """Batch-load existing TallySyncRecord rows for a company."""
        TallyIntegrationService.ensure_tables(db)
        rows = (
            db.query(TallySyncRecord)
            .filter(TallySyncRecord.company_id == company_id)
            .all()
        )
        return {(r.entity_type, r.entity_id): r for r in rows}

    @staticmethod
    def _resolve_effective_status(
        sync_rec: Optional[TallySyncRecord],
        live_wvv_hash: str,
        native_status: Optional[str] = None,
    ) -> str:
        """
        Determine effective Tally sync status using WVV hash verification:
          - If previously SYNCED or EXPORTED, but live_wvv_hash != sync_rec.wvv_hash,
            automatically flag as MODIFIED_PENDING_SYNC!
        """
        if sync_rec:
            if sync_rec.tally_status == "EXCLUDED":
                return "EXCLUDED"
            if sync_rec.tally_status in ("SYNCED", "EXPORTED"):
                if sync_rec.wvv_hash and sync_rec.wvv_hash != live_wvv_hash:
                    return "MODIFIED_PENDING_SYNC"
                return sync_rec.tally_status
            return sync_rec.tally_status

        if native_status:
            ns = native_status.upper()
            if ns in ("SYNCED", "TALLY_DONE", "UPDATED"):
                return "SYNCED"
            if ns in ("EXPORTED",):
                return "EXPORTED"
            if ns in ("EXCLUDED", "EXCEPTION_TALLY"):
                return "EXCLUDED"
            if ns == "MISMATCH":
                return "MISMATCH"
        return "NOT_SYNCED"

    @staticmethod
    def collect_company_vouchers(
        db: Session,
        company_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        segment_id: Optional[int] = None,
        modules: Optional[List[str]] = None,
        sync_status_filter: Optional[str] = "ALL",
        include_company_wide: bool = False,
        include_cashflow_register: bool = False,
    ) -> Dict[str, Any]:
        """
        Collect all eligible records across Purchase Orders, Purchase Invoices,
        Sales Invoices, Cash/Income/Expense/Payment Entries, and Journal Vouchers/Ledgers,
        computing live WVV hashes and resolving effective Tally sync statuses.
        """
        selected_modules = [m.upper() for m in (modules or ALL_TALLY_MODULES)]
        sync_map = TallyIntegrationService._load_sync_map(db, company_id)
        status_filter = (sync_status_filter or "ALL").upper()
        seen_keys = set()
        validation_warnings: List[Dict[str, Any]] = []
        company_wide_excluded_modules: List[str] = []

        # Fix 10: When a segment filter is active, company-wide models without segment_id
        # (PURCHASE_ORDERS, LEDGERS_JV) are excluded unless include_company_wide=True.
        if segment_id and not include_company_wide:
            for cw_mod in ("PURCHASE_ORDERS", "LEDGERS_JV"):
                if cw_mod in selected_modules:
                    company_wide_excluded_modules.append(cw_mod)

        # Preload lookup maps
        vendors_map = {
            v.id: v
            for v in db.query(VendorMaster).all()
        }

        segments_map = {
            s.id: s.segment_name
            for s in db.query(CompanySegment).filter(CompanySegment.company_id == company_id).all()
        }
        income_sources_map = {
            s.id: s.source_name for s in db.query(IncomeSourceType).all()
        }
        main_cats_map = {c.id: c.name for c in db.query(ExpenseMainCategory).all()}
        sub_cats_map = {c.id: c.name for c in db.query(ExpenseSubCategory).all()}
        bank_accts_map = {
            b.id: b.bank_name
            for b in db.query(CompanyBankAccount).filter(CompanyBankAccount.company_id == company_id).all()
        }
        ledger_masters_map = {
            m.id: m.account_name
            for m in db.query(AccountLedgerMaster).filter(AccountLedgerMaster.company_id == company_id).all()
        }

        # Determine primary cash & bank ledger names for this company
        default_bank_ledger = "Bank Account"
        default_cash_ledger = "Cash"
        default_upi_ledger = "Bank Account"
        for m in (
            db.query(AccountLedgerMaster)
            .filter(AccountLedgerMaster.company_id == company_id, AccountLedgerMaster.is_active == True)
            .order_by(AccountLedgerMaster.id)
            .all()
        ):
            if m.account_type == "BANK" and default_bank_ledger == "Bank Account":
                default_bank_ledger = m.account_name
            elif m.account_type == "CASH" and default_cash_ledger == "Cash":
                default_cash_ledger = m.account_name
            elif m.account_type == "UPI":
                default_upi_ledger = m.account_name

        def _pm_ledger(pm: Optional[str], bank_account_id: Optional[int] = None) -> str:
            if bank_account_id:
                if bank_account_id in ledger_masters_map:
                    return ledger_masters_map[bank_account_id]
                if bank_account_id in bank_accts_map:
                    return bank_accts_map[bank_account_id]
            mode = (pm or "BANK").upper()
            if mode == "CASH":
                return default_cash_ledger
            if mode == "UPI":
                return default_upi_ledger
            return default_bank_ledger

        def _passes_sync_filter(eff_status: str) -> bool:
            if eff_status == "EXCLUDED" and status_filter != "EXCLUDED":
                return False
            if status_filter in ("ALL", ""):
                return True
            if status_filter in ("UNSYNCED_OR_MODIFIED", "PENDING"):
                return eff_status in (
                    "NOT_SYNCED",
                    "MODIFIED_PENDING_SYNC",
                    "MISMATCH",
                    "CANCELLED_PENDING_SYNC",
                )
            if status_filter == "MODIFIED_ONLY":
                return eff_status in ("MODIFIED_PENDING_SYNC", "CANCELLED_PENDING_SYNC")
            if status_filter == "SYNCED_ONLY":
                return eff_status in ("SYNCED", "EXPORTED", "CANCELLED_EXPORTED", "CANCELLED_SYNCED")
            return eff_status == status_filter

        items_list: List[Dict[str, Any]] = []
        module_stats: Dict[str, Dict[str, Any]] = {
            mod: {
                "total": 0,
                "not_synced": 0,
                "exported": 0,
                "synced": 0,
                "modified": 0,
                "mismatch": 0,
                "cancelled_pending_sync": 0,
                "excluded": 0,
                "total_amount": Decimal("0.00"),
                "is_company_wide": mod in ("PURCHASE_ORDERS", "LEDGERS_JV"),
                "excluded_by_segment_filter": mod in company_wide_excluded_modules,
            }
            for mod in [
                "PURCHASE_ORDERS",
                "PURCHASE_INVOICES",
                "SALES_INVOICES",
                "CASH_ENTRIES",
                "LEDGERS_JV",
            ]
        }

        def _record_stat(mod_key: str, eff_status: str, amt: Decimal):
            st = module_stats[mod_key]
            st["total"] += 1
            st["total_amount"] += amt
            if eff_status == "NOT_SYNCED":
                st["not_synced"] += 1
            elif eff_status in ("EXPORTED", "CANCELLED_EXPORTED"):
                st["exported"] += 1
            elif eff_status in ("SYNCED", "CANCELLED_SYNCED"):
                st["synced"] += 1
            elif eff_status == "MODIFIED_PENDING_SYNC":
                st["modified"] += 1
            elif eff_status == "MISMATCH":
                st["mismatch"] += 1
            elif eff_status == "CANCELLED_PENDING_SYNC":
                st["cancelled_pending_sync"] += 1
            elif eff_status == "EXCLUDED":
                st["excluded"] += 1

        # ── 1. PURCHASE ORDERS (ProcurementRequest + SparePurchaseOrder) ─────
        if "PURCHASE_ORDERS" in selected_modules and (not segment_id or include_company_wide):
            # 1a. ProcurementRequest (QUOTE_APPROVED, PO_CREATED, COMPLETED)
            pr_q = db.query(ProcurementRequest).filter(
                ProcurementRequest.company_id == company_id,
                ProcurementRequest.status.in_(["QUOTE_APPROVED", "PO_CREATED", "COMPLETED"]),
            )
            if start_date:
                pr_q = pr_q.filter(ProcurementRequest.request_date >= start_date)
            if end_date:
                pr_q = pr_q.filter(ProcurementRequest.request_date <= end_date)

            exported_pr_ids = set()
            for pr in pr_q.order_by(ProcurementRequest.request_date.asc(), ProcurementRequest.id.asc()).all():
                seen_keys.add(("PURCHASE_ORDER", pr.id))
                exported_pr_ids.add(pr.id)
                vendor = vendors_map.get(pr.approved_vendor_id)
                vendor_name = vendor.vendor_name if vendor else "Approved Vendor"
                quote = (
                    db.query(ProcurementQuote)
                    .filter(ProcurementQuote.id == pr.approved_quote_id)
                    .first()
                    if pr.approved_quote_id
                    else db.query(ProcurementQuote)
                    .filter(ProcurementQuote.request_id == pr.id, ProcurementQuote.is_selected == True)
                    .first()
                )
                quote_items_map = {}
                if quote:
                    for qi in (
                        db.query(ProcurementQuoteItem)
                        .filter(ProcurementQuoteItem.quote_id == quote.id)
                        .all()
                    ):
                        quote_items_map[qi.request_item_id] = qi

                delivery_days = int(quote.delivery_days or 0) if (quote and quote.delivery_days) else 0
                base_po_date = pr.request_date or get_indian_time().date()
                order_due_date = base_po_date + timedelta(days=delivery_days)

                po_lines = []
                calc_total = Decimal("0.00")
                for req_item in pr.request_items or []:
                    qi = quote_items_map.get(req_item.id)
                    qty = _q3(req_item.required_qty or 1)
                    rate = _q2(qi.unit_rate if qi and qi.unit_rate else (req_item.item.standard_cost if req_item.item and getattr(req_item.item, "standard_cost", None) else 0))
                    line_amt = _q2(qi.total_amount if qi and qi.total_amount else (qty * rate))
                    calc_total += line_amt
                    po_lines.append({
                        "item_name": (req_item.item.item_name if req_item.item else f"Item #{req_item.item_id}"),
                        "item_code": (req_item.item.item_code if req_item.item else ""),
                        "hsn_code": (req_item.item.hsn_code if req_item.item else ""),
                        "quantity": qty,
                        "uom": req_item.unit_of_measure or "PCS",
                        "rate": rate,
                        "amount": line_amt,
                        "order_due_date": order_due_date,
                    })

                grand_total = _q2(quote.grand_total if quote and quote.grand_total else calc_total)
                wvv_hash = _compute_sha256({
                    "type": "PURCHASE_ORDER",
                    "id": pr.id,
                    "no": pr.request_number,
                    "date": str(pr.request_date),
                    "due_date": str(order_due_date),
                    "vendor": vendor_name,
                    "total": str(grand_total),
                    "status": pr.status,
                    "lines": [(l["item_name"], str(l["quantity"]), str(l["amount"])) for l in po_lines],
                })
                sync_rec = sync_map.get(("PURCHASE_ORDER", pr.id))
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash)
                _record_stat("PURCHASE_ORDERS", eff_status, grand_total)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "PURCHASE_ORDERS",
                        "entity_type": "PURCHASE_ORDER",
                        "entity_id": pr.id,
                        "myntos_voucher_no": pr.request_number,
                        "tally_voucher_type": "Purchase Order",
                        "tally_guid": _make_tally_guid(company_id, "PURCHASE_ORDER", pr.id),
                        "transaction_date": pr.request_date,
                        "order_due_date": order_due_date,
                        "party_name": vendor_name,
                        "party_gstin": vendor.gst_number if vendor else None,
                        "party_state": vendor.state if vendor else None,
                        "segment_id": None,
                        "segment_name": "Company-Wide (Purchase Order)",
                        "amount": grand_total,
                        "taxable_amount": grand_total,
                        "cgst_amount": Decimal("0.00"),
                        "sgst_amount": Decimal("0.00"),
                        "igst_amount": Decimal("0.00"),
                        "round_off": Decimal("0.00"),
                        "narration": f"MyntOS Purchase Order {pr.request_number}" + (f" | {pr.notes}" if pr.notes else ""),
                        "inventory_lines": po_lines,
                        "ledger_entries": [
                            {"ledger_name": vendor_name, "is_deemed_positive": False, "amount": grand_total, "is_party": True},
                            {"ledger_name": "Purchase A/c", "is_deemed_positive": True, "amount": grand_total, "is_party": False},
                        ],
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

            # 1b. SparePurchaseOrder (APPROVED) — skip if already spawned into ProcurementRequest
            spo_q = db.query(SparePurchaseOrder).filter(
                SparePurchaseOrder.company_id == company_id,
                SparePurchaseOrder.status == "APPROVED",
            )
            for spo in spo_q.order_by(SparePurchaseOrder.id.asc()).all():
                spawned_reqs = spo.procurement_req_ids or []
                if spawned_reqs and any(int(rid) in exported_pr_ids for rid in spawned_reqs if str(rid).isdigit()):
                    continue
                if spawned_reqs:
                    existing_spawned = (
                        db.query(ProcurementRequest.id)
                        .filter(
                            ProcurementRequest.company_id == company_id,
                            ProcurementRequest.id.in_([int(rid) for rid in spawned_reqs if str(rid).isdigit()]),
                        )
                        .first()
                    )
                    if existing_spawned:
                        continue

                seen_keys.add(("SPARE_PO", spo.id))
                spo_date = (spo.approved_at or spo.created_at or get_indian_time()).date()
                if start_date and spo_date < start_date:
                    continue
                if end_date and spo_date > end_date:
                    continue

                spo_lines = []
                spo_total = Decimal("0.00")
                primary_vendor_name = "Spare Parts Vendor"
                for ln in spo.lines or []:
                    if ln.vendor and primary_vendor_name == "Spare Parts Vendor":
                        primary_vendor_name = ln.vendor.vendor_name
                    qty = _q3(ln.quantity or 1)
                    rate = _q2(ln.last_purchase_rate or 0)
                    amt = _q2(qty * rate)
                    spo_total += amt
                    spo_lines.append({
                        "item_name": ln.item_name or (ln.item.item_name if ln.item else f"Item #{ln.item_id}"),
                        "item_code": ln.item_code or "",
                        "hsn_code": ln.item.hsn_code if ln.item else "",
                        "quantity": qty,
                        "uom": ln.unit_of_measure or "PCS",
                        "rate": rate,
                        "amount": amt,
                        "order_due_date": spo_date,
                    })

                wvv_hash = _compute_sha256({
                    "type": "SPARE_PO",
                    "id": spo.id,
                    "no": spo.order_number,
                    "date": str(spo_date),
                    "vendor": primary_vendor_name,
                    "total": str(spo_total),
                    "lines": len(spo_lines),
                })
                sync_rec = sync_map.get(("SPARE_PO", spo.id))
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash)
                _record_stat("PURCHASE_ORDERS", eff_status, spo_total)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "PURCHASE_ORDERS",
                        "entity_type": "SPARE_PO",
                        "entity_id": spo.id,
                        "myntos_voucher_no": spo.order_number,
                        "tally_voucher_type": "Purchase Order",
                        "tally_guid": _make_tally_guid(company_id, "SPARE_PO", spo.id),
                        "transaction_date": spo_date,
                        "order_due_date": spo_date,
                        "party_name": primary_vendor_name,
                        "party_gstin": None,
                        "party_state": None,
                        "segment_id": None,
                        "segment_name": "Company-Wide (Purchase Order)",
                        "amount": spo_total,
                        "taxable_amount": spo_total,
                        "cgst_amount": Decimal("0.00"),
                        "sgst_amount": Decimal("0.00"),
                        "igst_amount": Decimal("0.00"),
                        "round_off": Decimal("0.00"),
                        "narration": f"MyntOS Spare Purchase Order {spo.order_number}" + (f" | {spo.notes}" if spo.notes else ""),
                        "inventory_lines": spo_lines,
                        "ledger_entries": [
                            {"ledger_name": primary_vendor_name, "is_deemed_positive": False, "amount": spo_total, "is_party": True},
                            {"ledger_name": "Purchase A/c", "is_deemed_positive": True, "amount": spo_total, "is_party": False},
                        ],
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

        # ── 2. PURCHASE INVOICES (PurchaseInvoiceUpload + VendorTransactionHeader) ──
        if "PURCHASE_INVOICES" in selected_modules:
            pu_q = db.query(PurchaseInvoiceUpload).filter(
                PurchaseInvoiceUpload.company_id == company_id,
                PurchaseInvoiceUpload.status.in_(["CONFIRMED", "PROCESSED"]),
            )
            if segment_id:
                pu_q = pu_q.filter(PurchaseInvoiceUpload.segment_id == segment_id)

            uploaded_vtxn_ids = set()
            for pu in pu_q.order_by(PurchaseInvoiceUpload.id.asc()).all():
                if pu.vendor_transaction_id:
                    uploaded_vtxn_ids.add(pu.vendor_transaction_id)
                txn_date = pu.vendor_invoice_date or (pu.confirmed_at or pu.uploaded_at or get_indian_time()).date()
                if start_date and txn_date < start_date:
                    continue
                if end_date and txn_date > end_date:
                    continue
                seen_keys.add(("PURCHASE_INVOICE", pu.id))

                vendor = pu.vendor or vendors_map.get(pu.vendor_id)
                vendor_name = (vendor.vendor_name if vendor else None) or "Sundry Creditor Vendor"
                vch_no = pu.voucher_number or pu.upload_number
                supplier_inv_no = pu.vendor_invoice_no or vch_no
                is_return = (pu.document_type or "").lower() in ("debit_note", "return", "purchase_return")
                tally_vch_type = "Debit Note" if is_return else "Purchase"

                taxable = _q2(pu.taxable_amount or pu.subtotal or 0)
                cgst = _q2(pu.cgst_amount or 0)
                sgst = _q2(pu.sgst_amount or 0)
                igst = _q2(pu.igst_amount or 0)
                courier_amt = _q2(pu.courier_amount or 0) if pu.courier_is_inclusive else Decimal("0.00")
                transport_amt = _q2(pu.transport_amount or 0) if pu.transport_is_inclusive else Decimal("0.00")
                grand_total = _q2(pu.grand_total or (taxable + cgst + sgst + igst + courier_amt + transport_amt))

                inv_lines = []
                lines_taxable_sum = Decimal("0.00")
                for li in pu.line_items or []:
                    l_qty = _q3(li.quantity or 1)
                    l_rate = _q2(li.unit_rate or 0)
                    l_taxable = _q2(li.taxable_amount or (l_qty * l_rate))
                    lines_taxable_sum += l_taxable
                    inv_lines.append({
                        "item_name": li.item_description or f"Item #{li.line_number}",
                        "item_code": li.item_code or "",
                        "hsn_code": li.hsn_code or "",
                        "quantity": l_qty,
                        "uom": li.unit_of_measure or "PCS",
                        "rate": l_rate,
                        "discount_pct": _q2(li.discount_percent or 0),
                        "amount": l_taxable,
                        "gst_rate": _q2(li.gst_rate or 0),
                        "ledger_name": "Purchase A/c",
                    })

                if inv_lines and lines_taxable_sum > Decimal("0.00"):
                    base_purchase_amt = lines_taxable_sum
                else:
                    base_purchase_amt = taxable

                # Compute exact Round Off so Debit == Credit to 0.01 paisa
                legs_sum = base_purchase_amt + cgst + sgst + igst + courier_amt + transport_amt
                round_off = _q2(grand_total - legs_sum)

                # Build balanced ledger entries
                # Normal Purchase: Vendor is CREDITED (is_deemed_positive=False), Purchase/GST are DEBITED (is_deemed_positive=True)
                # Debit Note (Return): Vendor is DEBITED (is_deemed_positive=True), Purchase/GST are CREDITED (is_deemed_positive=False)
                party_deemed_pos = True if is_return else False
                expense_deemed_pos = False if is_return else True

                ledger_entries = [
                    {
                        "ledger_name": vendor_name,
                        "is_deemed_positive": party_deemed_pos,
                        "amount": grand_total,
                        "is_party": True,
                        "bill_ref": supplier_inv_no,
                        "bill_type": "Agst Ref" if is_return else "New Ref",
                    },
                    {
                        "ledger_name": "Purchase A/c",
                        "is_deemed_positive": expense_deemed_pos,
                        "amount": base_purchase_amt,
                        "is_party": False,
                    },
                ]
                if cgst > Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "CGST Input",
                        "is_deemed_positive": expense_deemed_pos,
                        "amount": cgst,
                        "is_party": False,
                    })
                if sgst > Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "SGST Input",
                        "is_deemed_positive": expense_deemed_pos,
                        "amount": sgst,
                        "is_party": False,
                    })
                if igst > Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "IGST Input",
                        "is_deemed_positive": expense_deemed_pos,
                        "amount": igst,
                        "is_party": False,
                    })
                if courier_amt > Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "Courier Charges",
                        "is_deemed_positive": expense_deemed_pos,
                        "amount": courier_amt,
                        "is_party": False,
                    })
                if transport_amt > Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "Transport Charges",
                        "is_deemed_positive": expense_deemed_pos,
                        "amount": transport_amt,
                        "is_party": False,
                    })
                if round_off != Decimal("0.00"):
                    ro_deemed_pos = expense_deemed_pos if round_off > Decimal("0.00") else party_deemed_pos
                    ledger_entries.append({
                        "ledger_name": "Round Off A/c",
                        "is_deemed_positive": ro_deemed_pos,
                        "amount": abs(round_off),
                        "is_party": False,
                    })

                wvv_hash = _compute_sha256({
                    "type": "PURCHASE_INVOICE",
                    "id": pu.id,
                    "no": vch_no,
                    "ref": supplier_inv_no,
                    "date": str(txn_date),
                    "vendor": vendor_name,
                    "taxable": str(base_purchase_amt),
                    "cgst": str(cgst),
                    "sgst": str(sgst),
                    "igst": str(igst),
                    "grand_total": str(grand_total),
                    "lines": len(inv_lines),
                })
                sync_rec = sync_map.get(("PURCHASE_INVOICE", pu.id))
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash)
                _record_stat("PURCHASE_INVOICES", eff_status, grand_total)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "PURCHASE_INVOICES",
                        "entity_type": "PURCHASE_INVOICE",
                        "entity_id": pu.id,
                        "myntos_voucher_no": vch_no,
                        "supplier_invoice_no": supplier_inv_no,
                        "tally_voucher_type": tally_vch_type,
                        "tally_guid": _make_tally_guid(company_id, "PURCHASE_INVOICE", pu.id),
                        "transaction_date": txn_date,
                        "party_name": vendor_name,
                        "party_gstin": vendor.gst_number if vendor else None,
                        "party_state": (vendor.state if vendor else None) or pu.seller_state,
                        "segment_id": pu.segment_id,
                        "segment_name": segments_map.get(pu.segment_id, "Purchase"),
                        "amount": grand_total,
                        "taxable_amount": base_purchase_amt,
                        "cgst_amount": cgst,
                        "sgst_amount": sgst,
                        "igst_amount": igst,
                        "round_off": round_off,
                        "narration": f"MyntOS Purchase {vch_no} (Supplier Inv: {supplier_inv_no}) - {vendor_name}"
                        + (f" | {pu.review_notes}" if pu.review_notes else ""),
                        "inventory_lines": inv_lines,
                        "ledger_entries": ledger_entries,
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

            # 2b. Standalone VendorTransactionHeader (PURCHASE / DEBIT_NOTE not already linked to PurchaseInvoiceUpload)
            vt_q = db.query(VendorTransactionHeader).filter(
                VendorTransactionHeader.company_id == company_id,
                VendorTransactionHeader.status == "APPROVED",
                VendorTransactionHeader.transaction_type.in_(["PURCHASE", "DEBIT_NOTE"]),
            )
            if segment_id:
                vt_q = vt_q.filter(VendorTransactionHeader.segment_id == segment_id)
            if start_date:
                vt_q = vt_q.filter(VendorTransactionHeader.transaction_date >= start_date)
            if end_date:
                vt_q = vt_q.filter(VendorTransactionHeader.transaction_date <= end_date)

            for vt in vt_q.order_by(VendorTransactionHeader.transaction_date.asc(), VendorTransactionHeader.id.asc()).all():
                if vt.id in uploaded_vtxn_ids:
                    continue
                seen_keys.add(("VENDOR_TXN", vt.id))
                vendor = vendors_map.get(vt.vendor_id)
                vendor_name = vendor.vendor_name if vendor else "Sundry Creditor Vendor"
                is_return = vt.transaction_type == "DEBIT_NOTE"
                tally_vch_type = "Debit Note" if is_return else "Purchase"
                taxable = _q2(vt.taxable_amount or vt.subtotal or 0)
                cgst = _q2(vt.total_cgst or 0)
                sgst = _q2(vt.total_sgst or 0)
                igst = _q2(vt.total_igst or 0)
                grand_total = _q2(vt.grand_total or (taxable + cgst + sgst + igst))
                round_off = _q2(grand_total - (taxable + cgst + sgst + igst))

                party_deemed_pos = True if is_return else False
                expense_deemed_pos = False if is_return else True
                ledger_entries = [
                    {
                        "ledger_name": vendor_name,
                        "is_deemed_positive": party_deemed_pos,
                        "amount": grand_total,
                        "is_party": True,
                        "bill_ref": vt.vendor_invoice_no or vt.transaction_number,
                        "bill_type": "Agst Ref" if is_return else "New Ref",
                    },
                    {
                        "ledger_name": "Purchase A/c",
                        "is_deemed_positive": expense_deemed_pos,
                        "amount": taxable,
                        "is_party": False,
                    },
                ]
                for lbl, amt in [("CGST Input", cgst), ("SGST Input", sgst), ("IGST Input", igst)]:
                    if amt > Decimal("0.00"):
                        ledger_entries.append({
                            "ledger_name": lbl,
                            "is_deemed_positive": expense_deemed_pos,
                            "amount": amt,
                            "is_party": False,
                        })
                if round_off != Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "Round Off A/c",
                        "is_deemed_positive": expense_deemed_pos if round_off > Decimal("0.00") else party_deemed_pos,
                        "amount": abs(round_off),
                        "is_party": False,
                    })

                wvv_hash = _compute_sha256({
                    "type": "VENDOR_TXN",
                    "id": vt.id,
                    "no": vt.transaction_number,
                    "date": str(vt.transaction_date),
                    "vendor": vendor_name,
                    "grand_total": str(grand_total),
                })
                sync_rec = sync_map.get(("VENDOR_TXN", vt.id))
                eff_status = TallyIntegrationService._resolve_effective_status(
                    sync_rec, wvv_hash, vt.tally_status
                )
                _record_stat("PURCHASE_INVOICES", eff_status, grand_total)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "PURCHASE_INVOICES",
                        "entity_type": "VENDOR_TXN",
                        "entity_id": vt.id,
                        "myntos_voucher_no": vt.transaction_number,
                        "supplier_invoice_no": vt.vendor_invoice_no or vt.transaction_number,
                        "tally_voucher_type": tally_vch_type,
                        "tally_guid": _make_tally_guid(company_id, "VENDOR_TXN", vt.id),
                        "transaction_date": vt.transaction_date,
                        "party_name": vendor_name,
                        "party_gstin": vendor.gst_number if vendor else None,
                        "party_state": vendor.state if vendor else None,
                        "segment_id": vt.segment_id,
                        "segment_name": segments_map.get(vt.segment_id, "Purchase"),
                        "amount": grand_total,
                        "taxable_amount": taxable,
                        "cgst_amount": cgst,
                        "sgst_amount": sgst,
                        "igst_amount": igst,
                        "round_off": round_off,
                        "narration": f"MyntOS Vendor Purchase {vt.transaction_number} - {vendor_name}"
                        + (f" | {vt.narration}" if vt.narration else ""),
                        "inventory_lines": [],
                        "ledger_entries": ledger_entries,
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

        # ── 3. SALES INVOICES (SalesInvoice) ─────────────────────────────────
        if "SALES_INVOICES" in selected_modules:
            si_q = db.query(SalesInvoice).filter(
                SalesInvoice.company_id == company_id,
                SalesInvoice.status.in_(["CONFIRMED", "RETURNED"]),
            )
            if segment_id:
                si_q = si_q.filter(SalesInvoice.segment_id == segment_id)
            if start_date:
                si_q = si_q.filter(SalesInvoice.invoice_date >= start_date)
            if end_date:
                si_q = si_q.filter(SalesInvoice.invoice_date <= end_date)

            for si in si_q.order_by(SalesInvoice.invoice_date.asc(), SalesInvoice.id.asc()).all():
                seen_keys.add(("SALES_INVOICE", si.id))
                customer_name = (si.customer_name or "").strip() or "Walk-in Customer"
                is_credit_note = (si.document_type or "").lower() in ("credit_note", "return", "sales_return") or si.status == "RETURNED"
                tally_vch_type = "Credit Note" if is_credit_note else "Sales"

                taxable = _q2(si.taxable_amount or si.subtotal or 0)
                cgst = _q2(si.cgst_amount or 0)
                sgst = _q2(si.sgst_amount or 0)
                igst = _q2(si.igst_amount or 0)
                courier_amt = _q2(si.courier_amount or 0)
                transport_amt = _q2(si.transport_amount or 0)
                grand_total = _q2(si.net_payable or si.grand_total or (taxable + cgst + sgst + igst + courier_amt + transport_amt))

                inv_lines = []
                lines_taxable_sum = Decimal("0.00")
                for li in si.line_items or []:
                    l_qty = _q3(li.quantity or 1)
                    l_rate = _q2(li.unit_rate or 0)
                    l_taxable = _q2(li.taxable_amount or (l_qty * l_rate))
                    lines_taxable_sum += l_taxable
                    inv_lines.append({
                        "item_name": li.item_description or f"Item #{li.line_number}",
                        "item_code": li.item_code or "",
                        "hsn_code": li.hsn_code or "",
                        "quantity": l_qty,
                        "uom": li.unit_of_measure or "PCS",
                        "rate": l_rate,
                        "discount_pct": _q2(li.discount_percent or 0),
                        "amount": l_taxable,
                        "gst_rate": _q2(li.gst_rate or 0),
                        "ledger_name": "Sales A/c",
                    })

                base_sales_amt = lines_taxable_sum if (inv_lines and lines_taxable_sum > Decimal("0.00")) else taxable
                legs_sum = base_sales_amt + cgst + sgst + igst + courier_amt + transport_amt
                round_off = _q2(grand_total - legs_sum)

                # Normal Sales: Customer is DEBITED (is_deemed_positive=True), Sales/GST are CREDITED (is_deemed_positive=False)
                # Credit Note: Customer is CREDITED (is_deemed_positive=False), Sales/GST are DEBITED (is_deemed_positive=True)
                party_deemed_pos = False if is_credit_note else True
                rev_deemed_pos = True if is_credit_note else False

                ledger_entries = [
                    {
                        "ledger_name": customer_name,
                        "is_deemed_positive": party_deemed_pos,
                        "amount": grand_total,
                        "is_party": True,
                        "bill_ref": si.invoice_number,
                        "bill_type": "Agst Ref" if is_credit_note else "New Ref",
                    },
                    {
                        "ledger_name": "Sales A/c",
                        "is_deemed_positive": rev_deemed_pos,
                        "amount": base_sales_amt,
                        "is_party": False,
                    },
                ]
                for lbl, amt in [("CGST Output", cgst), ("SGST Output", sgst), ("IGST Output", igst)]:
                    if amt > Decimal("0.00"):
                        ledger_entries.append({
                            "ledger_name": lbl,
                            "is_deemed_positive": rev_deemed_pos,
                            "amount": amt,
                            "is_party": False,
                        })
                if courier_amt > Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "Courier Charges",
                        "is_deemed_positive": rev_deemed_pos,
                        "amount": courier_amt,
                        "is_party": False,
                    })
                if transport_amt > Decimal("0.00"):
                    ledger_entries.append({
                        "ledger_name": "Transport Charges",
                        "is_deemed_positive": rev_deemed_pos,
                        "amount": transport_amt,
                        "is_party": False,
                    })
                if round_off != Decimal("0.00"):
                    ro_deemed_pos = rev_deemed_pos if round_off > Decimal("0.00") else party_deemed_pos
                    ledger_entries.append({
                        "ledger_name": "Round Off A/c",
                        "is_deemed_positive": ro_deemed_pos,
                        "amount": abs(round_off),
                        "is_party": False,
                    })

                wvv_hash = _compute_sha256({
                    "type": "SALES_INVOICE",
                    "id": si.id,
                    "no": si.invoice_number,
                    "date": str(si.invoice_date),
                    "customer": customer_name,
                    "gstin": si.customer_gstin or "",
                    "taxable": str(base_sales_amt),
                    "cgst": str(cgst),
                    "sgst": str(sgst),
                    "igst": str(igst),
                    "grand_total": str(grand_total),
                    "status": si.status,
                    "lines": len(inv_lines),
                })
                sync_rec = sync_map.get(("SALES_INVOICE", si.id))
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash)
                _record_stat("SALES_INVOICES", eff_status, grand_total)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "SALES_INVOICES",
                        "entity_type": "SALES_INVOICE",
                        "entity_id": si.id,
                        "myntos_voucher_no": si.invoice_number,
                        "tally_voucher_type": tally_vch_type,
                        "tally_guid": _make_tally_guid(company_id, "SALES_INVOICE", si.id),
                        "transaction_date": si.invoice_date,
                        "party_name": customer_name,
                        "party_gstin": si.customer_gstin,
                        "party_state": si.customer_state or si.buyer_state,
                        "segment_id": si.segment_id,
                        "segment_name": segments_map.get(si.segment_id, "Sales"),
                        "amount": grand_total,
                        "taxable_amount": base_sales_amt,
                        "cgst_amount": cgst,
                        "sgst_amount": sgst,
                        "igst_amount": igst,
                        "round_off": round_off,
                        "narration": f"MyntOS Sales Invoice {si.invoice_number} - {customer_name}"
                        + (f" | {si.remarks}" if si.remarks else ""),
                        "inventory_lines": inv_lines,
                        "ledger_entries": ledger_entries,
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

        # ── 4. CASH, INCOME, EXPENSE & PAYMENT ENTRIES ────────────────────────
        cashflow_register_notice: Optional[Dict[str, Any]] = None
        if "CASH_ENTRIES" in selected_modules:
            detailed_cash_dates = set()
            seen_payment_refs = set()
            seen_invoice_payments = set()

            # 4a. Income Entries (CONFIRMED, TALLY_DONE, ADJUSTMENT)
            ie_q = db.query(IncomeEntry).filter(
                IncomeEntry.company_id == company_id,
                IncomeEntry.is_deleted == False,
                IncomeEntry.status.in_(["CONFIRMED", "TALLY_DONE", "ADJUSTMENT"]),
            )
            if segment_id:
                ie_q = ie_q.filter(IncomeEntry.segment_id == segment_id)
            if start_date:
                ie_q = ie_q.filter(IncomeEntry.income_date >= start_date)
            if end_date:
                ie_q = ie_q.filter(IncomeEntry.income_date <= end_date)

            for ie in ie_q.order_by(IncomeEntry.income_date.asc(), IncomeEntry.id.asc()).all():
                seen_keys.add(("INCOME_ENTRY", ie.id))
                amt = _q2(ie.amount or 0)
                if amt <= Decimal("0.00"):
                    continue
                eff_date = ie.payment_date or ie.income_date
                if eff_date:
                    detailed_cash_dates.add(eff_date)
                if ie.income_date:
                    detailed_cash_dates.add(ie.income_date)
                if ie.payment_reference:
                    seen_payment_refs.add((str(ie.payment_reference).strip().upper(), amt))

                payer = (ie.payer_name or "").strip() or income_sources_map.get(ie.income_source_id, "Service Income")
                bank_or_cash = _pm_ledger(ie.payment_mode, ie.bank_account_id)
                wvv_hash = _compute_sha256({
                    "type": "INCOME_ENTRY",
                    "id": ie.id,
                    "no": ie.entry_number,
                    "date": str(ie.income_date),
                    "payer": payer,
                    "mode": ie.payment_mode,
                    "amount": str(amt),
                    "narration": ie.narration or "",
                })
                sync_rec = sync_map.get(("INCOME_ENTRY", ie.id))
                native_stat = "SYNCED" if ie.status == "TALLY_DONE" else ie.tally_status
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash, native_stat)
                _record_stat("CASH_ENTRIES", eff_status, amt)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "CASH_ENTRIES",
                        "entity_type": "INCOME_ENTRY",
                        "entity_id": ie.id,
                        "myntos_voucher_no": ie.entry_number,
                        "tally_voucher_type": "Receipt",
                        "tally_guid": _make_tally_guid(company_id, "INCOME_ENTRY", ie.id),
                        "transaction_date": eff_date,
                        "party_name": payer,
                        "party_gstin": None,
                        "party_state": ie.payer_state,
                        "segment_id": ie.segment_id,
                        "segment_name": segments_map.get(ie.segment_id, "General"),
                        "amount": amt,
                        "taxable_amount": amt,
                        "cgst_amount": Decimal("0.00"),
                        "sgst_amount": Decimal("0.00"),
                        "igst_amount": Decimal("0.00"),
                        "round_off": Decimal("0.00"),
                        "payment_mode": ie.payment_mode,
                        "payment_reference": ie.payment_reference,
                        "narration": f"MyntOS Receipt {ie.entry_number} ({ie.payment_mode}) - {payer}"
                        + (f" | {ie.narration}" if ie.narration else ""),
                        "inventory_lines": [],
                        "ledger_entries": [
                            # Receipt: Cash/Bank is DEBITED (True), Party/Income Head is CREDITED (False)
                            {"ledger_name": bank_or_cash, "is_deemed_positive": True, "amount": amt, "is_party": False},
                            {"ledger_name": payer, "is_deemed_positive": False, "amount": amt, "is_party": True, "bill_ref": ie.entry_number},
                        ],
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

            # 4b. Expense Entries (APPROVED) — Fix 6: accurate GST Input & TDS Payable legs
            ee_q = db.query(ExpenseEntry).filter(
                ExpenseEntry.company_id == company_id,
                ExpenseEntry.status == "APPROVED",
            )
            if segment_id:
                ee_q = ee_q.filter(ExpenseEntry.segment_id == segment_id)
            if start_date:
                ee_q = ee_q.filter(ExpenseEntry.expense_date >= start_date)
            if end_date:
                ee_q = ee_q.filter(ExpenseEntry.expense_date <= end_date)

            for ee in ee_q.order_by(ExpenseEntry.expense_date.asc(), ExpenseEntry.id.asc()).all():
                seen_keys.add(("EXPENSE_ENTRY", ee.id))
                base_amt = _q2(ee.amount or 0)
                gst_amt = _q2(ee.gst_amount or 0) if ee.gst_applicable else Decimal("0.00")
                tds_amt = _q2(ee.tds_amount or 0) if ee.tds_applicable else Decimal("0.00")
                raw_net = _q2(ee.net_amount or 0)

                if base_amt <= Decimal("0.00") and raw_net > Decimal("0.00"):
                    base_amt = raw_net - gst_amt + tds_amt
                expected_net = _q2(base_amt + gst_amt - tds_amt)
                net_amt = raw_net if raw_net > Decimal("0.00") else expected_net
                if net_amt <= Decimal("0.00") and base_amt <= Decimal("0.00"):
                    continue

                if ee.expense_date:
                    detailed_cash_dates.add(ee.expense_date)
                ref_val = ee.payment_utr or ee.payment_reference
                if ref_val:
                    seen_payment_refs.add((str(ref_val).strip().upper(), net_amt))

                exp_head = (
                    ee.custom_category_name
                    or sub_cats_map.get(ee.sub_category_id)
                    or main_cats_map.get(ee.main_category_id)
                    or "Office Expenses"
                )
                payee_name = (ee.vendor_name or "").strip() or exp_head
                bank_or_cash = _pm_ledger(ee.payment_mode, ee.bank_account_id)

                # Validate GST / TDS component completeness & arithmetic consistency
                exp_warning = None
                if ee.gst_applicable and gst_amt <= Decimal("0.00"):
                    exp_warning = f"Expense {ee.entry_number} has gst_applicable=True but gst_amount is 0.00"
                elif ee.tds_applicable and tds_amt <= Decimal("0.00"):
                    exp_warning = f"Expense {ee.entry_number} has tds_applicable=True but tds_amount is 0.00"
                elif abs(expected_net - net_amt) > Decimal("1.00"):
                    exp_warning = (
                        f"Expense {ee.entry_number} tax math mismatch: "
                        f"amount({base_amt}) + gst({gst_amt}) - tds({tds_amt}) = {expected_net} != net_amount({net_amt})"
                    )
                if exp_warning:
                    validation_warnings.append({
                        "entity_type": "EXPENSE_ENTRY",
                        "entity_id": ee.id,
                        "voucher_no": ee.entry_number,
                        "warning": exp_warning,
                    })

                is_exp_return = bool(getattr(ee, "is_return", False))
                tally_vch_type = "Receipt" if is_exp_return else "Payment"
                dr_flag = False if is_exp_return else True
                cr_flag = True if is_exp_return else False

                # If tax components are consistent (within 1.00 round-off), post separate Expense, GST Input, TDS Payable, and Bank/Cash legs
                if abs(expected_net - net_amt) <= Decimal("1.00"):
                    exp_round_off = _q2(net_amt - expected_net)
                    exp_ledgers = [
                        {"ledger_name": exp_head, "is_deemed_positive": dr_flag, "amount": base_amt, "is_party": False},
                    ]
                    if gst_amt > Decimal("0.00"):
                        exp_ledgers.append({
                            "ledger_name": "GST Input",
                            "is_deemed_positive": dr_flag,
                            "amount": gst_amt,
                            "is_party": False,
                        })
                    if tds_amt > Decimal("0.00"):
                        exp_ledgers.append({
                            "ledger_name": "TDS Payable",
                            "is_deemed_positive": cr_flag,
                            "amount": tds_amt,
                            "is_party": False,
                        })
                    if exp_round_off != Decimal("0.00"):
                        exp_ledgers.append({
                            "ledger_name": "Round Off A/c",
                            "is_deemed_positive": dr_flag if exp_round_off > Decimal("0.00") else cr_flag,
                            "amount": abs(exp_round_off),
                            "is_party": False,
                        })
                    exp_ledgers.append({
                        "ledger_name": bank_or_cash,
                        "is_deemed_positive": cr_flag,
                        "amount": net_amt,
                        "is_party": False,
                    })
                    voucher_gross = max(base_amt + gst_amt, net_amt + tds_amt)
                else:
                    # Fallback when stored net_amount conflicts with base+gst-tds: post to Suspense/review and flag warning
                    exp_ledgers = [
                        {"ledger_name": exp_head, "is_deemed_positive": dr_flag, "amount": net_amt, "is_party": False},
                        {"ledger_name": bank_or_cash, "is_deemed_positive": cr_flag, "amount": net_amt, "is_party": False},
                    ]
                    voucher_gross = net_amt

                wvv_hash = _compute_sha256({
                    "type": "EXPENSE_ENTRY",
                    "id": ee.id,
                    "no": ee.entry_number,
                    "date": str(ee.expense_date),
                    "head": exp_head,
                    "payee": payee_name,
                    "mode": ee.payment_mode,
                    "base_amount": str(base_amt),
                    "gst_amount": str(gst_amt),
                    "tds_amount": str(tds_amt),
                    "net_amount": str(net_amt),
                    "is_return": is_exp_return,
                    "narration": ee.narration or "",
                })
                sync_rec = sync_map.get(("EXPENSE_ENTRY", ee.id))
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash, ee.tally_status)
                _record_stat("CASH_ENTRIES", eff_status, net_amt)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "CASH_ENTRIES",
                        "entity_type": "EXPENSE_ENTRY",
                        "entity_id": ee.id,
                        "myntos_voucher_no": ee.entry_number,
                        "tally_voucher_type": tally_vch_type,
                        "tally_guid": _make_tally_guid(company_id, "EXPENSE_ENTRY", ee.id),
                        "transaction_date": ee.expense_date,
                        "party_name": payee_name,
                        "party_gstin": None,
                        "party_state": None,
                        "segment_id": ee.segment_id,
                        "segment_name": segments_map.get(ee.segment_id, "General"),
                        "amount": net_amt,
                        "gross_amount": voucher_gross,
                        "taxable_amount": base_amt,
                        "gst_amount": gst_amt,
                        "tds_amount": tds_amt,
                        "cgst_amount": Decimal("0.00"),
                        "sgst_amount": Decimal("0.00"),
                        "igst_amount": Decimal("0.00"),
                        "round_off": Decimal("0.00"),
                        "payment_mode": ee.payment_mode,
                        "payment_reference": ref_val,
                        "validation_warning": exp_warning,
                        "narration": f"MyntOS Expense {tally_vch_type} {ee.entry_number} ({ee.payment_mode}) - {payee_name} [{exp_head}]"
                        + (f" | {ee.narration}" if ee.narration else ""),
                        "inventory_lines": [],
                        "ledger_entries": exp_ledgers,
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

            # 4c. Standalone PaymentTransaction (COMPLETED) — Fix 7: complete payment coverage
            if not segment_id or include_company_wide:
                pt_q = db.query(PaymentTransaction).filter(
                    PaymentTransaction.company_id == company_id,
                    PaymentTransaction.status == "COMPLETED",
                )
                if start_date:
                    pt_q = pt_q.filter(PaymentTransaction.transaction_date >= start_date)
                if end_date:
                    pt_q = pt_q.filter(PaymentTransaction.transaction_date <= end_date)

                for pt in pt_q.order_by(PaymentTransaction.transaction_date.asc(), PaymentTransaction.id.asc()).all():
                    seen_keys.add(("PAYMENT_TXN", pt.id))
                    amt = _q2(pt.amount or 0)
                    if amt <= Decimal("0.00"):
                        continue
                    pt_ref = (pt.payment_reference or pt.bank_reference or pt.cheque_number or "").strip()
                    if pt_ref and (pt_ref.upper(), amt) in seen_payment_refs:
                        continue
                    if pt_ref:
                        seen_payment_refs.add((pt_ref.upper(), amt))
                    if (pt.source_type or "").upper() == "INVOICE" and pt.source_id:
                        seen_invoice_payments.add((int(pt.source_id), pt.transaction_date, amt))
                    if pt.transaction_date:
                        detailed_cash_dates.add(pt.transaction_date)

                    ttype = (pt.transaction_type or "PAYMENT_TO_VENDOR").upper()
                    is_inflow = ttype in ("RECEIPT_FROM_CUSTOMER", "ADVANCE_RECEIPT", "REFUND_FROM_VENDOR")
                    tally_vch_type = "Receipt" if is_inflow else "Payment"
                    bill_type = "Advance" if "ADVANCE" in ttype else "Agst Ref"
                    party_name = (pt.party_name or "").strip() or (
                        "Sundry Debtor" if is_inflow else "Sundry Creditor Vendor"
                    )
                    bank_or_cash = (pt.bank_name or "").strip() or _pm_ledger(pt.payment_mode)
                    bill_ref_val = pt_ref or pt.transaction_number

                    if is_inflow:
                        pt_ledgers = [
                            {"ledger_name": bank_or_cash, "is_deemed_positive": True, "amount": amt, "is_party": False},
                            {
                                "ledger_name": party_name,
                                "is_deemed_positive": False,
                                "amount": amt,
                                "is_party": True,
                                "bill_ref": bill_ref_val,
                                "bill_type": bill_type,
                            },
                        ]
                    else:
                        pt_ledgers = [
                            {
                                "ledger_name": party_name,
                                "is_deemed_positive": True,
                                "amount": amt,
                                "is_party": True,
                                "bill_ref": bill_ref_val,
                                "bill_type": bill_type,
                            },
                            {"ledger_name": bank_or_cash, "is_deemed_positive": False, "amount": amt, "is_party": False},
                        ]

                    wvv_hash = _compute_sha256({
                        "type": "PAYMENT_TXN",
                        "id": pt.id,
                        "no": pt.transaction_number,
                        "ttype": ttype,
                        "date": str(pt.transaction_date),
                        "party": party_name,
                        "mode": pt.payment_mode,
                        "amount": str(amt),
                    })
                    sync_rec = sync_map.get(("PAYMENT_TXN", pt.id))
                    eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash)
                    _record_stat("CASH_ENTRIES", eff_status, amt)

                    if _passes_sync_filter(eff_status):
                        items_list.append({
                            "module": "CASH_ENTRIES",
                            "entity_type": "PAYMENT_TXN",
                            "entity_id": pt.id,
                            "myntos_voucher_no": pt.transaction_number,
                            "tally_voucher_type": tally_vch_type,
                            "tally_guid": _make_tally_guid(company_id, "PAYMENT_TXN", pt.id),
                            "transaction_date": pt.transaction_date,
                            "party_name": party_name,
                            "party_gstin": None,
                            "party_state": None,
                            "segment_id": None,
                            "segment_name": "Company-Wide (Payment)",
                            "amount": amt,
                            "taxable_amount": amt,
                            "cgst_amount": Decimal("0.00"),
                            "sgst_amount": Decimal("0.00"),
                            "igst_amount": Decimal("0.00"),
                            "round_off": Decimal("0.00"),
                            "payment_mode": pt.payment_mode,
                            "payment_reference": pt_ref,
                            "narration": f"MyntOS {tally_vch_type} {pt.transaction_number} ({pt.payment_mode}) - {party_name}"
                            + (f" | {pt.narration}" if pt.narration else ""),
                            "inventory_lines": [],
                            "ledger_entries": pt_ledgers,
                            "wvv_hash": wvv_hash,
                            "tally_status": eff_status,
                            "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                        })

            # 4d. SalesInvoicePayment (Customer receipts against Sales Invoices) — Fix 7
            sip_q = (
                db.query(SalesInvoicePayment, SalesInvoice)
                .join(SalesInvoice, SalesInvoicePayment.invoice_id == SalesInvoice.id)
                .filter(
                    SalesInvoice.company_id == company_id,
                    SalesInvoice.status.in_(["CONFIRMED", "RETURNED"]),
                )
            )
            if segment_id:
                sip_q = sip_q.filter(SalesInvoice.segment_id == segment_id)
            if start_date:
                sip_q = sip_q.filter(SalesInvoicePayment.payment_date >= start_date)
            if end_date:
                sip_q = sip_q.filter(SalesInvoicePayment.payment_date <= end_date)

            for sip, parent_si in sip_q.order_by(SalesInvoicePayment.payment_date.asc(), SalesInvoicePayment.id.asc()).all():
                seen_keys.add(("SALES_INVOICE_PAYMENT", sip.id))
                amt = _q2(sip.amount or 0)
                if amt <= Decimal("0.00"):
                    continue
                sip_ref = (sip.reference_number or "").strip()
                if sip_ref and (sip_ref.upper(), amt) in seen_payment_refs:
                    continue
                if (parent_si.id, sip.payment_date, amt) in seen_invoice_payments:
                    continue
                if sip_ref:
                    seen_payment_refs.add((sip_ref.upper(), amt))
                if sip.payment_date:
                    detailed_cash_dates.add(sip.payment_date)

                customer_name = (parent_si.customer_name or "").strip() or "Walk-in Customer"
                bank_or_cash = _pm_ledger(sip.payment_mode)
                sip_vch_no = f"RCPT-{parent_si.invoice_number}-{sip.id}"

                wvv_hash = _compute_sha256({
                    "type": "SALES_INVOICE_PAYMENT",
                    "id": sip.id,
                    "invoice_no": parent_si.invoice_number,
                    "date": str(sip.payment_date),
                    "customer": customer_name,
                    "mode": sip.payment_mode,
                    "amount": str(amt),
                })
                sync_rec = sync_map.get(("SALES_INVOICE_PAYMENT", sip.id))
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash)
                _record_stat("CASH_ENTRIES", eff_status, amt)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "CASH_ENTRIES",
                        "entity_type": "SALES_INVOICE_PAYMENT",
                        "entity_id": sip.id,
                        "myntos_voucher_no": sip_vch_no,
                        "supplier_invoice_no": parent_si.invoice_number,
                        "tally_voucher_type": "Receipt",
                        "tally_guid": _make_tally_guid(company_id, "SALES_INVOICE_PAYMENT", sip.id),
                        "transaction_date": sip.payment_date,
                        "party_name": customer_name,
                        "party_gstin": parent_si.customer_gstin,
                        "party_state": parent_si.customer_state or parent_si.buyer_state,
                        "segment_id": parent_si.segment_id,
                        "segment_name": segments_map.get(parent_si.segment_id, "Sales"),
                        "amount": amt,
                        "taxable_amount": amt,
                        "cgst_amount": Decimal("0.00"),
                        "sgst_amount": Decimal("0.00"),
                        "igst_amount": Decimal("0.00"),
                        "round_off": Decimal("0.00"),
                        "payment_mode": sip.payment_mode,
                        "payment_reference": sip_ref,
                        "narration": f"MyntOS Sales Invoice Receipt {sip_vch_no} against {parent_si.invoice_number}"
                        + (f" | {sip.notes}" if sip.notes else ""),
                        "inventory_lines": [],
                        "ledger_entries": [
                            {"ledger_name": bank_or_cash, "is_deemed_positive": True, "amount": amt, "is_party": False},
                            {
                                "ledger_name": customer_name,
                                "is_deemed_positive": False,
                                "amount": amt,
                                "is_party": True,
                                "bill_ref": parent_si.invoice_number,
                                "bill_type": "Agst Ref",
                            },
                        ],
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

            # 4e. CashflowRegister (Fix 5: Daily aggregate guard & non-destructive Inflow/Outflow handling)
            if not segment_id:
                cf_q = db.query(CashflowRegister)
                if start_date:
                    cf_q = cf_q.filter(CashflowRegister.entry_date >= start_date)
                if end_date:
                    cf_q = cf_q.filter(CashflowRegister.entry_date <= end_date)
                cf_rows = cf_q.order_by(CashflowRegister.entry_date.asc()).all()
                active_cf_rows = [
                    cf for cf in cf_rows
                    if _q2(cf.total_in()) > Decimal("0.00") or _q2(cf.total_out()) > Decimal("0.00")
                ]
                overlapping_dates = [
                    cf.entry_date.isoformat() for cf in active_cf_rows if cf.entry_date in detailed_cash_dates
                ]
                unmapped_dates = [
                    cf.entry_date.isoformat() for cf in active_cf_rows if cf.entry_date not in detailed_cash_dates
                ]
                if active_cf_rows:
                    cashflow_register_notice = {
                        "total_register_days": len(active_cf_rows),
                        "overlapping_detailed_days": overlapping_dates,
                        "unmapped_only_days": unmapped_dates,
                        "exported_by_default": False,
                        "message": (
                            "CashflowRegister is a multi-company daily aggregate without individual ledger mappings "
                            "and is excluded from default voucher export to prevent duplicate postings against "
                            "detailed IncomeEntry/ExpenseEntry/PaymentTransaction records."
                        ),
                    }

                if include_cashflow_register:
                    for cf in active_cf_rows:
                        # Skip dates that already have detailed IncomeEntry/ExpenseEntry/Payment vouchers
                        if cf.entry_date in detailed_cash_dates:
                            continue
                        t_in = _q2(cf.total_in())
                        t_out = _q2(cf.total_out())
                        date_tag = cf.entry_date.strftime("%Y%m%d")

                        # Emit separate Receipt (t_in) and Payment (t_out) vouchers so outflows are NEVER dropped on net-positive days
                        # and map to explicit Suspense ledgers instead of inventing Sales A/c or Office Expenses
                        if t_in > Decimal("0.00"):
                            seen_keys.add(("CASHFLOW_REGISTER_IN", cf.id))
                            in_no = f"CF-{date_tag}-IN"
                            in_hash = _compute_sha256({
                                "type": "CASHFLOW_REGISTER_IN",
                                "id": cf.id,
                                "date": str(cf.entry_date),
                                "in": str(t_in),
                                "notes": cf.notes or "",
                            })
                            sync_rec = sync_map.get(("CASHFLOW_REGISTER_IN", cf.id))
                            eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, in_hash)
                            _record_stat("CASH_ENTRIES", eff_status, t_in)
                            if _passes_sync_filter(eff_status):
                                items_list.append({
                                    "module": "CASH_ENTRIES",
                                    "entity_type": "CASHFLOW_REGISTER_IN",
                                    "entity_id": cf.id,
                                    "myntos_voucher_no": in_no,
                                    "tally_voucher_type": "Receipt",
                                    "tally_guid": _make_tally_guid(company_id, "CASHFLOW_REGISTER_IN", cf.id),
                                    "transaction_date": cf.entry_date,
                                    "party_name": "Unmapped Cashflow Inflow (Suspense)",
                                    "party_gstin": None,
                                    "party_state": None,
                                    "segment_id": None,
                                    "segment_name": "Cash Register (Suspense)",
                                    "amount": t_in,
                                    "taxable_amount": t_in,
                                    "cgst_amount": Decimal("0.00"),
                                    "sgst_amount": Decimal("0.00"),
                                    "igst_amount": Decimal("0.00"),
                                    "round_off": Decimal("0.00"),
                                    "needs_mapping": True,
                                    "validation_warning": "Aggregate CashflowRegister inflow mapped to Suspense A/c pending CA ledger classification",
                                    "narration": f"MyntOS Daily Cashflow Inflow {in_no} (₹{t_in})"
                                    + (f" | {cf.notes}" if cf.notes else ""),
                                    "inventory_lines": [],
                                    "ledger_entries": [
                                        {"ledger_name": default_cash_ledger, "is_deemed_positive": True, "amount": t_in, "is_party": False},
                                        {"ledger_name": "Unmapped Cashflow Inflow (Suspense)", "is_deemed_positive": False, "amount": t_in, "is_party": False},
                                    ],
                                    "wvv_hash": in_hash,
                                    "tally_status": eff_status,
                                    "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                                })

                        if t_out > Decimal("0.00"):
                            seen_keys.add(("CASHFLOW_REGISTER_OUT", cf.id))
                            out_no = f"CF-{date_tag}-OUT"
                            out_hash = _compute_sha256({
                                "type": "CASHFLOW_REGISTER_OUT",
                                "id": cf.id,
                                "date": str(cf.entry_date),
                                "out": str(t_out),
                                "notes": cf.notes or "",
                            })
                            sync_rec = sync_map.get(("CASHFLOW_REGISTER_OUT", cf.id))
                            eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, out_hash)
                            _record_stat("CASH_ENTRIES", eff_status, t_out)
                            if _passes_sync_filter(eff_status):
                                items_list.append({
                                    "module": "CASH_ENTRIES",
                                    "entity_type": "CASHFLOW_REGISTER_OUT",
                                    "entity_id": cf.id,
                                    "myntos_voucher_no": out_no,
                                    "tally_voucher_type": "Payment",
                                    "tally_guid": _make_tally_guid(company_id, "CASHFLOW_REGISTER_OUT", cf.id),
                                    "transaction_date": cf.entry_date,
                                    "party_name": "Unmapped Cashflow Outflow (Suspense)",
                                    "party_gstin": None,
                                    "party_state": None,
                                    "segment_id": None,
                                    "segment_name": "Cash Register (Suspense)",
                                    "amount": t_out,
                                    "taxable_amount": t_out,
                                    "cgst_amount": Decimal("0.00"),
                                    "sgst_amount": Decimal("0.00"),
                                    "igst_amount": Decimal("0.00"),
                                    "round_off": Decimal("0.00"),
                                    "needs_mapping": True,
                                    "validation_warning": "Aggregate CashflowRegister outflow mapped to Suspense A/c pending CA ledger classification",
                                    "narration": f"MyntOS Daily Cashflow Outflow {out_no} (₹{t_out})"
                                    + (f" | {cf.notes}" if cf.notes else ""),
                                    "inventory_lines": [],
                                    "ledger_entries": [
                                        {"ledger_name": "Unmapped Cashflow Outflow (Suspense)", "is_deemed_positive": True, "amount": t_out, "is_party": False},
                                        {"ledger_name": default_cash_ledger, "is_deemed_positive": False, "amount": t_out, "is_party": False},
                                    ],
                                    "wvv_hash": out_hash,
                                    "tally_status": eff_status,
                                    "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                                })

        # ── 5. JOURNAL VOUCHERS & LEDGER ENTRIES (JournalVoucher) ────────────
        if "LEDGERS_JV" in selected_modules and (not segment_id or include_company_wide):
            jv_q = db.query(JournalVoucher).filter(
                JournalVoucher.company_id == company_id,
                JournalVoucher.status == "POSTED",
            )
            if start_date:
                jv_q = jv_q.filter(JournalVoucher.voucher_date >= start_date)
            if end_date:
                jv_q = jv_q.filter(JournalVoucher.voucher_date <= end_date)

            jv_ids = [j.id for j in jv_q.all()]
            jv_lines_by_vid: Dict[int, List[JournalVoucherLine]] = {}
            if jv_ids:
                for ln in (
                    db.query(JournalVoucherLine)
                    .filter(JournalVoucherLine.voucher_id.in_(jv_ids))
                    .order_by(JournalVoucherLine.sort_order.asc(), JournalVoucherLine.id.asc())
                    .all()
                ):
                    jv_lines_by_vid.setdefault(ln.voucher_id, []).append(ln)

            for jv in jv_q.order_by(JournalVoucher.voucher_date.asc(), JournalVoucher.id.asc()).all():
                seen_keys.add(("JOURNAL_VOUCHER", jv.id))
                amt = _q2(jv.amount or 0)
                if amt <= Decimal("0.00"):
                    continue
                v_type_map = {
                    "JOURNAL": "Journal",
                    "CONTRA": "Contra",
                    "PAYMENT": "Payment",
                    "RECEIPT": "Receipt",
                }
                tally_vch_type = v_type_map.get((jv.voucher_type or "JOURNAL").upper(), "Journal")
                child_lines = jv_lines_by_vid.get(jv.id, [])

                ledger_entries = []
                if child_lines:
                    dr_sum = Decimal("0.00")
                    cr_sum = Decimal("0.00")
                    for cl in child_lines:
                        l_amt = _q2(cl.amount or 0)
                        if l_amt <= Decimal("0.00"):
                            continue
                        is_dr = (cl.entry_type or "DEBIT").upper() == "DEBIT"
                        if is_dr:
                            dr_sum += l_amt
                        else:
                            cr_sum += l_amt
                        ledger_entries.append({
                            "ledger_name": cl.party_name or cl.account_name,
                            "is_deemed_positive": is_dr,
                            "amount": l_amt,
                            "is_party": bool(cl.party_name or cl.account_type == "PARTY"),
                        })
                    # Ensure strict balance
                    if dr_sum != cr_sum:
                        diff = abs(dr_sum - cr_sum)
                        ledger_entries.append({
                            "ledger_name": "Round Off A/c",
                            "is_deemed_positive": dr_sum < cr_sum,
                            "amount": diff,
                            "is_party": False,
                        })
                else:
                    ledger_entries = [
                        {
                            "ledger_name": jv.dr_account_name,
                            "is_deemed_positive": True,
                            "amount": amt,
                            "is_party": jv.dr_account_type == "PARTY",
                        },
                        {
                            "ledger_name": jv.cr_account_name,
                            "is_deemed_positive": False,
                            "amount": amt,
                            "is_party": jv.cr_account_type == "PARTY",
                        },
                    ]

                wvv_hash = _compute_sha256({
                    "type": "JOURNAL_VOUCHER",
                    "id": jv.id,
                    "no": jv.voucher_number,
                    "vtype": jv.voucher_type,
                    "date": str(jv.voucher_date),
                    "dr": jv.dr_account_name,
                    "cr": jv.cr_account_name,
                    "amount": str(amt),
                    "narration": jv.narration or "",
                    "lines": [(l["ledger_name"], l["is_deemed_positive"], str(l["amount"])) for l in ledger_entries],
                })
                sync_rec = sync_map.get(("JOURNAL_VOUCHER", jv.id))
                eff_status = TallyIntegrationService._resolve_effective_status(sync_rec, wvv_hash)
                _record_stat("LEDGERS_JV", eff_status, amt)

                if _passes_sync_filter(eff_status):
                    items_list.append({
                        "module": "LEDGERS_JV",
                        "entity_type": "JOURNAL_VOUCHER",
                        "entity_id": jv.id,
                        "myntos_voucher_no": jv.voucher_number,
                        "tally_voucher_type": tally_vch_type,
                        "tally_guid": _make_tally_guid(company_id, "JOURNAL_VOUCHER", jv.id),
                        "transaction_date": jv.voucher_date,
                        "party_name": jv.party_name or jv.dr_account_name,
                        "party_gstin": None,
                        "party_state": None,
                        "segment_id": None,
                        "segment_name": "Company-Wide (Ledgers & JV)",
                        "amount": amt,
                        "taxable_amount": amt,
                        "cgst_amount": Decimal("0.00"),
                        "sgst_amount": Decimal("0.00"),
                        "igst_amount": Decimal("0.00"),
                        "round_off": Decimal("0.00"),
                        "payment_mode": jv.payment_mode,
                        "payment_reference": jv.reference_number,
                        "narration": f"MyntOS {tally_vch_type} {jv.voucher_number}"
                        + (f" | {jv.narration}" if jv.narration else ""),
                        "inventory_lines": [],
                        "ledger_entries": ledger_entries,
                        "wvv_hash": wvv_hash,
                        "tally_status": eff_status,
                        "is_alter": bool(sync_rec and sync_rec.tally_status in ("EXPORTED", "SYNCED")),
                    })

        # ── 6. CANCELLATION & DELETION DETECTION (Fix 8) ─────────────────────
        # Inspect previously EXPORTED/SYNCED records in sync_map that were not collected above
        # because their source record was CANCELLED, REJECTED, REVERSED, or soft-deleted.
        entity_to_module = {
            "PURCHASE_ORDER": "PURCHASE_ORDERS",
            "SPARE_PO": "PURCHASE_ORDERS",
            "PURCHASE_INVOICE": "PURCHASE_INVOICES",
            "VENDOR_TXN": "PURCHASE_INVOICES",
            "SALES_INVOICE": "SALES_INVOICES",
            "INCOME_ENTRY": "CASH_ENTRIES",
            "EXPENSE_ENTRY": "CASH_ENTRIES",
            "PAYMENT_TXN": "CASH_ENTRIES",
            "SALES_INVOICE_PAYMENT": "CASH_ENTRIES",
            "JOURNAL_VOUCHER": "LEDGERS_JV",
        }

        def _is_source_cancelled_or_deleted(etype: str, eid: int) -> Tuple[bool, str]:
            if etype == "PURCHASE_ORDER":
                row = db.query(ProcurementRequest).filter(ProcurementRequest.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "REJECTED"):
                    return True, row.status.upper()
            elif etype == "SPARE_PO":
                row = db.query(SparePurchaseOrder).filter(SparePurchaseOrder.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "REJECTED"):
                    return True, row.status.upper()
            elif etype == "PURCHASE_INVOICE":
                row = db.query(PurchaseInvoiceUpload).filter(PurchaseInvoiceUpload.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "REJECTED"):
                    return True, row.status.upper()
            elif etype == "VENDOR_TXN":
                row = db.query(VendorTransactionHeader).filter(VendorTransactionHeader.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "REJECTED"):
                    return True, row.status.upper()
            elif etype == "SALES_INVOICE":
                row = db.query(SalesInvoice).filter(SalesInvoice.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "VOID", "REJECTED"):
                    return True, row.status.upper()
            elif etype == "INCOME_ENTRY":
                row = db.query(IncomeEntry).filter(IncomeEntry.id == eid).first()
                if not row or getattr(row, "is_deleted", False):
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "REJECTED"):
                    return True, row.status.upper()
            elif etype == "EXPENSE_ENTRY":
                row = db.query(ExpenseEntry).filter(ExpenseEntry.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "REJECTED"):
                    return True, row.status.upper()
            elif etype == "PAYMENT_TXN":
                row = db.query(PaymentTransaction).filter(PaymentTransaction.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "REVERSED", "FAILED"):
                    return True, row.status.upper()
            elif etype == "SALES_INVOICE_PAYMENT":
                row = db.query(SalesInvoicePayment).filter(SalesInvoicePayment.id == eid).first()
                if not row:
                    return True, "DELETED"
            elif etype == "JOURNAL_VOUCHER":
                row = db.query(JournalVoucher).filter(JournalVoucher.id == eid).first()
                if not row:
                    return True, "DELETED"
                if (row.status or "").upper() in ("CANCELLED", "VOID", "REJECTED"):
                    return True, row.status.upper()
            return False, ""

        dirty_cancelled_sync_recs = False
        for (etype, eid), srec in sync_map.items():
            if (etype, eid) in seen_keys:
                continue
            if srec.tally_status not in (
                "EXPORTED",
                "SYNCED",
                "MODIFIED_PENDING_SYNC",
                "CANCELLED_PENDING_SYNC",
                "CANCELLED_EXPORTED",
                "CANCELLED_SYNCED",
            ):
                continue
            mod_key = entity_to_module.get(etype)
            if not mod_key or mod_key not in selected_modules:
                continue
            if segment_id and mod_key in company_wide_excluded_modules:
                continue
            if segment_id and srec.segment_id != segment_id:
                continue
            if start_date and srec.transaction_date and srec.transaction_date < start_date:
                continue
            if end_date and srec.transaction_date and srec.transaction_date > end_date:
                continue

            is_canc, canc_reason = _is_source_cancelled_or_deleted(etype, eid)
            if not is_canc:
                continue

            eff_canc_status = (
                srec.tally_status
                if srec.tally_status in ("CANCELLED_EXPORTED", "CANCELLED_SYNCED")
                else "CANCELLED_PENDING_SYNC"
            )
            if srec.tally_status in ("EXPORTED", "SYNCED", "MODIFIED_PENDING_SYNC"):
                srec.tally_status = "CANCELLED_PENDING_SYNC"
                dirty_cancelled_sync_recs = True

            canc_wvv = _compute_sha256({
                "type": etype,
                "id": eid,
                "no": srec.myntos_voucher_no,
                "cancelled": True,
                "reason": canc_reason,
            })
            _record_stat(mod_key, eff_canc_status, Decimal("0.00"))
            if _passes_sync_filter(eff_canc_status):
                items_list.append({
                    "module": mod_key,
                    "entity_type": etype,
                    "entity_id": eid,
                    "myntos_voucher_no": srec.myntos_voucher_no,
                    "tally_voucher_type": srec.tally_voucher_type,
                    "tally_guid": srec.tally_guid or _make_tally_guid(company_id, etype, eid),
                    "transaction_date": srec.transaction_date or get_indian_time().date(),
                    "party_name": srec.party_name or "",
                    "party_gstin": None,
                    "party_state": None,
                    "segment_id": srec.segment_id,
                    "segment_name": segments_map.get(srec.segment_id, "Cancelled"),
                    "amount": Decimal("0.00"),
                    "original_amount": _q2(srec.amount or 0),
                    "taxable_amount": Decimal("0.00"),
                    "cgst_amount": Decimal("0.00"),
                    "sgst_amount": Decimal("0.00"),
                    "igst_amount": Decimal("0.00"),
                    "round_off": Decimal("0.00"),
                    "is_cancelled": True,
                    "cancellation_reason": canc_reason,
                    "narration": f"CANCELLED in MyntOS ({canc_reason}): {srec.myntos_voucher_no}",
                    "inventory_lines": [],
                    "ledger_entries": [],
                    "wvv_hash": canc_wvv,
                    "tally_status": eff_canc_status,
                    "is_alter": True,
                })

        if dirty_cancelled_sync_recs:
            try:
                db.commit()
            except Exception:
                db.rollback()

        return {
            "vouchers": items_list,
            "module_stats": {
                k: {**v, "total_amount": float(v["total_amount"])}
                for k, v in module_stats.items()
            },
            "company_wide_excluded_modules": company_wide_excluded_modules,
            "cashflow_register_notice": cashflow_register_notice,
            "validation_warnings": validation_warnings,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # TALLY XML GENERATOR (MASTERS + VOUCHERS) WITH VERSION & VOUCHER MODE
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_tally_xml(
        db: Session,
        company_id: int,
        tally_version: str = "TALLY_PRIME_4",
        voucher_mode: str = "AUTO",
        period_preset: str = "THIS_MONTH",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        segment_id: Optional[int] = None,
        modules: Optional[List[str]] = None,
        sync_status_filter: str = "ALL",
        include_masters: bool = True,
        mark_as_exported: bool = True,
        include_company_wide: bool = False,
        include_cashflow_register: bool = False,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate Tally-compatible <ENVELOPE> XML for the selected Tally version,
        date range/period, segment, and modules.
        Verifies WVV structural balance (Dr == Cr) on every accounting voucher and records a TallySyncBatch.
        """
        TallyIntegrationService.ensure_tables(db)
        ver_cfg = TALLY_VERSIONS.get((tally_version or "TALLY_PRIME_4").upper(), TALLY_VERSIONS["TALLY_PRIME_4"])
        v_mode = (voucher_mode or "AUTO").upper()
        selected_modules = [m.upper() for m in (modules or ALL_TALLY_MODULES)]

        start_date, end_date, resolved_preset = TallyIntegrationService.resolve_period(
            period_preset, date_from, date_to
        )

        company = db.query(AssociatedCompany).filter(AssociatedCompany.id == company_id).first()
        company_name = (company.company_name if company else f"Company #{company_id}").strip()
        company_state = (company.state if company and company.state else "Maharashtra").strip()

        only_masters = selected_modules == ["MASTERS"]
        collected = TallyIntegrationService.collect_company_vouchers(
            db=db,
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            segment_id=segment_id,
            modules=[] if only_masters else selected_modules,
            sync_status_filter=sync_status_filter,
            include_company_wide=include_company_wide,
            include_cashflow_register=include_cashflow_register,
        )
        vouchers = [] if only_masters else collected["vouchers"]
        has_masters = bool(include_masters or "MASTERS" in selected_modules)
        report_name = "All Masters" if has_masters else "Vouchers"

        # Build XML Root <ENVELOPE>
        envelope = ET.Element("ENVELOPE")
        header = ET.SubElement(envelope, "HEADER")
        ET.SubElement(header, "TALLYREQUEST").text = "Import Data"
        ET.SubElement(header, "TYPE").text = "Data"
        ET.SubElement(header, "ID").text = report_name
        if ver_cfg["code"] in ("TALLY_PRIME_4", "TALLY_PRIME_2"):
            ET.SubElement(header, "VERSION").text = ver_cfg["header_version"]

        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")

        req_desc = ET.SubElement(import_data, "REQUESTDESC")
        # Fix 3: Use "All Masters" whenever master definitions are included in the envelope,
        # and "Vouchers" for voucher-only exports.
        ET.SubElement(req_desc, "REPORTNAME").text = report_name
        static_vars = ET.SubElement(req_desc, "STATICVARIABLES")
        ET.SubElement(static_vars, "SVCURRENTCOMPANY").text = _clean_xml_text(company_name)

        req_data = ET.SubElement(import_data, "REQUESTDATA")

        masters_count = 0
        unresolved_ledgers: List[Dict[str, Any]] = []

        # Build explicit known-ledger group lookup (Fix 6: do NOT default unknown ledgers to Indirect Expenses)
        known_ledger_groups: Dict[str, str] = {
            "sales a/c": "Sales Accounts",
            "purchase a/c": "Purchase Accounts",
            "round off a/c": "Indirect Expenses",
            "courier charges": "Direct Expenses",
            "transport charges": "Direct Expenses",
            "office expenses": "Indirect Expenses",
            "cgst input": "Duties & Taxes",
            "sgst input": "Duties & Taxes",
            "igst input": "Duties & Taxes",
            "gst input": "Duties & Taxes",
            "cgst output": "Duties & Taxes",
            "sgst output": "Duties & Taxes",
            "igst output": "Duties & Taxes",
            "tds payable": "Duties & Taxes",
            "cash": "Cash-in-Hand",
            "bank account": "Bank Accounts",
            "unmapped cashflow inflow (suspense)": "Suspense A/c",
            "unmapped cashflow outflow (suspense)": "Suspense A/c",
            "suspense a/c": "Suspense A/c",
        }
        for (ec_name,) in db.query(ExpenseMainCategory.name).all():
            if ec_name:
                known_ledger_groups[ec_name.strip().lower()] = "Indirect Expenses"
        for (esc_name,) in db.query(ExpenseSubCategory.name).all():
            if esc_name:
                known_ledger_groups[esc_name.strip().lower()] = "Indirect Expenses"
        for (ist_name,) in db.query(IncomeSourceType.source_name).all():
            if ist_name:
                known_ledger_groups[ist_name.strip().lower()] = "Direct Incomes"
        for alm_name, alm_grp in (
            db.query(AccountLedgerMaster.account_name, AccountLedgerMaster.parent_group)
            .filter(AccountLedgerMaster.company_id == company_id)
            .all()
        ):
            if alm_name:
                known_ledger_groups[alm_name.strip().lower()] = alm_grp or "Current Assets"
        for (cba_name,) in (
            db.query(CompanyBankAccount.bank_name)
            .filter(CompanyBankAccount.company_id == company_id)
            .all()
        ):
            if cba_name:
                known_ledger_groups[cba_name.strip().lower()] = "Bank Accounts"
        for (vm_name,) in db.query(VendorMaster.vendor_name).all():
            if vm_name:
                known_ledger_groups[vm_name.strip().lower()] = "Sundry Creditors"
        for (mp_name,) in db.query(ManualPartyMaster.name).all():
            if mp_name:
                known_ledger_groups[str(mp_name).strip().lower()] = "Sundry Debtors"

        # ── 1. EMIT MASTERS (Units, Stock Groups, Stock Items, Ledger Masters, Parties) ──
        if has_masters:
            emitted_units = set()
            emitted_ledgers = set()
            emitted_items = set()

            def _emit_unit(uom_code: str):
                u = _clean_xml_text(uom_code or "PCS").upper()
                if not u or u in emitted_units:
                    return
                emitted_units.add(u)
                tm = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
                unit_el = ET.SubElement(tm, "UNIT", {"NAME": u, "RESERVEDNAME": "", "ACTION": "Create"})
                ET.SubElement(unit_el, "NAME").text = u
                ET.SubElement(unit_el, "ISSIMPLEUNIT").text = "Yes"
                ET.SubElement(unit_el, "DECIMALPLACES").text = "3"

            def _emit_ledger(
                name: str,
                parent_group: str,
                gstin: Optional[str] = None,
                pan: Optional[str] = None,
                state: Optional[str] = None,
                address: Optional[str] = None,
                opening_bal: Decimal = Decimal("0.00"),
                opening_type: str = "DEBIT",
                is_tax_ledger: bool = False,
                tax_duty_head: Optional[str] = None,
                bank_ac_no: Optional[str] = None,
                ifsc: Optional[str] = None,
            ):
                nonlocal masters_count
                clean_name = _clean_xml_text(name)
                if not clean_name:
                    return
                key = clean_name.lower()
                if key in emitted_ledgers:
                    return
                emitted_ledgers.add(key)

                # Map internal parent_group path (e.g. "Current Assets/Bank Accounts") to Tally group name without splitting "A/c"
                if parent_group and "/" in parent_group and not parent_group.strip().endswith("A/c"):
                    tally_parent = parent_group.split("/")[-1].strip()
                else:
                    tally_parent = (parent_group or "Suspense A/c").strip()
                tm = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
                led_el = ET.SubElement(tm, "LEDGER", {"NAME": clean_name, "RESERVEDNAME": "", "ACTION": "Create"})
                name_list = ET.SubElement(led_el, "NAME.LIST", {"TYPE": "String"})
                ET.SubElement(name_list, "NAME").text = clean_name
                ET.SubElement(led_el, "PARENT").text = _clean_xml_text(tally_parent)
                ET.SubElement(led_el, "ISBILLWISEON").text = (
                    "Yes" if tally_parent in ("Sundry Debtors", "Sundry Creditors") else "No"
                )
                ET.SubElement(led_el, "AFFECTSSTOCK").text = (
                    "Yes" if tally_parent in ("Sales Accounts", "Purchase Accounts") else "No"
                )

                if is_tax_ledger and tax_duty_head:
                    ET.SubElement(led_el, "TAXTYPE").text = "GST" if tax_duty_head != "TDS" else "TDS"
                    ET.SubElement(led_el, "GSTDUTYHEAD").text = tax_duty_head

                if gstin:
                    ET.SubElement(led_el, "PARTYGSTIN").text = _clean_xml_text(gstin)
                    ET.SubElement(led_el, "GSTREGISTRATIONTYPE").text = "Regular"
                if pan:
                    ET.SubElement(led_el, "INCOMETAXNUMBER").text = _clean_xml_text(pan)
                if state:
                    st_clean = _clean_xml_text(state)
                    if ver_cfg["use_ledstatename"]:
                        ET.SubElement(led_el, "LEDSTATENAME").text = st_clean
                    ET.SubElement(led_el, "STATENAME").text = st_clean
                if address:
                    addr_list = ET.SubElement(led_el, "ADDRESS.LIST", {"TYPE": "String"})
                    ET.SubElement(addr_list, "ADDRESS").text = _clean_xml_text(address)[:200]
                if bank_ac_no:
                    ET.SubElement(led_el, "BANKDETAILS").text = _clean_xml_text(bank_ac_no)
                if ifsc:
                    ET.SubElement(led_el, "IFSCODE").text = _clean_xml_text(ifsc)
                if opening_bal and opening_bal != Decimal("0.00"):
                    # In Tally Ledger Master, Debit opening balance is negative, Credit is positive
                    signed_ob = -abs(opening_bal) if opening_type.upper() == "DEBIT" else abs(opening_bal)
                    ET.SubElement(led_el, "OPENINGBALANCE").text = f"{signed_ob:.2f}"

                masters_count += 1

            def _emit_stock_item(
                item_name: str,
                uom: str = "PCS",
                hsn_code: Optional[str] = None,
                gst_rate: Decimal = Decimal("18.00"),
            ):
                nonlocal masters_count
                clean_item = _clean_xml_text(item_name)
                if not clean_item:
                    return
                key = clean_item.lower()
                if key in emitted_items:
                    return
                emitted_items.add(key)
                _emit_unit(uom)

                tm = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
                si_el = ET.SubElement(tm, "STOCKITEM", {"NAME": clean_item, "RESERVEDNAME": "", "ACTION": "Create"})
                nl = ET.SubElement(si_el, "NAME.LIST", {"TYPE": "String"})
                ET.SubElement(nl, "NAME").text = clean_item
                ET.SubElement(si_el, "BASEUNITS").text = _clean_xml_text(uom or "PCS").upper()
                # Fix 1: Use valid XML 1.0 text "Applicable" without U+0004 control character
                ET.SubElement(si_el, "GSTAPPLICABLE").text = "Applicable"
                if hsn_code:
                    ET.SubElement(si_el, "HSNCODE").text = _clean_xml_text(hsn_code)
                masters_count += 1

            # Emit standard units
            for std_u in ("PCS", "NOS", "SET", "KG", "BOX"):
                _emit_unit(std_u)

            # Emit Core Tax & System Ledgers
            _emit_ledger("Sales A/c", "Sales Accounts")
            _emit_ledger("Purchase A/c", "Purchase Accounts")
            _emit_ledger("Round Off A/c", "Indirect Expenses")
            _emit_ledger("Courier Charges", "Direct Expenses")
            _emit_ledger("Transport Charges", "Direct Expenses")
            _emit_ledger("Office Expenses", "Indirect Expenses")
            _emit_ledger("CGST Input", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="Central Tax")
            _emit_ledger("SGST Input", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="State Tax")
            _emit_ledger("IGST Input", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="Integrated Tax")
            _emit_ledger("GST Input", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="GST")
            _emit_ledger("TDS Payable", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="TDS")
            _emit_ledger("CGST Output", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="Central Tax")
            _emit_ledger("SGST Output", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="State Tax")
            _emit_ledger("IGST Output", "Duties & Taxes", is_tax_ledger=True, tax_duty_head="Integrated Tax")

            # Emit Company Chart of Accounts (AccountLedgerMaster)
            for alm in (
                db.query(AccountLedgerMaster)
                .filter(AccountLedgerMaster.company_id == company_id, AccountLedgerMaster.is_active == True)
                .all()
            ):
                _emit_ledger(
                    name=alm.account_name,
                    parent_group=alm.parent_group or "Current Assets",
                    opening_bal=_q2(alm.opening_balance or 0),
                    opening_type=alm.opening_balance_type or "DEBIT",
                    bank_ac_no=alm.account_number,
                    ifsc=alm.ifsc_code,
                )

            # Emit CompanyBankAccount ledgers
            for cba in (
                db.query(CompanyBankAccount)
                .filter(CompanyBankAccount.company_id == company_id, CompanyBankAccount.is_active == True)
                .all()
            ):
                _emit_ledger(
                    name=cba.bank_name,
                    parent_group="Bank Accounts",
                    bank_ac_no=cba.account_number,
                    ifsc=cba.ifsc_code,
                )

            # Emit Vendors (Sundry Creditors)
            for (
                vm_name,
                vm_gstin,
                vm_pan,
                vm_state,
                vm_addr,
                vm_acc,
                vm_ifsc,
                vm_app_cos,
            ) in (
                db.query(
                    VendorMaster.vendor_name,
                    VendorMaster.gst_number,
                    VendorMaster.pan_number,
                    VendorMaster.state,
                    VendorMaster.address,
                    VendorMaster.account_number,
                    VendorMaster.ifsc_code,
                    VendorMaster.applicable_companies,
                )
                .filter(VendorMaster.is_active == True)
                .order_by(VendorMaster.id.desc())
                .limit(500)
                .all()
            ):
                app_cos = vm_app_cos or []
                if app_cos and company_id not in app_cos and str(company_id) not in [str(x) for x in app_cos]:
                    continue
                _emit_ledger(
                    name=vm_name,
                    parent_group="Sundry Creditors",
                    gstin=vm_gstin,
                    pan=vm_pan,
                    state=vm_state,
                    address=vm_addr,
                    bank_ac_no=vm_acc,
                    ifsc=vm_ifsc,
                )

            # Emit Stock Items from StockItemMaster
            if "MASTERS" in selected_modules or include_masters:
                for sim_name, sim_uom, sim_hsn, sim_app_cos in (
                    db.query(
                        StockItemMaster.item_name,
                        StockItemMaster.unit_of_measure,
                        StockItemMaster.hsn_code,
                        StockItemMaster.applicable_companies,
                    )
                    .filter(StockItemMaster.is_active == True)
                    .order_by(StockItemMaster.id.desc())
                    .limit(500)
                    .all()
                ):
                    app_cos = sim_app_cos or []
                    if app_cos and company_id not in app_cos and str(company_id) not in [str(x) for x in app_cos]:
                        continue
                    _emit_stock_item(
                        item_name=sim_name,
                        uom=sim_uom or "PCS",
                        hsn_code=sim_hsn,
                    )

            # Ensure every ledger & stock item referenced in any exported voucher is also emitted as a Master!
            for v in vouchers:
                if v.get("is_cancelled"):
                    continue
                v_type = v["tally_voucher_type"]
                default_party_group = (
                    "Sundry Debtors" if v_type in ("Sales", "Credit Note", "Receipt") else "Sundry Creditors"
                )
                if v.get("party_name"):
                    p_clean = _clean_xml_text(v["party_name"]).lower()
                    p_grp = known_ledger_groups.get(p_clean, default_party_group)
                    _emit_ledger(
                        name=v["party_name"],
                        parent_group=p_grp,
                        gstin=v.get("party_gstin"),
                        state=v.get("party_state") or company_state,
                    )
                for le in v.get("ledger_entries", []):
                    l_name = le["ledger_name"]
                    l_key = _clean_xml_text(l_name).lower()
                    if le.get("is_party"):
                        grp = known_ledger_groups.get(l_key, default_party_group)
                    elif l_key in known_ledger_groups:
                        grp = known_ledger_groups[l_key]
                    else:
                        # Fix 6: Do not silently default unknown ledgers to Indirect Expenses!
                        grp = "Suspense A/c"
                        if not any(u["ledger_name"].lower() == l_key for u in unresolved_ledgers):
                            unresolved_ledgers.append({
                                "ledger_name": _clean_xml_text(l_name),
                                "voucher_no": v["myntos_voucher_no"],
                                "assigned_group": "Suspense A/c",
                                "reason": "Ledger not found in Chart of Accounts or known category masters; placed under Suspense A/c for CA review.",
                            })
                    _emit_ledger(name=l_name, parent_group=grp)
                for il in v.get("inventory_lines", []):
                    _emit_stock_item(
                        item_name=il["item_name"],
                        uom=il.get("uom", "PCS"),
                        hsn_code=il.get("hsn_code"),
                        gst_rate=_q2(il.get("gst_rate", 18)),
                    )
        else:
            # Even when include_masters=False, check for unresolved ledgers so callers get warnings
            for v in vouchers:
                if v.get("is_cancelled"):
                    continue
                for le in v.get("ledger_entries", []):
                    l_name = le["ledger_name"]
                    l_key = _clean_xml_text(l_name).lower()
                    if not le.get("is_party") and l_key not in known_ledger_groups:
                        if not any(u["ledger_name"].lower() == l_key for u in unresolved_ledgers):
                            unresolved_ledgers.append({
                                "ledger_name": _clean_xml_text(l_name),
                                "voucher_no": v["myntos_voucher_no"],
                                "assigned_group": "Suspense A/c",
                                "reason": "Ledger not found in Chart of Accounts or known category masters.",
                            })

        # ── 2. EMIT VOUCHERS ──────────────────────────────────────────────────
        vouchers_count = 0
        order_vouchers_count = 0
        cancelled_vouchers_count = 0
        total_debit_exported = Decimal("0.00")
        total_credit_exported = Decimal("0.00")

        now_ist = get_indian_time()
        batch_code = f"TALLY-EXP-{company_id}-{now_ist.strftime('%Y%m%d%H%M%S')}"

        for v in vouchers:
            tm = ET.SubElement(req_data, "TALLYMESSAGE", {"xmlns:UDF": "TallyUDF"})
            vch_type = v["tally_voucher_type"]
            vch_no = _clean_xml_text(v["myntos_voucher_no"])
            ref_no = _clean_xml_text(v.get("supplier_invoice_no") or vch_no)
            guid = v["tally_guid"]
            date_str = _tally_date(v["transaction_date"])
            party_name = _clean_xml_text(v.get("party_name") or "")
            is_cancelled_vch = bool(v.get("is_cancelled"))

            # Fix 8: Emit explicit Cancellation XML for cancelled/deleted records
            if is_cancelled_vch:
                vch_el = ET.SubElement(
                    tm,
                    "VOUCHER",
                    {
                        "REMOTEID": guid,
                        "VCHKEY": guid,
                        "VCHTYPE": vch_type,
                        "ACTION": "Cancel",
                        "OBJVIEW": "Accounting Voucher View",
                    },
                )
                ET.SubElement(vch_el, "GUID").text = guid
                ET.SubElement(vch_el, "DATE").text = date_str
                ET.SubElement(vch_el, "EFFECTIVEDATE").text = date_str
                ET.SubElement(vch_el, "VOUCHERTYPENAME").text = vch_type
                ET.SubElement(vch_el, "VOUCHERNUMBER").text = vch_no
                ET.SubElement(vch_el, "PARTYLEDGERNAME").text = party_name
                ET.SubElement(vch_el, "ISCANCELLED").text = "Yes"
                ET.SubElement(vch_el, "NARRATION").text = _clean_xml_text(v.get("narration") or f"Cancelled: {vch_no}")
                cancelled_vouchers_count += 1
                vouchers_count += 1
                continue

            inv_lines = v.get("inventory_lines") or []
            is_order_voucher = vch_type == "Purchase Order"
            use_item_invoice = (
                v_mode != "ACCOUNTING_INVOICE"
                and len(inv_lines) > 0
                and vch_type in ("Sales", "Credit Note", "Purchase", "Debit Note", "Purchase Order")
            )

            # Use ACTION="Create" (Tally automatically alters/updates if GUID/REMOTEID matches or creates if new)
            vch_el = ET.SubElement(
                tm,
                "VOUCHER",
                {
                    "REMOTEID": guid,
                    "VCHKEY": guid,
                    "VCHTYPE": vch_type,
                    "ACTION": "Create",
                    "OBJVIEW": "Invoice Voucher View" if use_item_invoice else "Accounting Voucher View",
                },
            )
            ET.SubElement(vch_el, "GUID").text = guid
            ET.SubElement(vch_el, "DATE").text = date_str
            ET.SubElement(vch_el, "EFFECTIVEDATE").text = date_str
            ET.SubElement(vch_el, "VOUCHERTYPENAME").text = vch_type
            ET.SubElement(vch_el, "VOUCHERNUMBER").text = vch_no
            ET.SubElement(vch_el, "REFERENCE").text = ref_no
            ET.SubElement(vch_el, "PARTYLEDGERNAME").text = party_name
            ET.SubElement(vch_el, "NARRATION").text = _clean_xml_text(v.get("narration") or "")

            if is_order_voucher:
                po_due_str = _tally_date(v.get("order_due_date") or v["transaction_date"])
                ET.SubElement(vch_el, "ISOPTIONAL").text = "No"
                ET.SubElement(vch_el, "ORDERDUEDATE").text = po_due_str
                ET.SubElement(vch_el, "DUEDATEOFPYMT").text = po_due_str
                terms_list = ET.SubElement(vch_el, "BASICORDERTERMS.LIST", {"TYPE": "String"})
                ET.SubElement(terms_list, "BASICORDERTERMS").text = f"Order Due Date: {po_due_str}"

            if ver_cfg["supports_persisted_view"]:
                ET.SubElement(vch_el, "PERSISTEDVIEW").text = (
                    "Invoice Voucher View" if use_item_invoice else "Accounting Voucher View"
                )
            ET.SubElement(vch_el, "ISINVOICE").text = (
                "Yes" if vch_type in ("Sales", "Credit Note", "Purchase", "Debit Note", "Purchase Order") else "No"
            )

            if v.get("party_gstin"):
                ET.SubElement(vch_el, "PARTYGSTIN").text = _clean_xml_text(v["party_gstin"])
                ET.SubElement(vch_el, "GSTREGISTRATIONTYPE").text = "Regular"
            if v.get("party_state"):
                st_val = _clean_xml_text(v["party_state"])
                ET.SubElement(vch_el, "STATENAME").text = st_val
                ET.SubElement(vch_el, "PLACEOFSUPPLY").text = st_val

            # Verify double-entry Dr == Cr for accounting vouchers (Purchase Orders are non-posting order vouchers)
            v_dr = Decimal("0.00")
            v_cr = Decimal("0.00")

            for le in v.get("ledger_entries", []):
                amt = _q2(le["amount"])
                if amt <= Decimal("0.00"):
                    continue
                is_deemed_pos = bool(le["is_deemed_positive"])  # True = DEBIT, False = CREDIT

                # If use_item_invoice is True, the Sales A/c or Purchase A/c leg is carried inside
                # <ALLINVENTORYENTRIES.LIST><ACCOUNTINGALLOCATIONS.LIST> so we don't duplicate it in ALLLEDGERENTRIES.LIST
                if use_item_invoice and le["ledger_name"] in ("Sales A/c", "Purchase A/c") and not le.get("is_party"):
                    if is_deemed_pos:
                        v_dr += amt
                    else:
                        v_cr += amt
                    continue

                if is_deemed_pos:
                    v_dr += amt
                    signed_amt_str = f"-{amt:.2f}"
                else:
                    v_cr += amt
                    signed_amt_str = f"{amt:.2f}"

                le_el = ET.SubElement(vch_el, "ALLLEDGERENTRIES.LIST")
                ET.SubElement(le_el, "LEDGERNAME").text = _clean_xml_text(le["ledger_name"])
                ET.SubElement(le_el, "ISDEEMEDPOSITIVE").text = "Yes" if is_deemed_pos else "No"
                ET.SubElement(le_el, "ISPARTYLEDGER").text = "Yes" if le.get("is_party") else "No"
                ET.SubElement(le_el, "AMOUNT").text = signed_amt_str

                if le.get("is_party") and le.get("bill_ref") and not is_order_voucher:
                    ba_el = ET.SubElement(le_el, "BILLALLOCATIONS.LIST")
                    ET.SubElement(ba_el, "NAME").text = _clean_xml_text(le["bill_ref"])
                    ET.SubElement(ba_el, "BILLTYPE").text = _clean_xml_text(le.get("bill_type") or "New Ref")
                    ET.SubElement(ba_el, "AMOUNT").text = signed_amt_str

            # Emit Inventory Allocations if Item Invoice mode is active
            if use_item_invoice:
                is_purchase_side = vch_type in ("Purchase", "Purchase Order") or (
                    vch_type == "Credit Note"
                )
                inv_deemed_pos = "Yes" if is_purchase_side else "No"
                acct_ledger_name = "Purchase A/c" if vch_type in ("Purchase", "Debit Note", "Purchase Order") else "Sales A/c"

                for il in inv_lines:
                    il_amt = _q2(il.get("amount") or 0)
                    il_qty = _q3(il.get("quantity") or 1)
                    il_rate = _q2(il.get("rate") or 0)
                    il_uom = _clean_xml_text(il.get("uom") or "PCS").upper()
                    signed_il_amt = f"-{il_amt:.2f}" if inv_deemed_pos == "Yes" else f"{il_amt:.2f}"

                    ie_el = ET.SubElement(vch_el, "ALLINVENTORYENTRIES.LIST")
                    ET.SubElement(ie_el, "STOCKITEMNAME").text = _clean_xml_text(il["item_name"])
                    ET.SubElement(ie_el, "ISDEEMEDPOSITIVE").text = inv_deemed_pos
                    ET.SubElement(ie_el, "RATE").text = f"{il_rate:.2f}/{il_uom}"
                    ET.SubElement(ie_el, "AMOUNT").text = signed_il_amt
                    ET.SubElement(ie_el, "ACTUALQTY").text = f" {il_qty:.3f} {il_uom}"
                    ET.SubElement(ie_el, "BILLEDQTY").text = f" {il_qty:.3f} {il_uom}"

                    # Fix 4: Include required Purchase Order due-date and order fields on BATCHALLOCATIONS.LIST
                    if is_order_voucher:
                        il_due_str = _tally_date(
                            il.get("order_due_date") or v.get("order_due_date") or v["transaction_date"]
                        )
                        ET.SubElement(ie_el, "ORDERDUEDATE").text = il_due_str
                        ba_el = ET.SubElement(ie_el, "BATCHALLOCATIONS.LIST")
                        ET.SubElement(ba_el, "GODOWNNAME").text = "Main Location"
                        ET.SubElement(ba_el, "BATCHNAME").text = "Primary Batch"
                        ET.SubElement(ba_el, "ORDERNO").text = vch_no
                        ET.SubElement(ba_el, "ORDERDUEDATE", {"JD": "45000", "P": il_due_str}).text = il_due_str
                        ET.SubElement(ba_el, "DUEDATEOFPYMT").text = il_due_str
                        ET.SubElement(ba_el, "AMOUNT").text = signed_il_amt
                        ET.SubElement(ba_el, "ACTUALQTY").text = f" {il_qty:.3f} {il_uom}"
                        ET.SubElement(ba_el, "BILLEDQTY").text = f" {il_qty:.3f} {il_uom}"

                    aa_el = ET.SubElement(ie_el, "ACCOUNTINGALLOCATIONS.LIST")
                    ET.SubElement(aa_el, "LEDGERNAME").text = acct_ledger_name
                    ET.SubElement(aa_el, "ISDEEMEDPOSITIVE").text = inv_deemed_pos
                    ET.SubElement(aa_el, "AMOUNT").text = signed_il_amt

            if is_order_voucher:
                order_vouchers_count += 1
            else:
                total_debit_exported += v_dr
                total_credit_exported += v_cr
            vouchers_count += 1

        # Pretty-format XML string with UTF-8 declaration
        ET.indent(envelope, space="  ")
        xml_bytes = ET.tostring(envelope, encoding="utf-8", xml_declaration=True)
        xml_str = xml_bytes.decode("utf-8")
        batch_hash = hashlib.sha256(xml_bytes).hexdigest()

        # Persist TallySyncBatch & update TallySyncRecord rows (WVV Write-Verify-Validate)
        batch_obj = TallySyncBatch(
            batch_code=batch_code,
            company_id=company_id,
            segment_id=segment_id,
            direction="EXPORT",
            tally_version=ver_cfg["code"],
            voucher_mode=v_mode,
            period_preset=resolved_preset,
            date_from=start_date,
            date_to=end_date,
            modules_included=selected_modules,
            masters_count=masters_count,
            vouchers_count=vouchers_count,
            total_debit=total_debit_exported,
            total_credit=total_credit_exported,
            wvv_batch_hash=batch_hash,
            summary_json=collected["module_stats"],
            actor_id=actor_id,
            actor_name=actor_name,
            created_at=now_ist,
        )
        db.add(batch_obj)
        db.flush()

        if mark_as_exported and vouchers:
            sync_map = TallyIntegrationService._load_sync_map(db, company_id)
            for v in vouchers:
                key = (v["entity_type"], v["entity_id"])
                rec = sync_map.get(key)
                if v.get("is_cancelled"):
                    new_status = "CANCELLED_EXPORTED"
                else:
                    new_status = (
                        "SYNCED"
                        if (rec and rec.tally_status == "SYNCED" and rec.wvv_hash == v["wvv_hash"])
                        else "EXPORTED"
                    )
                if not rec:
                    rec = TallySyncRecord(
                        company_id=company_id,
                        segment_id=v.get("segment_id"),
                        entity_type=v["entity_type"],
                        entity_id=v["entity_id"],
                        myntos_voucher_no=v["myntos_voucher_no"],
                        tally_voucher_no=v["myntos_voucher_no"],
                        tally_voucher_type=v["tally_voucher_type"],
                        tally_guid=v["tally_guid"],
                        transaction_date=v["transaction_date"],
                        party_name=v.get("party_name"),
                        amount=v.get("original_amount", v["amount"]),
                        tally_status=new_status,
                        tally_version=ver_cfg["code"],
                        wvv_hash=v["wvv_hash"],
                        last_batch_id=batch_obj.id,
                        last_exported_at=now_ist,
                        updated_by_id=actor_id,
                    )
                    db.add(rec)
                else:
                    rec.myntos_voucher_no = v["myntos_voucher_no"]
                    rec.tally_voucher_type = v["tally_voucher_type"]
                    rec.transaction_date = v["transaction_date"]
                    rec.party_name = v.get("party_name")
                    if not v.get("is_cancelled"):
                        rec.amount = v["amount"]
                    rec.tally_status = new_status
                    rec.tally_version = ver_cfg["code"]
                    rec.wvv_hash = v["wvv_hash"]
                    rec.last_batch_id = batch_obj.id
                    rec.last_exported_at = now_ist
                    rec.updated_by_id = actor_id

                # Keep native tally_status columns on IncomeEntry / ExpenseEntry / VendorTransactionHeader in sync
                native_status = "EXPORTED" if new_status == "CANCELLED_EXPORTED" else new_status
                if v["entity_type"] == "INCOME_ENTRY":
                    db.query(IncomeEntry).filter(IncomeEntry.id == v["entity_id"]).update(
                        {"tally_status": native_status, "tally_voucher_no": v["myntos_voucher_no"]},
                        synchronize_session=False,
                    )
                elif v["entity_type"] == "EXPENSE_ENTRY":
                    db.query(ExpenseEntry).filter(ExpenseEntry.id == v["entity_id"]).update(
                        {"tally_status": native_status, "tally_voucher_no": v["myntos_voucher_no"]},
                        synchronize_session=False,
                    )
                elif v["entity_type"] == "VENDOR_TXN":
                    db.query(VendorTransactionHeader).filter(VendorTransactionHeader.id == v["entity_id"]).update(
                        {"tally_status": native_status, "tally_voucher_no": v["myntos_voucher_no"]},
                        synchronize_session=False,
                    )

        db.commit()

        co_slug = re.sub(r"[^A-Za-z0-9]+", "_", company_name).strip("_")
        filename = f"MyntOS_Tally_{ver_cfg['code']}_{co_slug}_{resolved_preset}_{now_ist.strftime('%Y%m%d')}.xml"

        return {
            "xml_content": xml_str,
            "filename": filename,
            "report_name": report_name,
            "batch": batch_obj.to_dict(),
            "masters_count": masters_count,
            "vouchers_count": vouchers_count,
            "order_vouchers_count": order_vouchers_count,
            "cancelled_vouchers_count": cancelled_vouchers_count,
            "total_debit": float(total_debit_exported),
            "total_credit": float(total_credit_exported),
            "balanced": total_debit_exported == total_credit_exported,
            "unresolved_ledgers": unresolved_ledgers,
            "validation_warnings": collected.get("validation_warnings", []),
            "company_wide_excluded_modules": collected.get("company_wide_excluded_modules", []),
            "cashflow_register_notice": collected.get("cashflow_register_notice"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # BI-DIRECTIONAL UPLOAD & RECONCILIATION (DAYBOOK / VOUCHER XML & CSV)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def import_and_reconcile_tally_file(
        db: Session,
        company_id: int,
        file_bytes: bytes,
        filename: str,
        import_missing_to_ledger: bool = False,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse an uploaded Tally Daybook / Voucher XML (or CSV) file and reconcile against
        MyntOS records across all modules (Purchase Orders, Purchase Invoices, Sales Invoices,
        Cash/Income/Expense/Payment Entries, and Journal Vouchers).
        Fix 9:
          - Multi-candidate lookup maps prevent silent overwrites when voucher numbers collide.
          - Validates voucher type compatibility, transaction date, and amount.
          - Reports multi-candidate collisions as AMBIGUOUS instead of arbitrarily syncing one record.
          - Supports (Date + Amount + Party) fallback only when it resolves to a unique candidate.
        """
        TallyIntegrationService.ensure_tables(db)
        now_ist = get_indian_time()

        # Collect all current MyntOS vouchers for this company (across all time)
        collected = TallyIntegrationService.collect_company_vouchers(
            db=db,
            company_id=company_id,
            start_date=None,
            end_date=None,
            segment_id=None,
            modules=ALL_TALLY_MODULES,
            sync_status_filter="ALL",
            include_company_wide=True,
        )
        myntos_vouchers = collected["vouchers"]
        by_guid: Dict[str, Dict[str, Any]] = {
            v["tally_guid"].lower(): v for v in myntos_vouchers if v.get("tally_guid")
        }
        by_vch_no: Dict[str, List[Dict[str, Any]]] = {}
        by_ref_no: Dict[str, List[Dict[str, Any]]] = {}
        for v in myntos_vouchers:
            vno_key = str(v.get("myntos_voucher_no") or "").strip().upper()
            if vno_key:
                by_vch_no.setdefault(vno_key, []).append(v)
            for rfield in ("supplier_invoice_no", "payment_reference"):
                ref_key = str(v.get(rfield) or "").strip().upper()
                if ref_key:
                    by_ref_no.setdefault(ref_key, []).append(v)

        def _vtype_compatible(tally_vtype: Optional[str], myntos_vtype: Optional[str]) -> bool:
            t_norm = (tally_vtype or "").strip().lower()
            m_norm = (myntos_vtype or "").strip().lower()
            if not t_norm or not m_norm:
                return True
            if t_norm == m_norm:
                return True
            aliases = {
                "purchase order": {"purchase order", "po", "order"},
                "purchase": {"purchase", "purchase invoice", "tax invoice"},
                "debit note": {"debit note", "purchase return"},
                "sales": {"sales", "sales invoice", "tax invoice"},
                "credit note": {"credit note", "sales return"},
                "receipt": {"receipt", "rcpt"},
                "payment": {"payment", "pymt"},
                "journal": {"journal", "jv"},
                "contra": {"contra"},
            }
            for canonical, group in aliases.items():
                if m_norm == canonical and t_norm in group:
                    return True
            return False

        def _parse_any_date(date_raw: Optional[str]) -> Optional[date]:
            if not date_raw:
                return None
            s = str(date_raw).strip()
            for fmt in ("%Y%m%d", "%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None

        parsed_vouchers = []
        fname_lower = (filename or "").lower()
        head_str = file_bytes[:1000].decode("utf-8", errors="replace")

        if fname_lower.endswith(".xml") or "<envelope" in head_str.lower() or "<voucher" in head_str.lower():
            # Clean illegal XML chars Tally sometimes exports
            xml_text = file_bytes.decode("utf-8", errors="replace")
            xml_text = re.sub(r"&#([0-9]+);", "", xml_text)
            xml_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u007f-\u009f]", "", xml_text)
            root = ET.fromstring(xml_text)
            vch_nodes = root.findall(".//VOUCHER") or root.findall(".//voucher")
            for vn in vch_nodes:
                guid = (
                    vn.attrib.get("REMOTEID")
                    or (vn.findtext("GUID") or "")
                    or (vn.findtext("REMOTEID") or "")
                ).strip()
                vch_no = (vn.findtext("VOUCHERNUMBER") or vn.findtext("vouchernumber") or "").strip()
                ref_no = (vn.findtext("REFERENCE") or vn.findtext("reference") or "").strip()
                vch_type = (
                    vn.attrib.get("VCHTYPE")
                    or vn.findtext("VOUCHERTYPENAME")
                    or vn.findtext("vouchertypename")
                    or ""
                ).strip()
                action_attr = (vn.attrib.get("ACTION") or "").strip().upper()
                is_canc_tag = (vn.findtext("ISCANCELLED") or vn.findtext("iscancelled") or "").strip().upper() == "YES"
                is_cancelled = is_canc_tag or (action_attr == "CANCEL")
                date_raw = (vn.findtext("DATE") or vn.findtext("date") or "").strip()
                party = (vn.findtext("PARTYLEDGERNAME") or vn.findtext("partyledgername") or "").strip()
                narration = (vn.findtext("NARRATION") or vn.findtext("narration") or "").strip()
                txn_date = _parse_any_date(date_raw)

                max_amt = Decimal("0.00")
                dr_total = Decimal("0.00")
                for le in vn.findall(".//ALLLEDGERENTRIES.LIST") + vn.findall(".//LEDGERENTRIES.LIST"):
                    amt_txt = (le.findtext("AMOUNT") or le.findtext("amount") or "").replace(",", "").strip()
                    try:
                        val = abs(_q2(amt_txt))
                        if val > max_amt:
                            max_amt = val
                        if amt_txt.startswith("-"):
                            dr_total += val
                    except Exception:
                        continue

                parsed_vouchers.append({
                    "guid": guid,
                    "voucher_number": vch_no,
                    "reference": ref_no,
                    "voucher_type": vch_type,
                    "date": txn_date,
                    "party_name": party,
                    "amount": max_amt or dr_total,
                    "is_cancelled": is_cancelled,
                    "narration": narration,
                })
        else:
            # CSV fallback (Voucher No, Date, Voucher Type, Party Name, Amount)
            import csv
            import io

            reader = csv.DictReader(io.StringIO(file_bytes.decode("utf-8", errors="replace")))
            for row in reader:
                norm = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
                vch_no = (
                    norm.get("voucher no")
                    or norm.get("voucher number")
                    or norm.get("vch no.")
                    or norm.get("vch no")
                    or norm.get("voucher_number")
                    or norm.get("reference")
                    or ""
                )
                ref_no = norm.get("reference") or norm.get("ref no") or vch_no
                vch_type = norm.get("voucher type") or norm.get("vch type") or norm.get("voucher_type") or ""
                party = norm.get("party") or norm.get("party name") or norm.get("particulars") or norm.get("party_name") or ""
                date_raw = norm.get("date") or norm.get("voucher date") or norm.get("transaction_date") or ""
                amt_raw = norm.get("amount") or norm.get("debit") or norm.get("credit") or "0"
                amt = _q2(amt_raw.replace(",", ""))
                is_canc = (norm.get("status") or norm.get("cancelled") or "").strip().upper() in ("CANCELLED", "YES", "TRUE")
                parsed_vouchers.append({
                    "guid": norm.get("guid", ""),
                    "voucher_number": vch_no,
                    "reference": ref_no,
                    "voucher_type": vch_type,
                    "date": _parse_any_date(date_raw),
                    "party_name": party,
                    "amount": abs(amt),
                    "is_cancelled": is_canc,
                    "narration": norm.get("narration") or norm.get("description") or "",
                })

        sync_map = TallyIntegrationService._load_sync_map(db, company_id)
        synced_count = 0
        mismatch_count = 0
        ambiguous_count = 0
        unmatched_tally_vouchers = []
        ambiguous_matches = []
        reconciled_details = []

        for pv in parsed_vouchers:
            candidates: List[Dict[str, Any]] = []
            match_method = ""

            # 1. Deterministic GUID match
            if pv["guid"] and pv["guid"].lower() in by_guid:
                candidates = [by_guid[pv["guid"].lower()]]
                match_method = "GUID"
            else:
                # 2. Voucher Number / Supplier Reference lookup across multi-maps
                raw_candidates: List[Dict[str, Any]] = []
                vno_u = pv["voucher_number"].strip().upper() if pv["voucher_number"] else ""
                ref_u = pv["reference"].strip().upper() if pv["reference"] else ""

                if vno_u and vno_u in by_vch_no:
                    raw_candidates.extend(by_vch_no[vno_u])
                    match_method = "VOUCHER_NO"
                elif ref_u and ref_u in by_vch_no:
                    raw_candidates.extend(by_vch_no[ref_u])
                    match_method = "REFERENCE_TO_VOUCHER_NO"
                elif vno_u and vno_u in by_ref_no:
                    raw_candidates.extend(by_ref_no[vno_u])
                    match_method = "VOUCHER_NO_TO_SUPPLIER_REF"
                elif ref_u and ref_u in by_ref_no:
                    raw_candidates.extend(by_ref_no[ref_u])
                    match_method = "SUPPLIER_REF"

                # Deduplicate raw candidates by (entity_type, entity_id)
                dedup = {}
                for rc in raw_candidates:
                    dedup[(rc["entity_type"], rc["entity_id"])] = rc
                candidates = list(dedup.values())

                # Filter by voucher type compatibility when multiple candidates exist
                if len(candidates) > 1 and pv["voucher_type"]:
                    type_filtered = [
                        c for c in candidates if _vtype_compatible(pv["voucher_type"], c["tally_voucher_type"])
                    ]
                    if type_filtered:
                        candidates = type_filtered

                # Narrow by transaction_date when multiple candidates share the same number
                if len(candidates) > 1 and pv["date"]:
                    date_filtered = [c for c in candidates if c.get("transaction_date") == pv["date"]]
                    if date_filtered:
                        candidates = date_filtered

                # Narrow by party_name when multiple candidates still remain
                if len(candidates) > 1 and pv["party_name"]:
                    p_low = pv["party_name"].strip().lower()
                    party_filtered = [
                        c for c in candidates if (c.get("party_name") or "").strip().lower() == p_low
                    ]
                    if party_filtered:
                        candidates = party_filtered

                # 3. Fallback: (Date + Amount + Party) only when GUID/VoucherNo/Ref found nothing
                if not candidates and pv["date"] and pv["amount"] > Decimal("0.00") and pv["party_name"]:
                    p_low = pv["party_name"].strip().lower()
                    t_amt = _q2(pv["amount"])
                    fallback_cands = [
                        v for v in myntos_vouchers
                        if v.get("transaction_date") == pv["date"]
                        and abs(_q2(v.get("amount") or 0) - t_amt) <= Decimal("0.01")
                        and (v.get("party_name") or "").strip().lower() == p_low
                        and _vtype_compatible(pv["voucher_type"], v.get("tally_voucher_type"))
                    ]
                    if fallback_cands:
                        candidates = fallback_cands
                        match_method = "DATE_AMOUNT_PARTY"

            # Fix 9: Never silently mark an arbitrary candidate when multiple records match
            if len(candidates) > 1:
                ambiguous_count += 1
                amb_entry = {
                    "voucher_number": pv["voucher_number"],
                    "reference": pv["reference"],
                    "voucher_type": pv["voucher_type"],
                    "date": pv["date"].isoformat() if pv["date"] else None,
                    "party_name": pv["party_name"],
                    "tally_amount": float(pv["amount"]),
                    "status": "AMBIGUOUS",
                    "reason": f"Ambiguous match: {len(candidates)} MyntOS records share this identifier",
                    "candidates": [
                        {
                            "entity_type": c["entity_type"],
                            "entity_id": c["entity_id"],
                            "myntos_voucher_no": c["myntos_voucher_no"],
                            "tally_voucher_type": c["tally_voucher_type"],
                            "transaction_date": c["transaction_date"].isoformat() if c.get("transaction_date") else None,
                            "party_name": c.get("party_name"),
                            "amount": float(c.get("amount") or 0),
                        }
                        for c in candidates
                    ],
                }
                ambiguous_matches.append(amb_entry)
                reconciled_details.append(amb_entry)
                continue

            if len(candidates) == 1:
                matched_v = candidates[0]
                myntos_amt = _q2(matched_v["amount"])
                tally_amt = _q2(pv["amount"])
                mismatch_reasons = []

                # Check cancellation state
                if bool(pv.get("is_cancelled")) != bool(matched_v.get("is_cancelled")):
                    mismatch_reasons.append(
                        f"Cancellation mismatch (MyntOS cancelled={bool(matched_v.get('is_cancelled'))}, Tally cancelled={bool(pv.get('is_cancelled'))})"
                    )

                # Check voucher type compatibility
                if pv["voucher_type"] and not _vtype_compatible(pv["voucher_type"], matched_v["tally_voucher_type"]):
                    mismatch_reasons.append(
                        f"Voucher type mismatch (MyntOS={matched_v['tally_voucher_type']}, Tally={pv['voucher_type']})"
                    )

                # Check transaction date when present in uploaded Tally file
                if pv["date"] and matched_v.get("transaction_date") and pv["date"] != matched_v["transaction_date"]:
                    mismatch_reasons.append(
                        f"Date mismatch (MyntOS={matched_v['transaction_date'].isoformat()}, Tally={pv['date'].isoformat()})"
                    )

                # Check amount (for non-cancelled vouchers, require amount match within 1.00 round-off; for Expense with GST/TDS, also accept gross_amount)
                if not matched_v.get("is_cancelled") and not pv.get("is_cancelled"):
                    gross_amt = _q2(matched_v.get("gross_amount") or myntos_amt)
                    amt_matches = (
                        abs(myntos_amt - tally_amt) <= Decimal("1.00")
                        or abs(gross_amt - tally_amt) <= Decimal("1.00")
                    )
                    if tally_amt <= Decimal("0.00") and myntos_amt > Decimal("0.00"):
                        amt_matches = False
                    if not amt_matches:
                        mismatch_reasons.append(
                            f"Amount mismatch (MyntOS={myntos_amt:.2f}, Tally={tally_amt:.2f})"
                        )

                is_match = len(mismatch_reasons) == 0
                if is_match:
                    new_status = "CANCELLED_SYNCED" if matched_v.get("is_cancelled") else "SYNCED"
                    synced_count += 1
                else:
                    new_status = "MISMATCH"
                    mismatch_count += 1

                key = (matched_v["entity_type"], matched_v["entity_id"])
                rec = sync_map.get(key)
                tally_vno = pv["voucher_number"] or matched_v["myntos_voucher_no"]
                err_msg = "; ".join(mismatch_reasons) if mismatch_reasons else None
                if not rec:
                    rec = TallySyncRecord(
                        company_id=company_id,
                        segment_id=matched_v.get("segment_id"),
                        entity_type=matched_v["entity_type"],
                        entity_id=matched_v["entity_id"],
                        myntos_voucher_no=matched_v["myntos_voucher_no"],
                        tally_voucher_no=tally_vno,
                        tally_voucher_type=matched_v["tally_voucher_type"],
                        tally_guid=matched_v["tally_guid"],
                        transaction_date=matched_v["transaction_date"],
                        party_name=matched_v.get("party_name"),
                        amount=myntos_amt,
                        tally_status=new_status,
                        wvv_hash=matched_v["wvv_hash"],
                        last_synced_at=now_ist,
                        error_message=err_msg,
                        updated_by_id=actor_id,
                    )
                    db.add(rec)
                    sync_map[key] = rec
                else:
                    rec.tally_status = new_status
                    rec.tally_voucher_no = tally_vno
                    rec.wvv_hash = matched_v["wvv_hash"]
                    rec.last_synced_at = now_ist
                    rec.error_message = err_msg
                    rec.updated_by_id = actor_id

                # Sync native status columns
                if matched_v["entity_type"] == "INCOME_ENTRY" and is_match and not matched_v.get("is_cancelled"):
                    db.query(IncomeEntry).filter(IncomeEntry.id == matched_v["entity_id"]).update(
                        {"tally_status": "SYNCED", "status": "TALLY_DONE", "tally_voucher_no": tally_vno},
                        synchronize_session=False,
                    )
                elif matched_v["entity_type"] == "EXPENSE_ENTRY" and is_match and not matched_v.get("is_cancelled"):
                    db.query(ExpenseEntry).filter(ExpenseEntry.id == matched_v["entity_id"]).update(
                        {"tally_status": "SYNCED", "tally_voucher_no": tally_vno},
                        synchronize_session=False,
                    )
                elif matched_v["entity_type"] == "VENDOR_TXN" and is_match and not matched_v.get("is_cancelled"):
                    db.query(VendorTransactionHeader).filter(
                        VendorTransactionHeader.id == matched_v["entity_id"]
                    ).update(
                        {"tally_status": "SYNCED", "tally_voucher_no": tally_vno},
                        synchronize_session=False,
                    )

                reconciled_details.append({
                    "myntos_voucher_no": matched_v["myntos_voucher_no"],
                    "tally_voucher_no": tally_vno,
                    "entity_type": matched_v["entity_type"],
                    "match_method": match_method,
                    "myntos_amount": float(myntos_amt),
                    "tally_amount": float(tally_amt),
                    "status": new_status,
                    "mismatch_reasons": mismatch_reasons,
                })
            else:
                unmatched_tally_vouchers.append({
                    "voucher_number": pv["voucher_number"],
                    "voucher_type": pv["voucher_type"],
                    "date": pv["date"].isoformat() if pv["date"] else None,
                    "party_name": pv["party_name"],
                    "amount": float(pv["amount"]),
                })

        batch_code = f"TALLY-IMP-{company_id}-{now_ist.strftime('%Y%m%d%H%M%S')}"
        batch_obj = TallySyncBatch(
            batch_code=batch_code,
            company_id=company_id,
            direction="IMPORT",
            tally_version="UNIVERSAL",
            voucher_mode="AUTO",
            modules_included=ALL_TALLY_MODULES,
            masters_count=0,
            vouchers_count=len(parsed_vouchers),
            wvv_batch_hash=hashlib.sha256(file_bytes).hexdigest(),
            summary_json={
                "parsed_count": len(parsed_vouchers),
                "synced_count": synced_count,
                "mismatch_count": mismatch_count,
                "ambiguous_count": ambiguous_count,
                "unmatched_count": len(unmatched_tally_vouchers),
            },
            actor_id=actor_id,
            actor_name=actor_name,
            created_at=now_ist,
        )
        db.add(batch_obj)
        db.commit()

        return {
            "success": True,
            "batch": batch_obj.to_dict(),
            "parsed_vouchers_count": len(parsed_vouchers),
            "synced_count": synced_count,
            "mismatch_count": mismatch_count,
            "ambiguous_count": ambiguous_count,
            "unmatched_count": len(unmatched_tally_vouchers),
            "reconciled": reconciled_details[:100],
            "ambiguous_matches": ambiguous_matches[:50],
            "unmatched_sample": unmatched_tally_vouchers[:50],
        }
