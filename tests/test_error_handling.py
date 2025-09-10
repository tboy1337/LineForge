#!/usr/bin/env python3
"""
Test error handling scenarios for normalize.py.
"""

import logging
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize  # pylint: disable=wrong-import-position

# Disable logging for tests
normalize.logger.setLevel(logging.CRITICAL)


class TestErrorHandling(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

        # Create test files
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("Test content\n")

    def tearDown(self) -> None:
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_process_file_nonexistent_file(self) -> None:
        """Test processing a file that doesn't exist."""
        result = normalize.process_file("/nonexistent/file.txt", "lf", False, True)
        self.assertFalse(result)

    def test_process_file_permission_error(self) -> None:
        """Test processing a file with permission issues."""
        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=10):
                with patch("normalize.is_binary_file", return_value=False):
                    with patch("os.access", return_value=False):
                        result = normalize.process_file(
                            self.test_file, "lf", False, True
                        )
                        self.assertFalse(result)

    def test_process_file_write_error(self) -> None:
        """Test processing a file where writing fails."""
        with patch(
            "builtins.open",
            side_effect=[
                mock_open(read_data="test content").return_value,
                OSError("Write error"),
            ],
        ):
            result = normalize.process_file(self.test_file, "lf", False, True)
            self.assertFalse(result)

    def test_process_file_backup_creation_error(self) -> None:
        """Test processing when backup creation fails."""
        # Create a file with CRLF that needs to be converted to LF
        test_file = os.path.join(self.test_dir, "backup_test.txt")
        with open(test_file, "wb") as f:
            f.write(b"test\r\ncontent\r\n")

        with patch("shutil.copy2", side_effect=OSError("Backup error")):
            result = normalize.process_file(test_file, "lf", False, True)
            self.assertTrue(result)  # Should still succeed despite backup failure

    def test_process_file_restore_error(self) -> None:
        """Test processing when backup restore fails."""
        with patch(
            "builtins.open",
            side_effect=[
                mock_open(read_data="test\r\ncontent\r\n").return_value,
                OSError("Write error"),
            ],
        ):
            with patch("os.path.exists", return_value=True):
                with patch("os.path.getsize", return_value=10):
                    with patch("normalize.is_binary_file", return_value=False):
                        with patch("os.access", return_value=True):
                            with patch(
                                "shutil.copy2",
                                side_effect=[
                                    None,  # Backup creation succeeds
                                    OSError("Restore error"),  # Restore fails
                                ],
                            ):
                                result = normalize.process_file(
                                    self.test_file, "lf", False, True
                                )
                                self.assertFalse(result)

    def test_is_binary_file_os_error(self) -> None:
        """Test binary file detection with OS error."""
        with patch("os.path.getsize", side_effect=OSError("Size error")):
            result = normalize.is_binary_file(self.test_file)
            self.assertTrue(result)  # Should assume binary on error

    def test_find_files_pattern_error(self) -> None:
        """Test find_files with invalid pattern."""
        # Create a mock pattern that causes an error
        result = normalize.find_files(self.test_dir, ["[invalid"])
        # Should return empty list but not crash
        self.assertIsInstance(result, list)

    def test_empty_file_processing(self) -> None:
        """Test processing an empty file."""
        empty_file = os.path.join(self.test_dir, "empty.txt")
        with open(empty_file, "w", encoding="utf-8"):
            pass  # Create empty file

        result = normalize.process_file(empty_file, "lf", False, True)
        self.assertFalse(result)  # Should skip empty files

    def test_debug_logging_exception(self) -> None:
        """Test debug logging with exception traceback."""
        # Set debug logging
        original_level = normalize.logger.level
        normalize.logger.setLevel(logging.DEBUG)

        try:
            test_args = ["normalize.py", "/invalid/path", ".txt", "--non-interactive"]
            with patch("sys.argv", test_args):
                result = normalize.main()
                self.assertEqual(result, 1)
        finally:
            # Restore original logging level
            normalize.logger.setLevel(original_level)

    def test_file_not_writable(self) -> None:
        """Test process_file with non-writable file."""
        readonly_file = os.path.join(self.test_dir, "readonly.txt")
        with open(readonly_file, "w", encoding="utf-8") as f:
            f.write("test content\n")

        # Make file read-only
        os.chmod(readonly_file, stat.S_IREAD)

        try:
            result = normalize.process_file(readonly_file, "lf", False, True)
            self.assertFalse(result)
        finally:
            # Restore write permissions for cleanup
            os.chmod(readonly_file, stat.S_IREAD | stat.S_IWRITE)

    def test_latin1_encoding_failure(self) -> None:
        """Test latin-1 encoding failure fallback."""
        test_file = os.path.join(self.test_dir, "encoding_test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test content\n")

        # Mock the specific open calls to trigger the latin-1 fallback failure
        open_call_count = 0

        def mock_open_side_effect(
            filename: str, mode: str = "r", **kwargs: Any
        ) -> object:
            nonlocal open_call_count
            open_call_count += 1

            # First call for UTF-8 reading - fail
            if (
                open_call_count == 1
                and "encoding" in kwargs
                and kwargs["encoding"] == "utf-8"
            ):
                raise UnicodeDecodeError("utf-8", b"test", 0, 1, "invalid start byte")
            # Second call for latin-1 reading - fail
            if (
                open_call_count == 2
                and "encoding" in kwargs
                and kwargs["encoding"] == "latin-1"
            ):
                raise IOError("Simulated latin-1 failure")
            else:
                return mock_open(read_data="test content\n").return_value

        with patch("builtins.open", side_effect=mock_open_side_effect):
            result = normalize.process_file(test_file, "lf", False, True)
            self.assertFalse(result)

    def test_backup_restore_failure(self) -> None:
        """Test backup restoration failure scenario."""
        test_file = os.path.join(self.test_dir, "backup_test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test content\r\n")

        # Create detailed mock sequence to trigger restore failure
        mock_file = MagicMock()
        mock_file.read.return_value = "test content\r\n"
        mock_file.__enter__.return_value = mock_file
        mock_file.__exit__.return_value = None

        # Track copy2 calls: first for backup creation (success), second for restore (fail)
        copy2_call_count = 0

        def copy2_side_effect(*args: Any, **kwargs: Any) -> None:
            nonlocal copy2_call_count
            copy2_call_count += 1
            if copy2_call_count == 2:  # Second call is restore
                raise Exception("Restore failed")
            return None  # First call succeeds

        with patch("shutil.copy2", side_effect=copy2_side_effect):
            with patch("builtins.open") as mock_open_func:
                # Setup open mock sequence: read success, write fail
                mock_open_func.side_effect = [
                    mock_file,  # Read file
                    Exception("Write failed"),  # Write fails
                ]
                with patch("os.path.exists", return_value=True):
                    with patch("os.remove", side_effect=Exception("Remove failed")):
                        result = normalize.process_file(test_file, "lf", False, True)
                        self.assertFalse(result)

    def test_permission_error_in_process_file(self) -> None:
        """Test PermissionError handling in process_file."""
        with patch("os.path.exists", side_effect=PermissionError("Permission denied")):
            result = normalize.process_file("dummy_path", "lf", False, True)
            self.assertFalse(result)

    def test_general_exception_in_process_file(self) -> None:
        """Test general exception handling in process_file."""
        with patch("os.path.exists", side_effect=RuntimeError("Unexpected error")):
            result = normalize.process_file("dummy_path", "lf", False, True)
            self.assertFalse(result)

    def test_pattern_matching_error_in_find_files(self) -> None:
        """Test pattern matching error handling in find_files."""
        # Create a test file
        test_file = os.path.join(self.test_dir, "pattern_test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test")

        # Mock Path.match to raise an exception
        with patch.object(Path, "match", side_effect=Exception("Pattern error")):
            result = normalize.find_files(self.test_dir, [".txt"])
            # Should return empty list on pattern error
            self.assertEqual(result, [])

    def test_parallel_processing_exception_handling(self) -> None:
        """Test exception handling in parallel processing."""
        # Create test files
        test_files = []
        for i in range(3):
            test_file = os.path.join(self.test_dir, f"parallel_test_{i}.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("test content\n")
            test_files.append(test_file)

        # Mock process_file to raise exception for one file
        def mock_process_file(file_path: str, *args: Any, **kwargs: Any) -> bool:
            if "parallel_test_1" in file_path:
                raise RuntimeError("Process file error")
            return True

        with patch("normalize.process_file", side_effect=mock_process_file):
            result = normalize.process_files_parallel(
                test_files, "lf", False, True, max_workers=2
            )
            # Should handle exceptions and return successful count (2 out of 3)
            self.assertEqual(result, 2)

    def test_latin1_encoding_exact_failure(self) -> None:
        """Test exact latin-1 encoding failure scenario to cover lines 183-190."""
        test_file = os.path.join(self.test_dir, "encoding_fail.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test content\n")

        # Bypass all the early checks by patching them
        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=100):  # Non-empty file
                with patch(
                    "normalize.is_binary_file", return_value=False
                ):  # Not binary
                    with patch("os.access", return_value=True):  # Readable and writable

                        # Track encoding calls
                        call_sequence = []

                        def track_open(
                            filename: str, mode: str = "r", **kwargs: Any
                        ) -> object:
                            encoding = kwargs.get("encoding")
                            call_sequence.append(encoding)

                            if encoding == "utf-8":
                                # First call - UTF-8 fails
                                raise UnicodeDecodeError(
                                    "utf-8", b"test", 0, 1, "invalid start byte"
                                )
                            elif encoding == "latin-1":
                                # Second call - latin-1 also fails (lines 183-190)
                                raise OSError("Simulated latin-1 read error")
                            else:
                                # Default mock for other calls
                                mock_file = MagicMock()
                                mock_file.__enter__ = MagicMock(return_value=mock_file)
                                mock_file.__exit__ = MagicMock(return_value=None)
                                return mock_file

                        with patch("builtins.open", side_effect=track_open):
                            result = normalize.process_file(
                                test_file, "lf", False, True
                            )
                            self.assertFalse(result)
                            # Verify we hit both UTF-8 and latin-1 encoding failures
                            self.assertIn("utf-8", call_sequence)
                            self.assertIn("latin-1", call_sequence)

    def test_backup_restore_precise_failure(self) -> None:
        """Test precise backup restoration failure to cover lines 255-257."""
        test_file = os.path.join(self.test_dir, "restore_fail.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("original content\r\n")

        # Bypass all the early checks
        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=100):
                with patch("normalize.is_binary_file", return_value=False):
                    with patch("os.access", return_value=True):

                        # Create mock file read that returns content requiring change
                        mock_read_file = MagicMock()
                        mock_read_file.read.return_value = "original content\r\n"
                        mock_read_file.__enter__ = MagicMock(
                            return_value=mock_read_file
                        )
                        mock_read_file.__exit__ = MagicMock(return_value=None)

                        # Mock for write operation that fails
                        mock_write_file = MagicMock()
                        mock_write_file.__enter__ = MagicMock(
                            return_value=mock_write_file
                        )
                        mock_write_file.__exit__ = MagicMock(
                            side_effect=IOError("Write operation failed")
                        )
                        mock_write_file.write = MagicMock(
                            side_effect=IOError("Write failed")
                        )

                        open_call_count = 0

                        def mock_open_sequence(*args: Any, **kwargs: Any) -> object:
                            nonlocal open_call_count
                            open_call_count += 1

                            if open_call_count == 1:
                                # First call: read original file (success)
                                return mock_read_file
                            else:
                                # Second call: write file (return mock that fails)
                                return mock_write_file

                        # Track shutil.copy2 calls for backup and restore
                        copy2_call_count = 0

                        def failing_copy2(*args: Any, **kwargs: Any) -> None:
                            nonlocal copy2_call_count
                            copy2_call_count += 1
                            if copy2_call_count == 1:
                                # First call: backup creation succeeds
                                pass
                            else:
                                # Second call: restore fails (lines 255-257)
                                raise OSError("Restore backup failed")

                        with patch("builtins.open", side_effect=mock_open_sequence):
                            with patch("shutil.copy2", side_effect=failing_copy2):
                                with patch(
                                    "os.path.exists", return_value=True
                                ):  # Backup file exists
                                    with patch(
                                        "os.remove"
                                    ):  # Mock remove to avoid file system issues
                                        result = normalize.process_file(
                                            test_file, "lf", False, True
                                        )
                                        self.assertFalse(result)
                                        # Should have attempted both backup creation and restore
                                        self.assertEqual(copy2_call_count, 2)


if __name__ == "__main__":
    unittest.main()
