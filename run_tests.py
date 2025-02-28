#!/usr/bin/env python
"""
Test runner for backpack-volume-auto project.
Run all tests with: python run_tests.py
Run specific test files with: python run_tests.py tests/unit/test_bot_worker.py
"""

import sys
import pytest

if __name__ == "__main__":
    print("Running tests...")
    
    args = sys.argv[1:] if len(sys.argv) > 1 else ['tests/']
    exit_code = pytest.main(args)
    
    sys.exit(exit_code)