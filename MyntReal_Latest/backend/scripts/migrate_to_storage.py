"""
One-time migration script: Upload all local media files to Object Storage
Run this in PRODUCTION to populate the production App Storage bucket
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.object_storage import storage_service
from app.core.database import SessionLocal
from app.models.feedback import FeedbackMedia

def migrate_files_to_storage():
    """Upload all media files from local uploads to Object Storage"""
    
    print("="*70)
    print("📦 MIGRATING MEDIA FILES TO OBJECT STORAGE (PRODUCTION)")
    print("="*70)
    
    db = SessionLocal()
    try:
        # Get all media records
        all_media = db.query(FeedbackMedia).all()
        print(f"\n📊 Found {len(all_media)} media records in database")
        
        # Check local uploads directory
        local_uploads = Path("backend/uploads/feedback")
        if not local_uploads.exists():
            local_uploads = Path("uploads/feedback")
        
        if not local_uploads.exists():
            print("\n❌ ERROR: No local uploads folder found!")
            print("   This script needs to be run where 'backend/uploads/feedback' exists")
            return
        
        print(f"📂 Local uploads: {local_uploads.absolute()}")
        
        migrated = 0
        skipped = 0
        failed = 0
        
        # Process each media record
        for media in all_media:
            # Extract path components (e.g., "feedback/31/video_1.mp4")
            file_path = media.file_path
            
            # Skip if already in /storage/ format
            if file_path.startswith('/storage/'):
                file_path = file_path.replace('/storage/', '')
            
            # Build local file path
            # If file_path is like "feedback/31/video_1.mp4", use it directly
            # If it's like "uploads/feedback/31/video_1.mp4", extract the feedback part
            if file_path.startswith('uploads/'):
                file_path = file_path.replace('uploads/', '')
            elif file_path.startswith('backend/uploads/'):
                file_path = file_path.replace('backend/uploads/', '')
            
            # Check if file exists in Object Storage
            if storage_service.file_exists(file_path):
                print(f"   ⏭️  Skip: {file_path} (already in storage)")
                skipped += 1
                continue
            
            # Find local file
            local_file = local_uploads.parent / file_path
            if not local_file.exists():
                # Try alternative path
                local_file = Path(file_path)
            
            if not local_file.exists():
                print(f"   ❌ Not found locally: {file_path}")
                failed += 1
                continue
            
            # Read and upload
            try:
                with open(local_file, 'rb') as f:
                    file_data = f.read()
                
                success = storage_service.upload_file(file_path, file_data)
                
                if success:
                    size_kb = len(file_data) / 1024
                    print(f"   ✅ Uploaded: {file_path} ({size_kb:.1f} KB)")
                    migrated += 1
                else:
                    print(f"   ❌ Upload failed: {file_path}")
                    failed += 1
                    
            except Exception as e:
                print(f"   ❌ Error: {file_path} - {str(e)}")
                failed += 1
        
        print(f"\n" + "="*70)
        print(f"📊 MIGRATION COMPLETE")
        print(f"="*70)
        print(f"   ✅ Migrated: {migrated} files")
        print(f"   ⏭️  Skipped: {skipped} files (already existed)")
        print(f"   ❌ Failed: {failed} files")
        print(f"="*70)
        
        if migrated > 0:
            print(f"\n🎉 Success! {migrated} files uploaded to production App Storage")
            print(f"   Images should now work on https://mnr.manthraev.com")
        
    finally:
        db.close()

if __name__ == "__main__":
    migrate_files_to_storage()
