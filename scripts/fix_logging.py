#!/usr/bin/env python3
"""
Script to convert all basic logging to structured logging across the codebase.

This script finds all Python files and replaces:
- import logging / logger = logging.getLogger(__name__)
with:
- from app.core.logging_config import get_logger / logger = get_logger(__name__)
"""

import os
import re
from pathlib import Path


def fix_logging_in_file(file_path: Path) -> bool:
    """Fix logging imports in a single file. Returns True if changes were made."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Skip files that already use structured logging
        if 'from app.core.logging_config import get_logger' in content:
            return False

        # Skip __init__.py files to avoid circular imports
        if file_path.name == '__init__.py':
            return False

        # Skip files in core module to avoid circular imports
        if 'core/' in str(file_path) or '/core\\' in str(file_path):
            return False

        # Pattern 1: Replace "import logging" lines that are standalone
        content = re.sub(
            r'^import logging$',
            'from app.core.logging_config import get_logger',
            content,
            flags=re.MULTILINE
        )

        # Pattern 2: Replace "logger = logging.getLogger(__name__)"
        content = re.sub(
            r'logger = logging\.getLogger\(__name__\)',
            'logger = get_logger(__name__)',
            content
        )

        # Pattern 3: Replace "logger = logging.getLogger(__name__)" with different variable names
        content = re.sub(
            r'(\w+) = logging\.getLogger\(__name__\)',
            r'\1 = get_logger(__name__)',
            content
        )

        # Pattern 4: Handle cases where logging is imported alongside other modules
        # This is more complex and might need manual review

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process all Python files."""
    project_root = Path(__file__).parent.parent
    app_dir = project_root / 'app'

    if not app_dir.exists():
        print(f"App directory not found: {app_dir}")
        return

    changed_files = []

    # Process all Python files in the app directory
    for py_file in app_dir.rglob('*.py'):
        if fix_logging_in_file(py_file):
            changed_files.append(py_file)
            print(f"Updated logging in: {py_file.relative_to(project_root)}")

    if changed_files:
        print(f"\nSuccessfully updated {len(changed_files)} files:")
        for file_path in changed_files:
            print(f"  - {file_path.relative_to(project_root)}")
    else:
        print("No files needed logging updates.")


if __name__ == '__main__':
    main()