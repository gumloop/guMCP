import sys
import pytest
import argparse

from pathlib import Path
from typing import List, Dict, Tuple


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run tests for GuMCP servers")
    
    parser.add_argument(
        "--servers",
        nargs="*",
        help="Specific servers to test (defaults to all servers if not specified)"
    )
    
    parser.add_argument(
        "--mode",
        choices=["local", "remote", "both"],
        default="both",
        help="Test mode: local, remote, or both (default: both)"
    )
    
    parser.add_argument(
        "--base-port",
        type=int,
        default=8000,
        help="Base port for servers (default: 8000, ports will be incremented for multiple servers)"
    )
    
    parser.add_argument(
        "--endpoint-template",
        default="http://localhost:{port}/{server}",
        help="Template for server endpoints (default: http://localhost:{port}/{server})"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for each test (default: 60)"
    )
    
    return parser.parse_args()

def discover_servers() -> List[str]:
    """Discover available server tests in the project"""
    servers_dir = Path(__file__).parent / "servers"
    if not servers_dir.exists() or not servers_dir.is_dir():
        print(f"Servers directory not found at {servers_dir}")
        return []
        
    # Look for directories containing test files
    servers = []
    for server_dir in servers_dir.iterdir():
        if not server_dir.is_dir():
            continue
            
        # Check if this directory contains test files
        has_tests = False
        for test_file in server_dir.glob("*_test.py"):
            has_tests = True
            break
            
        if has_tests:
            servers.append(server_dir.name)
    
    return servers


def run_tests(server: str, test_mode: str, args: argparse.Namespace) -> Tuple[bool, Dict[str, bool]]:
    """Run tests for a specific server
    
    Args:
        server: Server name
        test_mode: Test mode (local, remote, or both)
        args: Command line arguments
        
    Returns:
        Tuple of (overall success, results by test type)
    """
    results = {}
    
    # Determine test directory
    test_dir = Path(__file__).parent / "servers" / server
    if not test_dir.exists() or not test_dir.is_dir():
        print(f"Test directory not found for server {server} at {test_dir}")
        return False, {}
    
    print(f"\n{'='*80}")
    print(f"Running tests for server: {server}")
    print(f"{'='*80}")
    
    # Run local tests if requested
    if test_mode in ["local", "both"]:
        local_test_file = test_dir / "local_test.py"
        if local_test_file.exists():
            print(f"\nRunning local tests for {server}...")
            
            # Build pytest args
            pytest_args = [
                "-xvs" if args.verbose else "-v",
                str(local_test_file),
                f"--server-name={server}",
                f"--timeout={args.timeout}"
            ]
            
            print(f"Running: pytest {' '.join(pytest_args)}")
            local_result = pytest.main(pytest_args)
            results["local"] = local_result == 0
            
            print(f"Local tests for {server}: {'PASSED' if results['local'] else 'FAILED'}")
        else:
            print(f"No local tests found for {server} at {local_test_file}")
    
    # Run remote tests if requested
    if test_mode in ["remote", "both"]:
        remote_test_file = test_dir / "remote_test.py"
        if remote_test_file.exists():
            print(f"\nRunning remote tests for {server}...")
            
            # Determine endpoint for remote tests
            endpoint = args.endpoint_template.format(port=args.base_port, server=server)
            
            # Build pytest args
            pytest_args = [
                "-xvs" if args.verbose else "-v",
                str(remote_test_file),
                f"--endpoint={endpoint}",
                f"--timeout={args.timeout}"
            ]
            
            print(f"Running: pytest {' '.join(pytest_args)}")
            remote_result = pytest.main(pytest_args)
            results["remote"] = remote_result == 0
            
            print(f"Remote tests for {server}: {'PASSED' if results['remote'] else 'FAILED'}")
        else:
            print(f"No remote tests found for {server} at {remote_test_file}")
    
    # Calculate overall success
    overall_success = all(results.values()) if results else False
    
    return overall_success, results


def main():
    """Main entry point"""
    args = parse_args()
    
    # Discover available servers
    available_servers = discover_servers()
    if not available_servers:
        print("No server tests found!")
        return 1
    
    print(f"Found server tests: {', '.join(available_servers)}")
    
    # Determine which servers to test
    servers_to_test = args.servers if args.servers else available_servers
    for server in servers_to_test:
        if server not in available_servers:
            print(f"Warning: Server '{server}' not found in available servers")
    
    # Filter to only available servers
    servers_to_test = [s for s in servers_to_test if s in available_servers]
    if not servers_to_test:
        print("No valid servers to test!")
        return 1
    
    # Run tests for each server
    overall_results = {}
    for server in servers_to_test:
        success, results = run_tests(server, args.mode, args)
        overall_results[server] = {"success": success, "results": results}
    
    # Print summary
    print("\n" + "="*80)
    print("Test Results Summary")
    print("="*80)
    
    for server, result in overall_results.items():
        status = "PASSED" if result["success"] else "FAILED"
        print(f"\n{server}: {status}")
        
        for test_type, success in result["results"].items():
            status = "PASSED" if success else "FAILED"
            print(f"  {test_type.capitalize()}: {status}")
    
    # Calculate overall success
    all_passed = all(r["success"] for r in overall_results.values())
    
    print("\n" + "="*80)
    print(f"Overall: {'PASSED' if all_passed else 'FAILED'}")
    print("="*80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main()) 