"""
DC Protocol: Lazy Initialization Module
Defers blocking schema bootstrap and checkpoint verification to first use
Ensures fast server startup while maintaining data consistency

WRITE: Initialization deferred to first DB operation (threadsafe)
VERIFY: Guard ensures operations run exactly once
VALIDATE: All existing functions work without modification
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Thread-safe guard for one-time initialization
_initialization_lock = threading.Lock()
_initialization_complete = False
_initialization_error: Optional[Exception] = None


def ensure_initialized():
    """
    DC Protocol: Ensure system is initialized before any DB operation
    Thread-safe, idempotent, runs exactly once
    Called automatically on first API request (lazy initialization)
    
    WRITE: Runs schema_bootstrap and checkpoint verification
    VERIFY: Lock prevents concurrent initialization
    VALIDATE: Returns immediately on subsequent calls
    """
    global _initialization_complete, _initialization_error
    
    # Fast path: Already initialized
    if _initialization_complete:
        if _initialization_error:
            raise _initialization_error
        return
    
    # Slow path: First initialization (only one thread proceeds)
    with _initialization_lock:
        # Double-check after acquiring lock
        if _initialization_complete:
            if _initialization_error:
                raise _initialization_error
            return
        
        try:
            logger.info("[LAZY-INIT] Starting system initialization...")
            
            # DC PROTOCOL: Schema bootstrap (idempotent)
            try:
                from app.core.schema_bootstrap import run_schema_bootstrap
                logger.info("[LAZY-INIT] Running schema bootstrap...")
                run_schema_bootstrap()
                logger.info("[LAZY-INIT] ✅ Schema bootstrap complete")
            except Exception as e:
                logger.error(f"[LAZY-INIT] ❌ Schema bootstrap failed: {e}")
                _initialization_error = e
                _initialization_complete = True
                raise
            
            # DC PROTOCOL: Verify/Create critical system checkpoints
            try:
                from app.core.database import SessionLocal
                from app.models.system import SystemCheckpoint
                from datetime import datetime
                
                logger.info("[LAZY-INIT] Verifying system checkpoints...")
                db = SessionLocal()
                try:
                    checkpoint = db.query(SystemCheckpoint).filter(
                        SystemCheckpoint.checkpoint_name == 'awards_production_start'
                    ).first()
                    
                    if not checkpoint:
                        logger.warning("[LAZY-INIT] Creating missing checkpoint: awards_production_start")
                        checkpoint = SystemCheckpoint(
                            checkpoint_name='awards_production_start',
                            checkpoint_date=datetime(2025, 10, 21, 0, 0, 0),
                            description='Production start date - all awards before this date are marked as legacy pre-reset',
                            created_by='system'
                        )
                        db.add(checkpoint)
                        db.commit()
                        logger.info("[LAZY-INIT] ✅ Checkpoint created: awards_production_start")
                    else:
                        logger.info(f"[LAZY-INIT] ✅ Checkpoint verified: {checkpoint.checkpoint_date}")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"[LAZY-INIT] ❌ Checkpoint verification failed: {e}")
                _initialization_error = e
                _initialization_complete = True
                raise
            
            logger.info("[LAZY-INIT] ✅ System initialization complete")
            _initialization_complete = True
            
        except Exception as e:
            logger.error(f"[LAZY-INIT] ❌ Initialization failed: {e}")
            _initialization_error = e
            _initialization_complete = True
            raise


def reset_initialization():
    """Debug utility: Reset initialization state (testing only)"""
    global _initialization_complete, _initialization_error
    _initialization_complete = False
    _initialization_error = None
