#!/usr/bin/env python3
"""
Test runner script for giraffeCAD-proto.

This script provides an easy way to run tests with various options.
"""

import sys
import subprocess
from pathlib import Path


def run_tests(args=None):
    """Run pytest with the given arguments."""
    if args is None:
        args = []
    
    # Base pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add custom arguments
    cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest run interrupted by user.")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point for the test runner."""
    # Pass any command line arguments directly to pytest
    return run_tests(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main()) 