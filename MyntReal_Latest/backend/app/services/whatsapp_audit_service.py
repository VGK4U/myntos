"""
Unified WhatsApp Trigger Execution Audit Service
Logs all system-level WhatsApp batch, group, and alert dispatches to wa_execution_logs.json.
"""
import os
import json
import uuid
try:
    import fcntl
except ImportError:
    fcntl = None
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

EXEC_LOGS_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "wa_execution_logs.json")
)
LOCK_FILE_PATH = f"{EXEC_LOGS_FILE_PATH}.lock"

def log_wa_trigger_execution(
    job_id: str,
    job_name: str,
    trigger_type: str = "AUTO_SCHEDULER",
    triggered_by: str = "System Cron",
    targets: list = None,
    sent_count: int = 0,
    failed_count: int = 0,
    status: str = "SUCCESS",
    error_message: str = None,
    detail_data: dict = None
) -> dict:
    """
    Atomically logs a system WhatsApp execution into wa_execution_logs.json with POSIX file locking.
    Ensures zero lost updates under multi-process/thread concurrency, single-record output, and IST timestamping.
    """
    try:
        os.makedirs(os.path.dirname(EXEC_LOGS_FILE_PATH), exist_ok=True)

        now_utc = datetime.utcnow()
        now_ist = now_utc + timedelta(hours=5, minutes=30)

        target_names = []
        for t in (targets or []):
            if isinstance(t, dict):
                t_name = t.get("name") or t.get("identifier") or "Target Group"
                target_names.append(t_name)
            elif isinstance(t, str):
                target_names.append(t)
        target_summary = ", ".join(target_names) if target_names else "Configured Targets"

        entry = {
            "id": f"log_{uuid.uuid4().hex[:8]}",
            "job_id": job_id,
            "job_name": job_name,
            "trigger_type": trigger_type,
            "triggered_by": triggered_by,
            "timestamp": now_ist.strftime("%d %b %Y, %I:%M:%S %p IST"),
            "iso_timestamp": now_ist.isoformat(),
            "target_summary": target_summary,
            "targets": targets or [],
            "sent_count": sent_count,
            "failed_count": failed_count,
            "status": status,
            "error_message": error_message,
            "detail": detail_data or {}
        }

        # Acquire lock if fcntl available
        with open(LOCK_FILE_PATH, "w") as lock_file:
            if fcntl:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                logs = []
                if os.path.exists(EXEC_LOGS_FILE_PATH):
                    try:
                        with open(EXEC_LOGS_FILE_PATH, "r") as f:
                            logs = json.load(f)
                    except Exception:
                        logs = []
                    if not isinstance(logs, list):
                        logs = []

                # Insert at top (newest first)
                logs.insert(0, entry)
                logs = logs[:500]

                # Atomic write via temporary file
                tmp_file = f"{EXEC_LOGS_FILE_PATH}.tmp_{uuid.uuid4().hex[:6]}"
                with open(tmp_file, "w") as f:
                    json.dump(logs, f, indent=2)
                os.replace(tmp_file, EXEC_LOGS_FILE_PATH)
            finally:
                if fcntl:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)

        return entry
    except Exception as e:
        logger.warning(f"Could not write execution log: {e}")
        return None
