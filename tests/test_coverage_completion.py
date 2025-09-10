#!/usr/bin/env python3
"""
Test additional scenarios to achieve 100% test coverage for normalize.py.
"""

import os
import sys
import unittest
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize


class TestCoverageCompletion(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create test file
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("Test content\n")

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_is_binary_file_extensions(self):
        """Test binary file detection by extensions."""
        # Test various binary extensions
        binary_files = [
            "test.exe", "test.dll", "test.png", "test.jpg",
            "test.pdf", "test.zip", "test.class", "test.pyc"
        ]
        
        for filename in binary_files:
            file_path = os.path.join(self.test_dir, filename)
            # Create file with some content to avoid empty file detection
            with open(file_path, 'wb') as f:
                f.write(b"some binary content")
            
            result = normalize.is_binary_file(file_path)
            self.assertTrue(result, f"Should detect {filename} as binary")

    def test_is_binary_file_magic_numbers(self):
        """Test binary file detection by magic numbers."""
        magic_files = [
            ("png.txt", b'\x89PNG\r\n\x1a\n'),
            ("gif.txt", b'GIF89a'),
            ("jpg.txt", b'\xff\xd8\xff'),
            ("pdf.txt", b'%PDF-1.4'),
            ("zip.txt", b'PK\x03\x04')
        ]
        
        for filename, magic in magic_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(magic)
                f.write(b"some content after magic")
            
            result = normalize.is_binary_file(file_path)
            self.assertTrue(result, f"Should detect {filename} as binary by magic number")

    def test_is_binary_file_null_bytes(self):
        """Test binary file detection by null bytes."""
        file_path = os.path.join(self.test_dir, "null_bytes.txt")
        with open(file_path, 'wb') as f:
            f.write(b"normal text\x00with null bytes")
        
        result = normalize.is_binary_file(file_path)
        self.assertTrue(result)

    def test_is_binary_file_non_text_ratio(self):
        """Test binary file detection by non-text character ratio."""
        file_path = os.path.join(self.test_dir, "non_text.txt")
        # Create content with high ratio of non-text bytes
        with open(file_path, 'wb') as f:
            f.write(b'\x01\x02\x03' * 100)  # High ratio of non-text bytes
        
        result = normalize.is_binary_file(file_path)
        self.assertTrue(result)

    def test_main_interactive_with_defaults(self):
        """Test main function interactive mode with all defaults."""
        test_args = ["normalize.py"]
        
        with patch('sys.argv', test_args):
            with patch('builtins.input', side_effect=[
                "",     # root directory (default to current)
                "",     # file patterns (default to .txt)
                "",     # format (default to crlf)
                "",     # remove whitespace (default to n)
                "",     # preserve tabs (default to n)
                "",     # ignore dirs (default)
                "",     # workers (default)
            ]):
                with patch('os.getcwd', return_value=self.test_dir):
                    result = normalize.main()
                    self.assertEqual(result, 0)

    def test_main_interactive_custom_inputs(self):
        """Test main function interactive mode with custom inputs."""
        test_args = ["normalize.py"]
        
        with patch('sys.argv', test_args):
            with patch('builtins.input', side_effect=[
                self.test_dir,          # root directory
                ".txt .py",             # file patterns
                "lf",                   # format
                "yes",                  # remove whitespace
                "",                     # preserve tabs (skip - whitespace removal chosen)
                "custom_dir",           # ignore dirs
                "2",                    # workers
            ]):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_main_with_partial_args(self):
        """Test main function with partial arguments triggering interactive mode."""
        # Only provide root_dir, should trigger interactive for file_patterns
        test_args = ["normalize.py", self.test_dir]
        
        with patch('sys.argv', test_args):
            with patch('builtins.input', side_effect=[
                ".txt",     # file patterns
                "lf",       # format
                "n",        # remove whitespace
                "y",        # preserve tabs
                "",         # ignore dirs (default)
                "",         # workers (default)
            ]):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_time_formatting_minutes(self):
        """Test time formatting for different durations."""
        # Mock time.time to simulate different execution times
        with patch('time.time', side_effect=[0, 90]):  # 90 seconds
            test_args = [
                "normalize.py",
                self.test_dir,
                ".txt",
                "--non-interactive"
            ]
            
            with patch('sys.argv', test_args):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_time_formatting_hours(self):
        """Test time formatting for hours."""
        with patch('time.time', side_effect=[0, 3700]):  # 1+ hour
            test_args = [
                "normalize.py",
                self.test_dir,
                ".txt",
                "--non-interactive"
            ]
            
            with patch('sys.argv', test_args):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_process_files_batch_processing(self):
        """Test batch processing of large file lists."""
        # Create many files to trigger batch processing
        files = []
        for i in range(1005):  # More than batch_size of 1000
            file_path = os.path.join(self.test_dir, f"batch_file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Batch file {i}\r\n")
            files.append(file_path)
        
        processed_count = normalize.process_files_parallel(
            files, 'lf', False, True, max_workers=2
        )
        self.assertEqual(processed_count, 1005)

    def test_no_changes_needed(self):
        """Test files that don't need processing."""
        # Create file with LF endings
        lf_file = os.path.join(self.test_dir, "lf_file.txt")
        with open(lf_file, 'wb') as f:
            f.write(b"Line 1\nLine 2\n")
        
        # Try to process to LF (no change needed)
        result = normalize.process_file(lf_file, 'lf', False, True)
        self.assertFalse(result)  # No changes needed

    def test_debug_logging_level(self):
        """Test debug logging functionality."""
        original_level = normalize.logger.level
        normalize.logger.setLevel(logging.DEBUG)
        
        try:
            # Create file that triggers debug logging
            debug_file = os.path.join(self.test_dir, "debug.txt")
            with open(debug_file, 'wb') as f:
                f.write(b"Debug test\r\n")
            
            result = normalize.process_file(debug_file, 'lf', False, True)
            self.assertTrue(result)
        finally:
            normalize.logger.setLevel(original_level)

    def test_cpu_count_none(self):
        """Test handling when CPU count is None."""
        files = [self.test_file]
        
        with patch('os.cpu_count', return_value=None):
            processed_count = normalize.process_files_parallel(
                files, 'lf', False, True
            )
            # Should handle None CPU count gracefully
            self.assertIsInstance(processed_count, int)


if __name__ == "__main__":
    unittest.main()
