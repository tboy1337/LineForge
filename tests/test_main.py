#!/usr/bin/env python3
"""
Test the main function and command line interface of normalize.py.
"""

import os
import sys
import unittest
import tempfile
import shutil
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize


class TestMain(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create test files
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, 'wb') as f:
            f.write(b"Line 1\r\nLine 2\r\n")

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_main_with_args(self):
        """Test main function with command line arguments."""
        test_args = [
            "normalize.py",
            self.test_dir,
            ".txt",
            "--format", "lf",
            "--remove-whitespace",
            "--non-interactive"
        ]
        
        with patch('sys.argv', test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_main_no_files_found(self):
        """Test main function when no matching files are found."""
        test_args = [
            "normalize.py", 
            self.test_dir, 
            ".nonexistent",
            "--non-interactive"
        ]
        
        with patch('sys.argv', test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_main_invalid_directory(self):
        """Test main function with invalid directory."""
        test_args = [
            "normalize.py", 
            "/nonexistent/directory", 
            ".txt",
            "--non-interactive"
        ]
        
        with patch('sys.argv', test_args):
            result = normalize.main()
            self.assertEqual(result, 1)

    def test_main_interactive_mode(self):
        """Test main function in interactive mode."""
        test_args = ["normalize.py"]
        
        with patch('sys.argv', test_args):
            with patch('builtins.input', side_effect=[
                self.test_dir,  # root directory
                ".txt",         # file patterns
                "lf",           # format
                "n",            # remove whitespace
                "n",            # preserve tabs
                "",             # ignore dirs (default)
                ""              # workers (default)
            ]):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_main_keyboard_interrupt(self):
        """Test main function handling KeyboardInterrupt."""
        test_args = ["normalize.py", self.test_dir, ".txt", "--non-interactive"]
        
        with patch('sys.argv', test_args):
            with patch('normalize.find_files', side_effect=KeyboardInterrupt()):
                result = normalize.main()
                self.assertEqual(result, 130)

    def test_main_exception_handling(self):
        """Test main function handling unexpected exceptions."""
        test_args = ["normalize.py", self.test_dir, ".txt", "--non-interactive"]
        
        with patch('sys.argv', test_args):
            with patch('normalize.find_files', side_effect=RuntimeError("Test error")):
                result = normalize.main()
                self.assertEqual(result, 1)

    def test_main_invalid_workers_count(self):
        """Test main function with invalid workers count."""
        test_args = [
            "normalize.py",
            self.test_dir,
            ".txt",
            "--workers", "0",
            "--non-interactive"
        ]
        
        with patch('sys.argv', test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_main_verbose_mode(self):
        """Test main function with verbose logging."""
        test_args = [
            "normalize.py",
            self.test_dir,
            ".txt",
            "--verbose",
            "--non-interactive"
        ]
        
        with patch('sys.argv', test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_version_argument(self):
        """Test --version argument."""
        test_args = ["normalize.py", "--version"]
        
        with patch('sys.argv', test_args):
            with self.assertRaises(SystemExit):
                normalize.main()


if __name__ == "__main__":
    unittest.main()
