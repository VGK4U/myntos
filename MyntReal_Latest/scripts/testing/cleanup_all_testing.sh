#!/bin/bash
echo "🧹 CLEANING UP ALL TESTING TRACES..."

# Delete screenshots
echo -e "\n📸 Deleting screenshots..."
rm -f *.png 2>/dev/null && echo "   ✅ Deleted all PNG files" || echo "   ℹ️  No PNG files found"

# Delete HTML sources
echo -e "\n📄 Deleting HTML page sources..."
rm -f page_source_*.html login_fail_*.html error_*.html 2>/dev/null && echo "   ✅ Deleted HTML sources" || echo "   ℹ️  No HTML sources found"

# Delete test summary
echo -e "\n📝 Deleting test documentation..."
rm -f TESTING_SUMMARY.md 2>/dev/null && echo "   ✅ Deleted TESTING_SUMMARY.md" || echo "   ℹ️  File not found"

echo -e "\n✅ FILE CLEANUP COMPLETE!"
