#!/usr/bin/env python3
"""
Run linting checks on the GuMCP codebase.
"""
import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gumcp-lint")

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent.absolute()

# Directories to check
CHECK_DIRS = [
    ROOT_DIR / "src",
    ROOT_DIR / "tests",
]


def parse_gitignore():
    """Parse .gitignore and return a list of patterns to ignore."""
    gitignore_path = ROOT_DIR / ".gitignore"
    if not gitignore_path.exists():
        return []
        
    patterns = []
    with open(gitignore_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            patterns.append(line)
    return patterns


def get_files_to_check(dirs, gitignore_patterns):
    """Get Python files to check, excluding those matching gitignore patterns."""
    import fnmatch
    import os
    
    def is_ignored(file_path):
        """Check if a file matches any gitignore pattern."""
        rel_path = str(file_path.relative_to(ROOT_DIR))
        for pattern in gitignore_patterns:
            if pattern.endswith('/'):
                # Directory pattern
                if fnmatch.fnmatch(rel_path + '/', pattern) or rel_path.startswith(pattern):
                    return True
            else:
                # File pattern
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
        return False
    
    files_to_check = []
    for dir_path in dirs:
        if not dir_path.exists():
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    if not is_ignored(file_path):
                        files_to_check.append(file_path)
    return files_to_check


def run_command(cmd, description):
    """Run a command and return its status."""
    logger.info(f"{description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"✅ {description} passed!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed!")
        logger.error(e.stdout)
        logger.error(e.stderr)
        return False


def run_flake8(files):
    """Run flake8 on the specified files."""
    cmd = ["flake8"] + [str(f) for f in files]
    return run_command(cmd, "Flake8 linting")


def run_mypy(files):
    """Run mypy on the specified files."""
    # Use namespace packages to prevent duplicate module errors
    cmd = ["mypy", "--explicit-package-bases"] + [str(f) for f in files]
    return run_command(cmd, "Mypy type checking")


def run_black_check(files):
    """Check if files are formatted with black."""
    cmd = ["black", "--check"] + [str(f) for f in files]
    return run_command(cmd, "Black format checking")


def run_linting(dirs, auto_fix=False):
    """Run all linting checks, optionally fixing issues."""
    # Parse gitignore patterns
    gitignore_patterns = parse_gitignore()
    logger.info(f"Parsed {len(gitignore_patterns)} patterns from .gitignore")
    
    # Get files to check
    files_to_check = get_files_to_check(dirs, gitignore_patterns)
    logger.info(f"Found {len(files_to_check)} Python files to check")
    
    if not files_to_check:
        logger.warning("No Python files found to check!")
        return 0
    
    all_passed = True
    
    # If auto-fix is enabled, run black to format code
    if auto_fix:
        logger.info("Auto-fixing formatting issues...")
        run_command(["black"] + [str(f) for f in files_to_check], "Black formatting")
    
    # Run all checks
    all_passed = run_flake8(files_to_check) and all_passed
    all_passed = run_mypy(files_to_check) and all_passed
    all_passed = run_black_check(files_to_check) and all_passed
    
    if all_passed:
        logger.info("✅ All linting checks passed!")
    else:
        logger.error("❌ Some linting checks failed.")
    
    return 0 if all_passed else 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run linting checks on the GuMCP codebase.")
    parser.add_argument(
        "--fix", 
        action="store_true", 
        help="Automatically fix formatting issues with black"
    )
    parser.add_argument(
        "--dirs", 
        nargs="+", 
        help="Directories to check (default: src tests)"
    )
    
    args = parser.parse_args()
    
    # Use provided directories or default
    dirs_to_check = [Path(d) for d in args.dirs] if args.dirs else CHECK_DIRS
    
    return run_linting(dirs_to_check, auto_fix=args.fix)


if __name__ == "__main__":
    sys.exit(main()) 