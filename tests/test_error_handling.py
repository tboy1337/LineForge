#!/usr/bin/env python3
"""
Test error handling scenarios for normalize.py.
"""

import os
import sys
import unittest
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, mock_open

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize

# Disable logging for tests
normalize.logger.setLevel(logging.CRITICAL)


class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create test files
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("Test content\n")

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_process_file_nonexistent_file(self):
        """Test processing a file that doesn't exist."""
        result = normalize.process_file(
            "/nonexistent/file.txt", 'lf', False, True
        )
        self.assertFalse(result)

    def test_process_file_permission_error(self):
        """Test processing a file with permission issues."""
        with patch('os.path.exists', return_value=True):
            with patch('os.path.getsize', return_value=10):
                with patch('normalize.is_binary_file', return_value=False):
                    with patch('os.access', return_value=False):
                        result = normalize.process_file(
                            self.test_file, 'lf', False, True
                        )
                        self.assertFalse(result)

    def test_process_file_write_error(self):
        """Test processing a file where writing fails."""
        with patch('builtins.open', side_effect=[
            mock_open(read_data="test content").return_value,
            OSError("Write error")
        ]):
            result = normalize.process_file(
                self.test_file, 'lf', False, True
            )
            self.assertFalse(result)

    def test_process_file_backup_creation_error(self):
        """Test processing when backup creation fails."""
        # Create a file with CRLF that needs to be converted to LF
        test_file = os.path.join(self.test_dir, "backup_test.txt")
        with open(test_file, 'wb') as f:
            f.write(b"test\r\ncontent\r\n")
        
        with patch('shutil.copy2', side_effect=OSError("Backup error")):
            result = normalize.process_file(test_file, 'lf', False, True)
            self.assertTrue(result)  # Should still succeed despite backup failure

    def test_process_file_restore_error(self):
        """Test processing when backup restore fails."""
        with patch('builtins.open', side_effect=[
            mock_open(read_data="test\r\ncontent\r\n").return_value,
            OSError("Write error")
        ]):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.getsize', return_value=10):
                    with patch('normalize.is_binary_file', return_value=False):
                        with patch('os.access', return_value=True):
                            with patch('shutil.copy2', side_effect=[
                                None,  # Backup creation succeeds
                                OSError("Restore error")  # Restore fails
                            ]):
                                result = normalize.process_file(
                                    self.test_file, 'lf', False, True
                                )
                                self.assertFalse(result)

    def test_is_binary_file_os_error(self):
        """Test binary file detection with OS error."""
        with patch('os.path.getsize', side_effect=OSError("Size error")):
            result = normalize.is_binary_file(self.test_file)
            self.assertTrue(result)  # Should assume binary on error

    def test_find_files_pattern_error(self):
        """Test find_files with invalid pattern."""
        # Create a mock pattern that causes an error
        result = normalize.find_files(self.test_dir, ["[invalid"])
        # Should return empty list but not crash
        self.assertIsInstance(result, list)

    def test_empty_file_processing(self):
        """Test processing an empty file."""
        empty_file = os.path.join(self.test_dir, "empty.txt")
        with open(empty_file, 'w') as f:
            pass  # Create empty file
        
        result = normalize.process_file(empty_file, 'lf', False, True)
        self.assertFalse(result)  # Should skip empty files

    def test_debug_logging_exception(self):
        """Test debug logging with exception traceback."""
        # Set debug logging
        original_level = normalize.logger.level
        normalize.logger.setLevel(logging.DEBUG)
        
        try:
            test_args = ["normalize.py", "/invalid/path", ".txt", "--non-interactive"]
            with patch('sys.argv', test_args):
                result = normalize.main()
                self.assertEqual(result, 1)
        finally:
            # Restore original logging level
            normalize.logger.setLevel(original_level)


if __name__ == "__main__":
    unittest.main()
