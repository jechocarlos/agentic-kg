#!/usr/bin/env python3
"""
Test runner for AKG system tests.

This script runs all available tests in the tests directory.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Add the parent directory to the path to access src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def run_test_file(test_file):
    """Run a single test file and return the result."""
    print(f"\n{'='*60}")
    print(f"🧪 RUNNING: {test_file}")
    print(f"{'='*60}")
    
    try:
        # Use the virtual environment python
        venv_python = os.path.join(os.path.dirname(__file__), '..', 'venv', 'bin', 'python')
        result = subprocess.run([venv_python, test_file], 
                              capture_output=True, 
                              text=True, 
                              timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            print(result.stdout)
            print(f"✅ {test_file} PASSED")
            return True
        else:
            print(f"❌ {test_file} FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_file} TIMED OUT")
        return False
    except Exception as e:
        print(f"💥 {test_file} ERROR: {e}")
        return False


def main():
    """Run all test files in the tests directory."""
    
    print("🚀 AKG SYSTEM TEST RUNNER")
    print("="*60)
    
    tests_dir = Path(__file__).parent
    test_files = []
    
    # Find all test files
    for test_file in tests_dir.glob("test_*.py"):
        if test_file.name != "test_runner.py":  # Don't run self
            test_files.append(test_file)
    
    if not test_files:
        print("❌ No test files found")
        return 1
    
    print(f"📋 Found {len(test_files)} test files:")
    for test_file in test_files:
        print(f"  • {test_file.name}")
    
    print(f"\n🏃‍♂️ Running tests...")
    
    # Run each test
    results = {}
    passed = 0
    failed = 0
    
    for test_file in test_files:
        success = run_test_file(test_file)
        results[test_file.name] = success
        if success:
            passed += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📋 Total:  {len(test_files)}")
    
    print(f"\n📝 Detailed Results:")
    for test_file, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_file:35} {status}")
    
    if failed == 0:
        print(f"\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
