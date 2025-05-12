import os
import sys
import time
import subprocess
from pathlib import Path


def get_file_mtimes(directory, pattern="*.py"):
    result = {}
    for path in Path(directory).rglob(pattern):
        if path.is_file():
            result[str(path)] = path.stat().st_mtime
    return result


def run_server():
    cmd = [sys.executable, "src/servers/main.py"]
    process = subprocess.Popen(cmd)
    return process


def watch_files():
    servers_dir = "src/servers"
    print(f"Watching for changes in {servers_dir}/*.py")

    mtimes = get_file_mtimes(servers_dir)
    process = run_server()

    try:
        while True:
            time.sleep(1)
            new_mtimes = get_file_mtimes(servers_dir)

            # Check for changed files
            for file_path, mtime in new_mtimes.items():
                if file_path not in mtimes or mtimes[file_path] != mtime:
                    print(f"\nChange detected in {file_path}, restarting server...")
                    process.terminate()
                    process.wait()
                    mtimes = new_mtimes
                    process = run_server()
                    break

            # Check for new files
            if set(new_mtimes.keys()) != set(mtimes.keys()):
                print("\nNew or deleted files detected, restarting server...")
                process.terminate()
                process.wait()
                mtimes = new_mtimes
                process = run_server()

    except KeyboardInterrupt:
        print("\nShutting down server...")
        process.terminate()
        sys.exit(0)


if __name__ == "__main__":
    watch_files()
