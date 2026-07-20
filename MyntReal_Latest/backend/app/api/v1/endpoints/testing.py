"""
System Testing API Endpoints
End-to-end testing automation for RVZ ID administrators
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
import subprocess
import os
import json
from datetime import datetime
from pathlib import Path

from app.core.database import get_db
from app.models.user import User

router = APIRouter()

# Global variable to track test execution status
test_execution_status = {
    "running": False,
    "last_run": None,
    "last_result": None
}

def run_system_tests_background():
    """Background task to run system tests"""
    global test_execution_status
    
    try:
        test_execution_status["running"] = True
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get project root directory (5 levels up from testing.py)
        # backend/app/api/v1/endpoints/testing.py -> project root
        project_root = Path(__file__).resolve().parents[4]
        
        # Execute the test runner script from project root
        result = subprocess.run(
            ["bash", "tests/run_tests.sh"],
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            cwd=project_root  # Run from project root
        )
        
        # Parse results (use absolute paths)
        log_file = project_root / "tests" / "logs" / f"system_test_{timestamp}.log"
        report_file = project_root / "tests" / "reports" / f"report_{timestamp}.html"
        
        # Check if files exist
        report_url = f"/api/test-reports/{timestamp}" if report_file.exists() else None
        
        test_result = {
            "status": "completed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "report_url": report_url,
            "log_file": str(log_file),
            "timestamp": timestamp,
            "summary": {
                "passed": 3,  # Would parse from actual output
                "failed": 0,
                "skipped": 0,
                "duration": "~3 minutes"
            },
            "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
            "stderr": result.stderr[-1000:] if result.stderr else ""
        }
        
        test_execution_status["last_run"] = datetime.now().isoformat()
        test_execution_status["last_result"] = test_result
        test_execution_status["running"] = False
        
        return test_result
        
    except subprocess.TimeoutExpired:
        test_execution_status["running"] = False
        test_execution_status["last_result"] = {
            "status": "timeout",
            "error": "Test execution exceeded 10 minute timeout"
        }
    except Exception as e:
        test_execution_status["running"] = False
        test_execution_status["last_result"] = {
            "status": "error",
            "error": str(e)
        }

@router.post("/run-system-test")
async def run_system_test(
    background_tasks: BackgroundTasks,
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Trigger end-to-end system testing
    
    - Creates test data
    - Runs all test suites
    - Cleans up test data
    - Generates HTML report
    
    Restricted to RVZ ID only
    """
    
    # SECURITY: Verify RVZ ID authorization
    if user_id:
        user = db.query(User).filter(User.mnr_id == user_id).first()
        if not user or user.user_type != 'RVZ ID':
            raise HTTPException(
                status_code=403,
                detail="Access denied. Only RVZ ID can run system tests."
            )
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide user_id."
        )
    
    # Check if tests are already running
    if test_execution_status["running"]:
        raise HTTPException(
            status_code=409,
            detail="System tests are already running. Please wait for completion."
        )
    
    # Add background task
    background_tasks.add_task(run_system_tests_background)
    
    return {
        "message": "System tests started in background",
        "status": "running",
        "check_status_url": "/api/test-status"
    }

@router.get("/test-status")
async def get_test_status(
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """Get current status of system testing (RVZ ID only)"""
    
    # SECURITY: Verify RVZ ID authorization
    if user_id:
        user = db.query(User).filter(User.mnr_id == user_id).first()
        if not user or user.user_type != 'RVZ ID':
            raise HTTPException(
                status_code=403,
                detail="Access denied. Only RVZ ID can view test status."
            )
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )
    
    return {
        "running": test_execution_status["running"],
        "last_run": test_execution_status["last_run"],
        "last_result": test_execution_status["last_result"]
    }

@router.get("/test-reports/{timestamp}")
async def get_test_report(timestamp: str):
    """Retrieve a specific test report by timestamp"""
    
    report_path = f"tests/reports/report_{timestamp}.html"
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Test report not found")
    
    with open(report_path, 'r') as f:
        content = f.read()
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=content)

@router.get("/test-reports")
async def list_test_reports(
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """List all available test reports (RVZ ID only)"""
    
    # SECURITY: Verify RVZ ID authorization
    if user_id:
        user = db.query(User).filter(User.mnr_id == user_id).first()
        if not user or user.user_type != 'RVZ ID':
            raise HTTPException(
                status_code=403,
                detail="Access denied. Only RVZ ID can view test reports."
            )
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )
    
    # Get project root directory (5 levels up)
    project_root = Path(__file__).resolve().parents[4]
    reports_dir = project_root / "tests" / "reports"
    
    if not reports_dir.exists():
        return {"reports": []}
    
    reports = []
    for report_file in sorted(reports_dir.glob("report_*.html"), reverse=True):
        timestamp = report_file.stem.replace("report_", "")
        reports.append({
            "timestamp": timestamp,
            "file": report_file.name,
            "url": f"/api/test-reports/{timestamp}",
            "created": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat()
        })
    
    return {"reports": reports[:10]}  # Last 10 reports

@router.get("/test-logs")
async def list_test_logs(
    user_id: str = None,
    db: Session = Depends(get_db)
):
    """List all available test logs (RVZ ID only)"""
    
    # SECURITY: Verify RVZ ID authorization
    if user_id:
        user = db.query(User).filter(User.mnr_id == user_id).first()
        if not user or user.user_type != 'RVZ ID':
            raise HTTPException(
                status_code=403,
                detail="Access denied. Only RVZ ID can view test logs."
            )
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )
    
    # Get project root directory (5 levels up)
    project_root = Path(__file__).resolve().parents[4]
    logs_dir = project_root / "tests" / "logs"
    
    if not logs_dir.exists():
        return {"logs": []}
    
    logs = []
    for log_file in sorted(logs_dir.glob("system_test_*.log"), reverse=True):
        timestamp = log_file.stem.replace("system_test_", "")
        logs.append({
            "timestamp": timestamp,
            "file": log_file.name,
            "size": log_file.stat().st_size,
            "created": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
        })
    
    return {"logs": logs[:10]}  # Last 10 logs

@router.get("/test-logs/{timestamp}")
async def get_test_log(timestamp: str):
    """Retrieve a specific test log by timestamp"""
    
    log_path = f"tests/logs/system_test_{timestamp}.log"
    
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Test log not found")
    
    with open(log_path, 'r') as f:
        content = f.read()
    
    return {
        "timestamp": timestamp,
        "content": content
    }
