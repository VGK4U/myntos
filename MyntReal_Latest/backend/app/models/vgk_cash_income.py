"""
VGK Cash Income System (DC Protocol Mar 2026)

Two parallel tracks when a VGK deal earns commission:
  Track 1 — VGK Discount Credits (points): DEBITED from member's points balance
  Track 2 — VGK Cash Income (₹):           CREDITED to member's cash wallet

Trigger: CRM lead status = 'completed' AND deal_value_balance = 0
Approval chain:
  DRAFT   → Sales staff confirms   → PENDING  (points debited, cash credited to wallet)
  PENDING → Accounts staff releases → RELEASED (8% admin + 2% TDS deducted, net to withdrawable)

Answer B for insufficient points: income still credited, points debit = 0 (waived).
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date, Text,
    ForeignKey, Index, UniqueConstraint, CheckConstraint, SmallInteger, text
)
from app.models.base import Base, BaseModel, get_indian_time


class VGKCashIncomeEntry(BaseModel):
    """
    VGK Cash Income Ledger — one row per (lead, partner, level).
    Created as DRAFT when lead is fully paid and completed.
    Confirmed by Sales → Accounts releases payout.
    """
    __tablename__ = 'vgk_cash_income_entries'

    id                     = Column(Integer, primary_key=True, index=True)
    company_id             = Column(Integer, ForeignKey('associated_companies.id'), nullable=False, index=True)
    entry_number           = Column(String(30), nullable=False)

    partner_id             = Column(Integer, ForeignKey('official_partners.id', ondelete='CASCADE'), nullable=False, index=True)
    source_lead_id         = Column(Integer, ForeignKey('crm_leads.id', ondelete='SET NULL'), nullable=True, index=True)
    category_id            = Column(Integer, ForeignKey('signup_categories.id', ondelete='SET NULL'), nullable=True)

    level                  = Column(SmallInteger, nullable=False)
    income_date            = Column(Date, nullable=True)

    deal_value_total       = Column(Numeric(15, 2), nullable=False, default=0)
    deal_value_excl_tax    = Column(Numeric(15, 2), nullable=False, default=0)
    confirmed_final_value  = Column(Numeric(15, 2), nullable=True)   # snapshot of lead.confirmed_final_value at draft time
    solar_value            = Column(Numeric(15, 2), nullable=True)   # DC-SOLAR-VALUE-001: snapshot of lead.solar_value — actual commission base
    commission_pct         = Column(Numeric(5, 2),  nullable=False, default=0)
    commission_amount      = Column(Numeric(15, 2), nullable=False, default=0)

    points_debit_required  = Column(Numeric(15, 2), nullable=False, default=0)
    points_actually_debited= Column(Numeric(15, 2), nullable=False, default=0)

    status                 = Column(String(20), nullable=False, default='DRAFT')

    admin_charges          = Column(Numeric(15, 2), nullable=False, default=0)
    tds_amount             = Column(Numeric(15, 2), nullable=False, default=0)
    net_payout             = Column(Numeric(15, 2), nullable=False, default=0)

    confirmed_by_id        = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    confirmed_at           = Column(DateTime, nullable=True)
    released_by_id         = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    released_at            = Column(DateTime, nullable=True)

    # DC-VGK-STAGE1-001: Stage 1 Approval — EA/supervisor approves before accounts marks paid
    stage_1_approved_at    = Column(DateTime, nullable=True)
    stage_1_approved_by    = Column(String(120), nullable=True)

    rejection_reason       = Column(Text, nullable=True)
    notes                  = Column(Text, nullable=True)

    # DC-HANDLER-CHANGE-INCOME-001 (Jul 2026): handler/source correction columns
    cancelled_reason       = Column(Text, nullable=True)           # "Handler Changed — source updated from X to Y"
    adjustment_ref_entry_id= Column(Integer, ForeignKey('vgk_cash_income_entries.id', ondelete='SET NULL'), nullable=True)
    adjustment_reason      = Column(Text, nullable=True)           # "Adjusted with Lead #N — handler changed from X to Y"

    # DC-VGK-INCOME-UNIFIED-001 (May 2026): unified state-machine + ledger postings
    kind                   = Column(String(20), nullable=False, default='COMMISSION')          # COMMISSION | ADVANCE | ADJUSTMENT
    paid_by_id             = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    paid_at                = Column(DateTime, nullable=True)
    payment_utr            = Column(String(80),  nullable=True)
    payment_mode           = Column(String(20),  nullable=True)                                  # BANK | CASH
    paid_bank_ledger_id    = Column(Integer, ForeignKey('account_ledger_masters.id', ondelete='SET NULL'), nullable=True)
    paid_cash_staff_id     = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    skip_reason            = Column(Text, nullable=True)
    ledger_posted          = Column(Boolean, nullable=False, default=False)

    created_at             = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at             = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)

    __table_args__ = (
        UniqueConstraint('company_id', 'entry_number', name='uq_vgk_cash_income_entry_number'),
        # DC-ADV-CONSTRAINT-FIX-001: old level-only constraint dropped (see dc_migrations key vgk_adv_constraint_fix_20260706)
        # Replaced by uq_vgk_cash_income_lead_partner_level_kind (includes kind) to allow ADVANCE+COMMISSION at same level.
        CheckConstraint("status IN ('DRAFT','PENDING','RELEASED','STAGE1_APPROVED','PAID','CANCELLED')", name='vgk_cash_income_status_check'),
        CheckConstraint("kind IN ('COMMISSION','ADVANCE','BRAND_ADVANCE','BRAND_COMMISSION','SENIOR_COMM','SLAB_BONUS','ADJUSTMENT','DVR_ADVANCE','EXTRA_COMMISSION')", name='vgk_cash_income_kind_check'),
        CheckConstraint("payment_mode IS NULL OR payment_mode IN ('BANK','CASH')", name='vgk_cash_income_paymode_check'),
        CheckConstraint('level BETWEEN 0 AND 10', name='vgk_cash_income_level_check'),
        Index('idx_vgk_cash_income_partner_status', 'company_id', 'partner_id', 'status'),
        Index('idx_vgk_cash_income_lead',           'company_id', 'source_lead_id'),
        Index('idx_vci_co_kind_status',             'company_id', 'kind', 'status'),
    )

    def __repr__(self):
        return f'<VGKCashIncomeEntry {self.entry_number}: partner={self.partner_id} L{self.level} {self.status}>'

    def to_dict(self):
        return {
            'id':                      self.id,
            'company_id':              self.company_id,
            'entry_number':            self.entry_number,
            'partner_id':              self.partner_id,
            'source_lead_id':          self.source_lead_id,
            'category_id':             self.category_id,
            'level':                   self.level,
            'deal_value_total':        float(self.deal_value_total or 0),
            'deal_value_excl_tax':     float(self.deal_value_excl_tax or 0),
            'confirmed_final_value':   float(self.confirmed_final_value) if self.confirmed_final_value is not None else None,
            'solar_value':             float(self.solar_value) if self.solar_value is not None else None,
            'commission_pct':          float(self.commission_pct or 0),
            'commission_amount':       float(self.commission_amount or 0),
            'points_debit_required':   float(self.points_debit_required or 0),
            'points_actually_debited': float(self.points_actually_debited or 0),
            'status':                  self.status,
            'admin_charges':           float(self.admin_charges or 0),
            'tds_amount':              float(self.tds_amount or 0),
            'net_payout':              float(self.net_payout or 0),
            'confirmed_by_id':         self.confirmed_by_id,
            'confirmed_at':            self.confirmed_at.isoformat() if self.confirmed_at else None,
            'released_by_id':          self.released_by_id,
            'released_at':             self.released_at.isoformat() if self.released_at else None,
            'stage_1_approved_at':     self.stage_1_approved_at.isoformat() if self.stage_1_approved_at else None,
            'stage_1_approved_by':     self.stage_1_approved_by,
            'rejection_reason':        self.rejection_reason,
            'notes':                   self.notes,
            'kind':                    self.kind or 'COMMISSION',
            'paid_by_id':              self.paid_by_id,
            'paid_at':                 self.paid_at.isoformat() if self.paid_at else None,
            'payment_utr':             self.payment_utr,
            'payment_mode':            self.payment_mode,
            'paid_bank_ledger_id':     self.paid_bank_ledger_id,
            'paid_cash_staff_id':      self.paid_cash_staff_id,
            'skip_reason':             self.skip_reason,
            'ledger_posted':           bool(self.ledger_posted),
            'cancelled_reason':        self.cancelled_reason,
            'adjustment_ref_entry_id': self.adjustment_ref_entry_id,
            'adjustment_reason':       self.adjustment_reason,
            'income_date':             self.income_date.isoformat() if hasattr(self.income_date, 'isoformat') and self.income_date else (str(self.income_date) if self.income_date else None),
            'created_at':              self.created_at.isoformat() if self.created_at else None,
            'updated_at':              self.updated_at.isoformat() if self.updated_at else None,
        }
