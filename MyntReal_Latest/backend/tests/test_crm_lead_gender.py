"""
Unit & Integration Tests for CRM Lead Gender & AI Calling Persona Mapping
DC Protocol & VGK4U System Rules Compliant
"""

import pytest
from pydantic import ValidationError

from app.models.crm import CRMLead
from app.api.v1.endpoints.crm import LeadCreate, LeadUpdate, update_lead
from app.services.sheets_leads_service import COL_MAP, row_to_crm_lead
from app.api.v1.endpoints.staff_ai_calling import (
    resolve_persona_from_lead_gender,
    _detect_voice_choice,
    _detect_pref_change,
)


# ─── 1. ALEMBIC MIGRATION INTEGRITY ──────────────────────────────────────────

def test_alembic_migration_chain():
    """Verify migration revision and down_revision form a valid link."""
    import importlib.util
    import os

    migration_file = os.path.join(
        os.path.dirname(__file__), "..", "..", "migrations", "versions", "e2f3a4b5c6d7_add_gender_to_crm_leads.py"
    )
    assert os.path.exists(migration_file), f"Migration file missing: {migration_file}"

    spec = importlib.util.spec_from_file_location("migration_mod", migration_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "e2f3a4b5c6d7"
    assert mod.down_revision == "c9d0e1f2a3b4"
    assert hasattr(mod, "upgrade")
    assert hasattr(mod, "downgrade")


# ─── 2. ORM MODEL INTEGRITY ──────────────────────────────────────────────────

def test_crm_lead_model_has_gender():
    """Verify CRMLead ORM model has gender column and includes it in to_dict()."""
    assert hasattr(CRMLead, "gender"), "CRMLead missing 'gender' column"

    lead = CRMLead(
        id=999,
        tenant_id=1,
        company_id=4,
        name="Test Lead",
        gender="male",
        phone="9876543210"
    )
    assert lead.gender == "male"
    d = lead.to_dict()
    assert "gender" in d
    assert d["gender"] == "male"

    lead_null = CRMLead(
        id=1000,
        tenant_id=1,
        company_id=4,
        name="Null Lead",
        phone="9876543211"
    )
    assert lead_null.gender is None
    d_null = lead_null.to_dict()
    assert "gender" in d_null
    assert d_null["gender"] is None


# ─── 3. PYDANTIC SCHEMAS VALIDATION ──────────────────────────────────────────

def test_lead_create_valid_genders():
    """Verify LeadCreate accepts valid gender values."""
    for val in ("male", "female", "unknown", None):
        lc = LeadCreate(name="Test", gender=val)
        assert lc.gender == val

    # Test case-insensitivity and stripping
    lc_upper = LeadCreate(name="Test", gender=" Male ")
    assert lc_upper.gender == "male"

    lc_female = LeadCreate(name="Test", gender="Female")
    assert lc_female.gender == "female"

    # Empty string should normalize to None
    lc_empty = LeadCreate(name="Test", gender="")
    assert lc_empty.gender is None

    lc_spaces = LeadCreate(name="Test", gender="   ")
    assert lc_spaces.gender is None


def test_lead_create_invalid_genders():
    """Verify LeadCreate rejects invalid gender values with validation error."""
    for invalid in ("other", "abc", "m", "f", "123", "transgender", "nonbinary"):
        with pytest.raises(ValidationError):
            LeadCreate(name="Test", gender=invalid)


def test_lead_update_valid_genders():
    """Verify LeadUpdate accepts valid gender values."""
    for val in ("male", "female", "unknown", None):
        lu = LeadUpdate(gender=val)
        assert lu.gender == val

    lu_empty = LeadUpdate(gender="")
    assert lu_empty.gender is None


def test_lead_update_invalid_genders():
    """Verify LeadUpdate rejects invalid gender values with validation error."""
    for invalid in ("other", "xyz", "m", "f"):
        with pytest.raises(ValidationError):
            LeadUpdate(gender=invalid)


def test_lead_update_clearing_gender_to_null():
    """Verify that submitting gender=None or gender='' clears gender to NULL on CRMLead."""
    lead = CRMLead(id=1, name="Test", gender="male", phone="1234567890")
    assert lead.gender == "male"

    # Client submits gender=None explicitly
    update_payload = LeadUpdate(gender=None)
    update_data = update_payload.dict(exclude_unset=True)
    assert "gender" in update_data
    assert update_data["gender"] is None

    for k, v in update_data.items():
        if hasattr(lead, k):
            setattr(lead, k, v)
    assert lead.gender is None

    # Reset and test client submitting gender=""
    lead.gender = "female"
    update_payload_empty = LeadUpdate(gender="")
    update_data_empty = update_payload_empty.dict(exclude_unset=True)
    assert "gender" in update_data_empty
    assert update_data_empty["gender"] is None

    for k, v in update_data_empty.items():
        if hasattr(lead, k):
            setattr(lead, k, v)
    assert lead.gender is None


def test_lead_update_partial_update_preserves_gender():
    """Verify that updating other fields without specifying gender preserves the existing gender."""
    lead = CRMLead(id=2, name="Original Name", gender="male", phone="1234567890")
    assert lead.gender == "male"

    update_payload = LeadUpdate(name="Updated Name")
    update_data = update_payload.dict(exclude_unset=True)
    assert "gender" not in update_data

    for k, v in update_data.items():
        if hasattr(lead, k):
            setattr(lead, k, v)
    assert lead.name == "Updated Name"
    assert lead.gender == "male"


def test_audit_field_map_tracks_gender():
    """Verify gender is tracked in CRM audit snapshot."""
    import inspect
    src = inspect.getsource(update_lead)
    assert "'gender'" in src
    assert "'gender':                'customer'" in src or "'gender': 'customer'" in src


# ─── 4. SHEETS IMPORT SERVICE ────────────────────────────────────────────────

def test_sheets_leads_service_col_map():
    """Verify COL_MAP recognizes gender headers."""
    assert "gender" in COL_MAP
    assert "gender" in COL_MAP["gender"]
    assert "sex" in COL_MAP["gender"]


def test_sheets_leads_service_row_to_crm_lead():
    """Verify row_to_crm_lead extracts and normalizes gender."""
    headers = ["Name", "Phone", "Gender"]
    col_map = {"name": 0, "phone": 1, "gender": 2}

    # Test 'male'
    row_m = ["Ravi Kumar", "9876543210", "male"]
    data_m = row_to_crm_lead(row_m, col_map, company_id=4, source_tag="test")
    assert data_m["gender"] == "male"

    # Test 'M' (abbreviation)
    row_m_abbr = ["Ravi Kumar", "9876543210", "M"]
    data_m_abbr = row_to_crm_lead(row_m_abbr, col_map, company_id=4, source_tag="test")
    assert data_m_abbr["gender"] == "male"

    # Test 'female'
    row_f = ["Sita Devi", "9876543211", "Female"]
    data_f = row_to_crm_lead(row_f, col_map, company_id=4, source_tag="test")
    assert data_f["gender"] == "female"

    # Test 'F' (abbreviation)
    row_f_abbr = ["Sita Devi", "9876543211", "f"]
    data_f_abbr = row_to_crm_lead(row_f_abbr, col_map, company_id=4, source_tag="test")
    assert data_f_abbr["gender"] == "female"

    # Test empty / unmapped
    row_none = ["Unknown Person", "9876543212", ""]
    data_none = row_to_crm_lead(row_none, col_map, company_id=4, source_tag="test")
    assert data_none["gender"] is None


# ─── 5. AI CALLING PERSONA MAPPING ───────────────────────────────────────────

def test_resolve_persona_from_lead_gender():
    """Verify confirmed AI Persona Mapping:
    - male -> ('Teja', 'onyx')
    - female -> ('Vidya', 'nova')
    - unknown / None / other -> ('Vidya', 'nova') (deterministic fallback)
    """
    assert resolve_persona_from_lead_gender("male") == ("Teja", "onyx")
    assert resolve_persona_from_lead_gender("Male") == ("Teja", "onyx")
    assert resolve_persona_from_lead_gender("MALE") == ("Teja", "onyx")

    assert resolve_persona_from_lead_gender("female") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("Female") == ("Vidya", "nova")

    assert resolve_persona_from_lead_gender("unknown") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender(None) == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("") == ("Vidya", "nova")
    assert resolve_persona_from_lead_gender("other") == ("Vidya", "nova")


def test_ai_calling_voice_choice_detection():
    """Verify spoken choice detection identifies Teja and Vidya."""
    assert _detect_voice_choice("I want Teja") == ("Teja", "onyx")
    assert _detect_voice_choice("male agent please") == ("Teja", "onyx")
    assert _detect_voice_choice("Vidya madam please") == ("Vidya", "nova")
    assert _detect_voice_choice("female agent") == ("Vidya", "nova")
    assert _detect_voice_choice("no preference") == (None, None)


def test_ai_calling_pref_change_detection():
    """Verify mid-conversation switch detection handles Teja and Vidya."""
    assert _detect_pref_change("teja se baat karni hai") == ("agent", "Teja", "onyx")
    assert _detect_pref_change("vidya se baat karni hai") == ("agent", "Vidya", "nova")
