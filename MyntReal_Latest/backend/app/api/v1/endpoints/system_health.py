"""
System Health & Monitoring Endpoint (Release 1A Observability Layer)
Provides real-time health telemetry for background queue, CAPI foundation, WA audit, and security encryption status.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.core.database import get_db
from app.core.config import settings

router = APIRouter(prefix="/system-health", tags=["System Health & Monitoring"])


@router.get("/release-1a")
def get_release_1a_health(db: Session = Depends(get_db)):
    """
    Release 1A Observability Status Endpoint.
    Reports real-time queue backlog, DLQ failures, CAPI logs, WA audit totals, and feature flags.
    """
    # 1. Feature Flags Status
    flags = {
        "META_SYNC_ENABLED": getattr(settings, "META_SYNC_ENABLED", False),
        "CAPI_ENABLED": getattr(settings, "CAPI_ENABLED", False),
        "WA_AUDIT_ENABLED": getattr(settings, "WA_AUDIT_ENABLED", False),
        "WA_AI_ENABLED": getattr(settings, "WA_AI_ENABLED", False),
        "VOICE_AI_ENABLED": getattr(settings, "VOICE_AI_ENABLED", False),
        "CAMPAIGN_AUTOMATION_ENABLED": getattr(settings, "CAMPAIGN_AUTOMATION_ENABLED", False),
        "STRICT_ENCRYPTED_CREDS_ONLY": getattr(settings, "STRICT_ENCRYPTED_CREDS_ONLY", False),
    }

    # 2. Queue Telemetry
    queue_telemetry = {"queued": 0, "processing": 0, "completed": 0, "failed_dlq": 0}
    try:
        q_rows = db.execute(text(
            "SELECT status, COUNT(*) FROM system_jobs GROUP BY status"
        )).fetchall()
        for st, count in q_rows:
            st_key = str(st).lower()
            queue_telemetry[st_key] = count
    except Exception:
        pass

    # 3. WhatsApp Audit Telemetry
    wa_telemetry = {"conversations_count": 0, "messages_count": 0}
    try:
        wa_telemetry["conversations_count"] = db.execute(text("SELECT COUNT(*) FROM wa_conversations")).scalar() or 0
        wa_telemetry["messages_count"] = db.execute(text("SELECT COUNT(*) FROM wa_messages")).scalar() or 0
    except Exception:
        pass

    # 4. Meta Attribution & Insights Telemetry
    meta_telemetry = {"attributions_count": 0, "insights_daily_rows": 0}
    try:
        meta_telemetry["attributions_count"] = db.execute(text("SELECT COUNT(*) FROM meta_leads_attribution")).scalar() or 0
        meta_telemetry["insights_daily_rows"] = db.execute(text("SELECT COUNT(*) FROM meta_daily_insights")).scalar() or 0
    except Exception:
        pass

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "release": "Release 1A (Foundation)",
        "feature_flags": flags,
        "queue_telemetry": queue_telemetry,
        "whatsapp_audit": wa_telemetry,
        "meta_telemetry": meta_telemetry
    }
