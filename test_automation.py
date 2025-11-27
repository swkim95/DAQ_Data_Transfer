#!/usr/bin/env python3
"""Test script to demonstrate live output in automation."""

import subprocess
import sys

def test_old_method():
    """Test with captured output (no live progress)."""
    print("=== OLD METHOD (captured output) ===")
    result = subprocess.run(
        ["python3", "test_progress.py"],
        capture_output=True,
        text=True
    )
    print("Final result:")
    print(result.stdout)
    print()

def test_new_method():
    """Test with live output (shows progress bars)."""
    print("=== NEW METHOD (live output) ===")
    
    process = subprocess.Popen(
        ["python3", "test_progress.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.rstrip())
    
    return_code = process.returncode
    print(f"Return code: {return_code}")
    print()

if __name__ == "__main__":
    test_old_method()
    test_new_method()