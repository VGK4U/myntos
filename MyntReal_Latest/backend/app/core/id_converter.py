"""
MNR ID to Employee ID Conversion Layer
DC Protocol: Validated conversion with audit trail
WVV: Write conversion logic → Verify employee exists → Validate result
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
import re


async def convert_mnr_id_to_employee_id(db: Session, mnr_id: str) -> int:
    """
    Convert MNR ID (user-facing format like MR00001) to internal employee_id (integer)
    
    DC Protocol:
    - WRITE: Accept MNR ID string, validate format
    - VERIFY: Query database for matching employee
    - VALIDATE: Return integer ID or raise exception
    
    Args:
        db: Database session
        mnr_id: MNR ID string in format MR##### (e.g., MR00001)
    
    Returns:
        int: Internal employee_id from staff_employees table
    
    Raises:
        ValueError: If MNR ID format is invalid
        HTTPException(404): If employee not found
    """
    # WRITE: Validate format
    if not mnr_id:
        raise ValueError("MNR ID cannot be empty")
    
    if not re.match(r'^(MR|MN)\d{5}$', mnr_id):
        raise ValueError(f"Invalid employee code format: {mnr_id}. Expected format: MR##### or MN##### (e.g., MR00001, MN10003)")
    
    # VERIFY: Import here to avoid circular imports
    from app.models.staff import StaffEmployee
    
    # Query employee by emp_code (MNR format: MR##### or MN#####)
    employee = db.query(StaffEmployee).filter(
        StaffEmployee.emp_code == mnr_id
    ).first()
    
    # VALIDATE: Check if employee exists
    if not employee:
        raise HTTPException(
            status_code=404, 
            detail=f"Employee with MNR ID {mnr_id} not found in system"
        )
    
    # Return integer employee_id
    return employee.id


async def convert_multiple_mnr_ids(db: Session, mnr_ids: list) -> list:
    """
    Convert multiple MNR IDs to employee IDs
    
    Args:
        db: Database session
        mnr_ids: List of MNR ID strings
    
    Returns:
        list: List of integer employee IDs
    
    Raises:
        ValueError: If any MNR ID is invalid
        HTTPException: If any employee not found
    """
    if not mnr_ids:
        return []
    
    employee_ids = []
    for mnr_id in mnr_ids:
        emp_id = await convert_mnr_id_to_employee_id(db, mnr_id)
        employee_ids.append(emp_id)
    
    return employee_ids
