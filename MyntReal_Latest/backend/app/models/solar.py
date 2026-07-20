"""
Solar Lead Technical Details Model
DC Protocol (Apr 2026): Stores panel, inverter, cable, earthing, and PO data
for solar lead document generation (Annexure A, C, Commissioning, etc.)
"""
from sqlalchemy import Column, Integer, String, Text, Date, Boolean, Numeric, Index, ForeignKey
from app.models.base import BaseModel


class CRMSolarLeadTech(BaseModel):
    """
    Technical details for a solar lead — 1:1 with crm_leads.
    Stores everything needed to generate all 7 solar documents.
    """
    __tablename__ = 'crm_solar_lead_tech'

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey('crm_leads.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)

    # ── Panel Details ──────────────────────────────────────────────────────────
    panel_make = Column(String(100), nullable=True)           # e.g. "Vikram Solar Limited"
    panel_model = Column(String(100), nullable=True)          # e.g. "M10 Bifacial G2GHCDCR"
    panel_capacity_each_w = Column(Integer, nullable=True)    # e.g. 550
    num_panels = Column(Integer, nullable=True)               # e.g. 6
    panel_serial_numbers = Column(Text, nullable=True)        # comma-separated serial nos (up to 15)
    panel_brand = Column(String(100), nullable=True)          # e.g. "Vikram Solar"
    panel_warranty = Column(String(100), nullable=True)       # e.g. "25 Years"
    panel_type = Column(String(60), nullable=True)            # e.g. "MONO PERC"
    panel_technology = Column(String(60), nullable=True)      # e.g. "Bifacial"
    tilt_angle = Column(String(20), nullable=True)            # e.g. "12°"
    azimuth = Column(String(20), nullable=True)               # e.g. "South"
    cell_manufacturer = Column(String(100), nullable=True)    # panel cell manufacturer
    rfid_position = Column(String(20), nullable=True)         # INSIDE / OUTSIDE

    # ── Inverter Details ───────────────────────────────────────────────────────
    inverter_make = Column(String(100), nullable=True)        # e.g. "GOODWE"
    inverter_brand = Column(String(100), nullable=True)       # e.g. "GOODWE Technologies"
    inverter_model = Column(String(100), nullable=True)       # e.g. "GOODWE 3KW INVERTER"
    inverter_serial_no = Column(String(100), nullable=True)   # e.g. "53000SSA257LX225"
    inverter_warranty = Column(String(100), nullable=True)    # e.g. "5 Years"
    inverter_capacity_kw = Column(String(20), nullable=True)  # e.g. "3KW"
    inverter_type = Column(String(60), nullable=True)         # e.g. "Grid Tie"
    inverter_efficiency_pct = Column(String(10), nullable=True) # e.g. "98%"
    num_inverters = Column(Integer, nullable=True, default=1)
    grid_voltage = Column(String(20), nullable=True)          # e.g. "240 V"
    string1_voc = Column(String(20), nullable=True)           # e.g. "99.73"
    string2_voc = Column(String(20), nullable=True)
    mppt_type = Column(String(60), nullable=True)             # e.g. "3KW MPPT INVERTER"

    # ── Purchase Order ─────────────────────────────────────────────────────────
    purchase_order_no = Column(String(60), nullable=True)     # e.g. "3SSO25-05957"
    purchase_order_date = Column(Date, nullable=True)
    cell_gst_invoice_no = Column(String(60), nullable=True)   # e.g. "3S25-05543"
    installation_date = Column(Date, nullable=True)           # e.g. 21-03-2026

    # ── Mounting & Structure ───────────────────────────────────────────────────
    mounting_type = Column(String(30), nullable=True, default='Rooftop')
    structure_material = Column(String(100), nullable=True, default='Galvanized MS Module Structure')
    wind_speed_tolerance = Column(String(30), nullable=True, default='150KW/HR')
    surface_finish = Column(String(30), nullable=True, default='GALVANIZED')

    # ── DC Cable ───────────────────────────────────────────────────────────────
    dc_cable_make = Column(String(100), nullable=True, default='Polycab / 4 Square mm')
    dc_cable_sqmm = Column(String(10), nullable=True, default='4')
    dc_cable_length_m = Column(Integer, nullable=True, default=90)

    # ── AC Cable (Inverter to ACDB) ────────────────────────────────────────────
    ac_cable_inv_acdb_make = Column(String(100), nullable=True, default='Polycab / 4 Square mm')
    ac_cable_inv_acdb_sqmm = Column(String(10), nullable=True, default='4')
    ac_cable_inv_acdb_length_m = Column(Integer, nullable=True, default=60)

    # ── AC Cable (ACDB to Electric Panel) ─────────────────────────────────────
    ac_cable_acdb_panel_make = Column(String(100), nullable=True, default='Polycab / 4 Square mm')
    ac_cable_acdb_panel_sqmm = Column(String(10), nullable=True, default='4')
    ac_cable_acdb_panel_length_m = Column(Integer, nullable=True, default=40)

    # ── Junction Boxes & Earthing ──────────────────────────────────────────────
    acdb_count = Column(Integer, nullable=True, default=1)
    dcdb_count = Column(Integer, nullable=True, default=1)
    ac_earthing_nos = Column(Integer, nullable=True, default=1)
    dc_earthing_nos = Column(Integer, nullable=True, default=1)
    la_nos = Column(Integer, nullable=True, default=1)
    earth_resistance_ac = Column(String(20), nullable=True, default='0.5 Ohms')
    earth_resistance_dc = Column(String(20), nullable=True, default='0.5 Ohms')
    earth_resistance_la = Column(String(20), nullable=True, default='0.5 Ohms')
    acdb_ic_voltage = Column(String(20), nullable=True, default='240')
    acdb_og_voltage = Column(String(20), nullable=True, default='240')

    # ── Online Monitoring ─────────────────────────────────────────────────────
    monitoring_user_id = Column(String(100), nullable=True)
    monitoring_password = Column(String(100), nullable=True)

    # ── Fire/Safety ───────────────────────────────────────────────────────────
    danger_board = Column(String(20), nullable=True, default='AVAILABLE')

    # ── Consumer / DISCOM classification (used in Annexure IV) ───────────────
    consumer_category = Column(String(30), nullable=True)   # e.g. 'HT', 'LT'

    # ── Quote tracking ────────────────────────────────────────────────────────
    last_quote_vendor_id = Column(Integer, nullable=True)
    last_quote_kw_size = Column(String(10), nullable=True)
    last_quote_value = Column(Numeric(12, 2), nullable=True)
    last_quote_discount = Column(Numeric(12, 2), nullable=True)
    last_quote_final = Column(Numeric(12, 2), nullable=True)
    last_quote_subsidy = Column(Numeric(12, 2), nullable=True)
    last_quote_ref_no = Column(String(50), nullable=True)
    last_quote_generated_at = Column(Date, nullable=True)

    created_at = Column(String(30), nullable=True)
    updated_at = Column(String(30), nullable=True)

    __table_args__ = (
        Index('idx_crm_solar_tech_lead', 'lead_id'),
        Index('idx_crm_solar_tech_company', 'company_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'lead_id': self.lead_id,
            'company_id': self.company_id,
            'panel_make': self.panel_make,
            'panel_model': self.panel_model,
            'panel_capacity_each_w': self.panel_capacity_each_w,
            'num_panels': self.num_panels,
            'panel_serial_numbers': self.panel_serial_numbers,
            'panel_brand': self.panel_brand,
            'panel_warranty': self.panel_warranty,
            'panel_type': self.panel_type,
            'panel_technology': self.panel_technology,
            'tilt_angle': self.tilt_angle,
            'azimuth': self.azimuth,
            'cell_manufacturer': self.cell_manufacturer,
            'rfid_position': self.rfid_position,
            'inverter_make': self.inverter_make,
            'inverter_brand': self.inverter_brand,
            'inverter_model': self.inverter_model,
            'inverter_serial_no': self.inverter_serial_no,
            'inverter_warranty': self.inverter_warranty,
            'inverter_capacity_kw': self.inverter_capacity_kw,
            'inverter_type': self.inverter_type,
            'inverter_efficiency_pct': self.inverter_efficiency_pct,
            'num_inverters': self.num_inverters,
            'grid_voltage': self.grid_voltage,
            'string1_voc': self.string1_voc,
            'string2_voc': self.string2_voc,
            'mppt_type': self.mppt_type,
            'purchase_order_no': self.purchase_order_no,
            'purchase_order_date': self.purchase_order_date.isoformat() if self.purchase_order_date else None,
            'cell_gst_invoice_no': self.cell_gst_invoice_no,
            'installation_date': self.installation_date.isoformat() if self.installation_date else None,
            'mounting_type': self.mounting_type,
            'structure_material': self.structure_material,
            'wind_speed_tolerance': self.wind_speed_tolerance,
            'surface_finish': self.surface_finish,
            'dc_cable_make': self.dc_cable_make,
            'dc_cable_sqmm': self.dc_cable_sqmm,
            'dc_cable_length_m': self.dc_cable_length_m,
            'ac_cable_inv_acdb_make': self.ac_cable_inv_acdb_make,
            'ac_cable_inv_acdb_sqmm': self.ac_cable_inv_acdb_sqmm,
            'ac_cable_inv_acdb_length_m': self.ac_cable_inv_acdb_length_m,
            'ac_cable_acdb_panel_make': self.ac_cable_acdb_panel_make,
            'ac_cable_acdb_panel_sqmm': self.ac_cable_acdb_panel_sqmm,
            'ac_cable_acdb_panel_length_m': self.ac_cable_acdb_panel_length_m,
            'acdb_count': self.acdb_count,
            'dcdb_count': self.dcdb_count,
            'ac_earthing_nos': self.ac_earthing_nos,
            'dc_earthing_nos': self.dc_earthing_nos,
            'la_nos': self.la_nos,
            'earth_resistance_ac': self.earth_resistance_ac,
            'earth_resistance_dc': self.earth_resistance_dc,
            'earth_resistance_la': self.earth_resistance_la,
            'acdb_ic_voltage': self.acdb_ic_voltage,
            'acdb_og_voltage': self.acdb_og_voltage,
            'monitoring_user_id': self.monitoring_user_id,
            'monitoring_password': self.monitoring_password,
            'danger_board': self.danger_board,
            'consumer_category': self.consumer_category,
            'last_quote_vendor_id': self.last_quote_vendor_id,
            'last_quote_kw_size': self.last_quote_kw_size,
            'last_quote_value': float(self.last_quote_value) if self.last_quote_value is not None else None,
            'last_quote_discount': float(self.last_quote_discount) if self.last_quote_discount is not None else None,
            'last_quote_final': float(self.last_quote_final) if self.last_quote_final is not None else None,
            'last_quote_subsidy': float(self.last_quote_subsidy) if self.last_quote_subsidy is not None else None,
            'last_quote_ref_no': self.last_quote_ref_no,
            'last_quote_generated_at': self.last_quote_generated_at.isoformat() if self.last_quote_generated_at else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
