#!/usr/bin/env python3
"""
Script to fix Unicode characters that cause issues on Windows.
Replaces problematic Unicode characters in Python source files.
"""

import os
from pathlib import Path

# Unicode character replacements
REPLACEMENTS = {
    '✓': 'OK',
    '✗': 'ERROR',
    '→': 'to',
}

def fix_file(filepath: Path) -> bool:
    """
    Fix Unicode characters in a single file.
    
    Args:
        filepath: Path to file to fix
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        # Read file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace problematic characters
        for old_char, new_char in REPLACEMENTS.items():
            if old_char in content:
                content = content.replace(old_char, new_char)
                print(f"  Replaced '{old_char}' with '{new_char}' in {filepath.name}")
        
        # Write back if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"  ERROR processing {filepath}: {e}")
        return False


def main():
    """Main entry point."""
    print("="*60)
    print("FIX UNICODE CHARACTERS IN PROJECT")
    print("="*60)
    print()
    
    # Get project root (parent of scripts folder)
    project_root = Path(__file__).parent
    
    # Directories to scan
    scan_dirs = [
        project_root / 'src',
        project_root / 'scripts',
    ]
    
    files_modified = 0
    files_scanned = 0
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        
        print(f"Scanning {scan_dir}...")
        
        # Find all Python files
        for py_file in scan_dir.rglob('*.py'):
            files_scanned += 1
            
            if fix_file(py_file):
                files_modified += 1
    
    print()
    print("="*60)
    print("COMPLETE")
    print("="*60)
    print(f"Files scanned: {files_scanned}")
    print(f"Files modified: {files_modified}")
    print("="*60)
    
    if files_modified > 0:
        print("\nPlease run your sync command again:")
        print("  python main.py sync")


if __name__ == '__main__':
    main()