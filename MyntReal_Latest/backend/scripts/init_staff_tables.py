#!/usr/bin/env python3
"""
DC PROTOCOL: Safe initialization of Staff Task Management and Time Tracker tables
ONLY creates NEW tables - does NOT modify any existing tables
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base
from app.models.staff_tasks import (
    StaffTask, StaffTaskAssignee, StaffTaskComment,
    StaffTaskActivityLog, StaffTaskTimeEntry
)
from app.models.staff_attendance import (
    StaffAttendance, StaffAttendanceBreak, StaffAttendanceLog
)
from sqlalchemy import inspect, text

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def init_staff_tables():
    """
    Initialize ONLY the staff task and attendance tables
    DC PROTOCOL: Create only if they don't exist
    """
    print("🔍 DC PROTOCOL: Checking Staff System tables...")
    
    # List of new tables we're creating
    new_tables = [
        'staff_tasks',
        'staff_task_assignees',
        'staff_task_comments',
        'staff_task_activity_log',
        'staff_task_time_entries',
        'staff_attendance',
        'staff_attendance_breaks',
        'staff_attendance_log'
    ]
    
    # Check which tables already exist
    existing_tables = []
    missing_tables = []
    
    for table_name in new_tables:
        if check_table_exists(table_name):
            existing_tables.append(table_name)
        else:
            missing_tables.append(table_name)
    
    if existing_tables:
        print(f"✅ Already exists: {', '.join(existing_tables)}")
    
    if missing_tables:
        print(f"📝 Creating: {', '.join(missing_tables)}")
        
        # DC PROTOCOL: Create ONLY the new tables
        # This will only create tables that don't exist yet
        Base.metadata.create_all(bind=engine, checkfirst=True)
        
        print(f"✅ Created {len(missing_tables)} new tables")
    else:
        print("✅ All Staff System tables already exist - No action needed")
    
    # Verify all tables were created
    print("\n🔍 Verifying table creation...")
    all_exist = True
    for table_name in new_tables:
        exists = check_table_exists(table_name)
        status = "✅" if exists else "❌"
        print(f"{status} {table_name}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n✅ DC PROTOCOL VERIFIED: All Staff System tables ready")
        return True
    else:
        print("\n❌ ERROR: Some tables failed to create")
        return False

if __name__ == "__main__":
    success = init_staff_tables()
    sys.exit(0 if success else 1)
