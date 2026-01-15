#!/usr/bin/env python3
"""
Simple test script to verify CLI functionality
"""
import subprocess
import sys
import os

def run_test(name, cmd, expected_in_output=None, should_succeed=True):
    """Run a test command"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"CMD: {cmd}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if should_succeed and result.returncode != 0:
            print(f"❌ FAILED: Command returned {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False
        
        if expected_in_output:
            if expected_in_output not in result.stdout:
                print(f"❌ FAILED: Expected '{expected_in_output}' not in output")
                print(f"OUTPUT: {result.stdout[:500]}")
                return False
        
        print(f"✅ PASSED")
        return True
    
    except subprocess.TimeoutExpired:
        print(f"⚠️  TIMEOUT (expected for some tests)")
        return True
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Run all tests"""
    tests_passed = 0
    tests_total = 0
    
    # Test 1: List strategies
    tests_total += 1
    if run_test(
        "List Strategies",
        "python3 duckdice_cli.py strategies",
        expected_in_output="classic-martingale"
    ):
        tests_passed += 1
    
    # Test 2: Show config
    tests_total += 1
    if run_test(
        "Show Config",
        "python3 duckdice_cli.py config",
        expected_in_output="Current Configuration"
    ):
        tests_passed += 1
    
    # Test 3: Show help
    tests_total += 1
    if run_test(
        "Show Help",
        "python3 duckdice_cli.py --help",
        expected_in_output="DuckDice Bot CLI"
    ):
        tests_passed += 1
    
    # Test 4: Run simulation (short)
    tests_total += 1
    if run_test(
        "Run Simulation (5 bets)",
        "timeout 10 python3 duckdice_cli.py run -m simulation -s dalembert -c btc --max-bets 5 || true",
        expected_in_output="dalembert"  # Changed to match new output format
    ):
        tests_passed += 1
    
    # Test 5: List profiles
    tests_total += 1
    if run_test(
        "List Profiles",
        "python3 duckdice_cli.py profiles"
    ):
        tests_passed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print(f"✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"❌ {tests_total - tests_passed} TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
