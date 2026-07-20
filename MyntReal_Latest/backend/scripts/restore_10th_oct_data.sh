#!/bin/bash
# Quick Restore Script for "10th Oct Data" Checkpoint

echo "🔄 Restoring database to '10th Oct Data' checkpoint..."
echo ""
echo "⚠️  WARNING: This will replace ALL current database data!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo ""
    echo "📥 Dropping current schema..."
    psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    
    echo ""
    echo "📦 Restoring backup..."
    psql $DATABASE_URL < database_backup_10th_Oct_Data.sql
    
    echo ""
    echo "✅ Database restored to '10th Oct Data' checkpoint successfully!"
    echo "🔄 Please restart your workflows to see the changes."
else
    echo ""
    echo "❌ Restore cancelled."
fi
