#!/usr/bin/env python3
"""
Format the GuMCP codebase using black.
"""
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
logger = logging.getLogger("gumcp-format")

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent.absolute()

# Directories to format
FORMAT_DIRS = [
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


def get_files_to_format(dirs, gitignore_patterns):
    """Get Python files to format, excluding those matching gitignore patterns."""
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
    
    files_to_format = []
    for dir_path in dirs:
        if not dir_path.exists():
            continue
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    if not is_ignored(file_path):
                        files_to_format.append(file_path)
    return files_to_format


def run_command(cmd, description):
    """Run a command and log its output."""
    logger.info(f"{description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.info(result.stdout)
        logger.info(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed!")
        if e.stdout:
            logger.error(e.stdout)
        if e.stderr:
            logger.error(e.stderr)
        return False


def run_black(files):
    """Run black on the specified files."""
    cmd = ["black"] + [str(f) for f in files]
    return run_command(cmd, "Black formatting")


def main():
    """Main entry point."""
    logger.info("Formatting GuMCP codebase...")
    
    # Parse gitignore patterns
    gitignore_patterns = parse_gitignore()
    logger.info(f"Parsed {len(gitignore_patterns)} patterns from .gitignore")
    
    # Get files to format
    files_to_format = get_files_to_format(FORMAT_DIRS, gitignore_patterns)
    logger.info(f"Found {len(files_to_format)} Python files to format")
    
    if not files_to_format:
        logger.warning("No Python files found to format!")
        return 0
    
    success = run_black(files_to_format)
    
    if success:
        logger.info("✅ Formatting completed successfully!")
    else:
        logger.error("❌ Formatting failed.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
