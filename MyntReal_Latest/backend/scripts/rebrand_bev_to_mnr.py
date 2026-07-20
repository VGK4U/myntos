"""
DC PROTOCOL: Comprehensive MNR to MNR Rebranding
================================================
Systematically replace ALL MNR references with MNR across active codebase
Excludes: docs/project_history, docs/archive (historical documentation)

Run with: cd backend && python scripts/rebrand_mnr_to_mnr.py
"""

import os
import re
from pathlib import Path

# Replacement mappings (case-sensitive)
# ARCHIVED: Rebranding complete. Keep for reference only.
REPLACEMENTS = [
    ("BeV", "MNR"),
    ("bev", "mnr"),
    ("BEV", "MNR"),
]

# Directories to process
INCLUDE_DIRS = [
    "backend/app",
    "backend/scripts", 
    "backend/tests",
    "frontend",
]

# Directories to EXCLUDE (historical docs)
EXCLUDE_DIRS = [
    "docs/project_history",
    "docs/archive",
    "node_modules",
    ".git",
    "__pycache__",
    ".pythonlibs",
]

# File extensions to process
INCLUDE_EXTENSIONS = {".py", ".js", ".html", ".css", ".md", ".json", ".sql"}

def should_process_file(file_path):
    """Check if file should be processed"""
    # Check extension
    if file_path.suffix not in INCLUDE_EXTENSIONS:
        return False
    
    # Check if in excluded directory
    for exclude_dir in EXCLUDE_DIRS:
        if exclude_dir in str(file_path):
            return False
    
    return True

def rebrand_file(file_path):
    """Replace MNR with MNR in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = False
        
        # Apply all replacements
        for old_text, new_text in REPLACEMENTS:
            if old_text in content:
                content = content.replace(old_text, new_text)
                changes_made = True
        
        # Write back if changed
        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Count replacements
            count = sum(original_content.count(old) for old, _ in REPLACEMENTS)
            return True, count
        
        return False, 0
        
    except Exception as e:
        print(f"  ✗ Error processing {file_path}: {str(e)}")
        return False, 0

def main():
    """Run comprehensive rebranding"""
    
    print("="*80)
    print("  DC PROTOCOL: MNR → MNR Comprehensive Rebranding")
    print("="*80)
    
    total_files = 0
    total_changes = 0
    changed_files = []
    
    # Process each directory
    for include_dir in INCLUDE_DIRS:
        if not os.path.exists(include_dir):
            print(f"\n⚠️  Directory not found: {include_dir}")
            continue
        
        print(f"\n📁 Processing: {include_dir}")
        dir_files = 0
        dir_changes = 0
        
        # Walk directory
        for root, dirs, files in os.walk(include_dir):
            # Remove excluded dirs from traversal
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                if should_process_file(file_path):
                    changed, count = rebrand_file(file_path)
                    
                    if changed:
                        dir_files += 1
                        dir_changes += count
                        changed_files.append(str(file_path))
                        print(f"  ✓ {file_path.relative_to('.')} ({count} replacements)")
        
        if dir_files > 0:
            print(f"  → {dir_files} files updated, {dir_changes} replacements")
        else:
            print(f"  → No MNR references found")
        
        total_files += dir_files
        total_changes += dir_changes
    
    # Process root-level important files
    print(f"\n📄 Processing root files")
    root_files = ["replit.md", "PRODUCTION_READINESS_REPORT.md", "backend/app/main.py"]
    for file_name in root_files:
        if os.path.exists(file_name):
            changed, count = rebrand_file(Path(file_name))
            if changed:
                total_files += 1
                total_changes += count
                changed_files.append(file_name)
                print(f"  ✓ {file_name} ({count} replacements)")
    
    # Summary
    print("\n" + "="*80)
    print("  REBRANDING COMPLETE")
    print("="*80)
    print(f"\n  ✅ Files Updated: {total_files}")
    print(f"  ✅ Total Replacements: {total_changes}")
    print(f"\n  DC Protocol: All MNR references → MNR")
    print("="*80 + "\n")
    
    if changed_files:
        print("  Modified Files:")
        for f in changed_files[:20]:  # Show first 20
            print(f"    - {f}")
        if len(changed_files) > 20:
            print(f"    ... and {len(changed_files) - 20} more")
    
    print("\n✅ Rebranding complete! Restart workflows to apply changes.\n")

if __name__ == "__main__":
    main()
