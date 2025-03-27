import os
import sys
import pytest

# Get the absolute path to the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add project root to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    # Get the server name from command line
    server_name = None
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--server="):
            server_name = arg.split("=")[1]
            break
        elif arg == "--server" and i + 1 < len(sys.argv):
            server_name = sys.argv[i + 1]
            break

    if not server_name:
        print("Error: --server argument is required")
        sys.exit(1)

    # Load the server-specific tests
    tests_path = os.path.join(os.path.dirname(__file__), server_name, "tests.py")
    if not os.path.exists(tests_path):
        print(f"Error: No tests.py found for server '{server_name}'")
        sys.exit(1)

    # Clean up any existing .pyc files and __pycache__ directories
    for root, dirs, files in os.walk(os.path.dirname(tests_path)):
        if "__pycache__" in dirs:
            import shutil

            shutil.rmtree(os.path.join(root, "__pycache__"))
        for file in files:
            if file.endswith(".pyc"):
                os.remove(os.path.join(root, file))

    # Construct pytest arguments
    pytest_args = [
        "-v",  # verbose output
        "--capture=no",  # show print statements
        "-p",
        "no:warnings",  # disable warning capture
        "--import-mode=importlib",  # Use importlib for imports
        tests_path,  # path to test file
    ]

    # Add all remaining command line arguments to pytest_args
    # Filter out the --server argument and its value
    skip_next = False
    for arg in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg == "--server":
            skip_next = True
            continue
        if arg.startswith("--server="):
            continue
        pytest_args.append(arg)

    # Run pytest
    sys.exit(pytest.main(pytest_args))
