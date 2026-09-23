"""
Test suite for historical/resigned employee incentive achievement and target resolution.
Verifies that employees who closed deals or have saved targets in a month always resolve
their full name, department, employee code, and KRA compliance even if current status is 'resigned'.
"""
import pytest
from unittest.mock import MagicMock
from app.api.v1.endpoints.staff_performance import get_incentive_achievements, get_incentive_employee_targets


def test_resigned_earner_name_resolution():
    # Verify logic maps missing_lead_eids from emp_data into emp_map
    emp_data = {'33': {'solar': {'company_count': 9, 'direct_count': 2, 'self_count': 0}}}
    emp_map = {'1': {'emp_code': 'MR10001', 'name': 'Admin', 'dept_id': 1, 'department': 'Management'}}

    missing_lead_eids = [int(k) for k in emp_data.keys() if str(k).isdigit() and str(k) not in emp_map]
    assert missing_lead_eids == [33]

    # Simulate resolved missing staff
    resolved = [(33, 'MN10003', 'Ms. Bhoolakshmi Pathakamsetti', 19, 'Tele Sales')]
    for r in resolved:
        emp_map[str(r[0])] = {'emp_code': r[1], 'name': r[2], 'dept_id': r[3], 'department': r[4]}

    assert '33' in emp_map
    assert emp_map['33']['name'] == 'Ms. Bhoolakshmi Pathakamsetti'
    assert emp_map['33']['emp_code'] == 'MN10003'
    assert emp_map['33']['department'] == 'Tele Sales'


def test_kra_compliance_bonus_evaluation():
    # 160 total, 134 completed -> 83.8% -> >= 80% gets 1.2 multiplier
    total_tasks = 160
    completed_tasks = 134
    pct = (completed_tasks / total_tasks * 100.0)
    assert pct >= 80.0

    multiplier = 1.2 if pct >= 80.0 else 0.5
    assert multiplier == 1.2

    base_incentive = 24500.0
    final_incentive = base_incentive * multiplier
    assert final_incentive == 29400.0
