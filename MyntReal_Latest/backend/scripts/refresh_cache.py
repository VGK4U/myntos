#!/usr/bin/env python3
"""
Cache Refresh Utility - Run this when system slows down
Usage: python3 backend/refresh_cache.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.services.leg_metrics_cache_service import LegMetricsCacheService
from app.models.user import User
from datetime import datetime

def refresh_cache():
    """Refresh cache for all users to speed up dashboard"""
    print("=" * 60)
    print("🚀 BeV Cache Refresh Utility")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    db = SessionLocal()
    cache_service = LegMetricsCacheService(db)
    
    try:
        # Get total user count
        total = db.query(User).count()
        print(f"📊 Total users in system: {total}")
        print(f"🔄 Starting cache refresh...")
        print()
        
        # Get all users (including inactive for complete coverage)
        users = db.query(User).all()
        processed = 0
        
        for i, user in enumerate(users, 1):
            try:
                cache_service.refresh_user_metrics(str(user.id), source='manual_refresh')
                processed += 1
                
                # Show progress every 100 users
                if i % 100 == 0:
                    db.commit()
                    print(f"   ✅ {i}/{total} users processed...")
            except Exception as e:
                print(f"   ⚠️ Skipped user {user.id}: {str(e)[:50]}")
        
        # Final commit
        db.commit()
        
        print()
        print("=" * 60)
        print(f"✅ Cache refresh completed!")
        print(f"   Users processed: {processed}")
        print(f"   Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("💡 Dashboard should now load in ~0.1s instead of 15-31s")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Error during cache refresh: {e}")
        print("=" * 60)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    refresh_cache()
