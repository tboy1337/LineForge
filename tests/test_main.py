#!/usr/bin/env python3
"""
Test the main function and command line interface of normalize.py.
"""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize  # pylint: disable=wrong-import-position


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

        # Create test files
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, "wb") as f:
            f.write(b"Line 1\r\nLine 2\r\n")

    def tearDown(self) -> None:
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_main_with_args(self) -> None:
        """Test main function with command line arguments."""
        test_args = [
            "normalize.py",
            self.test_dir,
            ".txt",
            "--format",
            "lf",
            "--remove-whitespace",
            "--non-interactive",
        ]

        with patch("sys.argv", test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_main_no_files_found(self) -> None:
        """Test main function when no matching files are found."""
        test_args = ["normalize.py", self.test_dir, ".nonexistent", "--non-interactive"]

        with patch("sys.argv", test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_main_invalid_directory(self) -> None:
        """Test main function with invalid directory."""
        test_args = [
            "normalize.py",
            "/nonexistent/directory",
            ".txt",
            "--non-interactive",
        ]

        with patch("sys.argv", test_args):
            result = normalize.main()
            self.assertEqual(result, 1)

    def test_main_interactive_mode(self) -> None:
        """Test main function in interactive mode."""
        test_args = ["normalize.py"]

        with patch("sys.argv", test_args):
            with patch(
                "builtins.input",
                side_effect=[
                    self.test_dir,  # root directory
                    ".txt",  # file patterns
                    "lf",  # format
                    "n",  # remove whitespace
                    "n",  # preserve tabs
                    "",  # ignore dirs (default)
                    "",  # workers (default)
                ],
            ):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_main_keyboard_interrupt(self) -> None:
        """Test main function handling KeyboardInterrupt."""
        test_args = ["normalize.py", self.test_dir, ".txt", "--non-interactive"]

        with patch("sys.argv", test_args):
            with patch("normalize.find_files", side_effect=KeyboardInterrupt()):
                result = normalize.main()
                self.assertEqual(result, 130)

    def test_main_exception_handling(self) -> None:
        """Test main function handling unexpected exceptions."""
        test_args = ["normalize.py", self.test_dir, ".txt", "--non-interactive"]

        with patch("sys.argv", test_args):
            with patch("normalize.find_files", side_effect=RuntimeError("Test error")):
                result = normalize.main()
                self.assertEqual(result, 1)

    def test_main_invalid_workers_count(self) -> None:
        """Test main function with invalid workers count."""
        test_args = [
            "normalize.py",
            self.test_dir,
            ".txt",
            "--workers",
            "0",
            "--non-interactive",
        ]

        with patch("sys.argv", test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_main_verbose_mode(self) -> None:
        """Test main function with verbose logging."""
        test_args = [
            "normalize.py",
            self.test_dir,
            ".txt",
            "--verbose",
            "--non-interactive",
        ]

        with patch("sys.argv", test_args):
            result = normalize.main()
            self.assertEqual(result, 0)

    def test_version_argument(self) -> None:
        """Test --version argument."""
        test_args = ["normalize.py", "--version"]

        with patch("sys.argv", test_args):
            with self.assertRaises(SystemExit):
                normalize.main()

    def test_main_interactive_with_defaults(self) -> None:
        """Test main function interactive mode with all defaults."""
        test_args = ["normalize.py"]

        with patch("sys.argv", test_args):
            with patch(
                "builtins.input",
                side_effect=[
                    "",  # root directory (default to current)
                    "",  # file patterns (default to .txt)
                    "",  # format (default to crlf)
                    "",  # remove whitespace (default to n)
                    "",  # preserve tabs (default to n)
                    "",  # ignore dirs (default)
                    "",  # workers (default)
                ],
            ):
                with patch("os.getcwd", return_value=self.test_dir):
                    result = normalize.main()
                    self.assertEqual(result, 0)

    def test_main_interactive_custom_inputs(self) -> None:
        """Test main function interactive mode with custom inputs."""
        test_args = ["normalize.py"]

        with patch("sys.argv", test_args):
            with patch(
                "builtins.input",
                side_effect=[
                    self.test_dir,  # root directory
                    ".txt .py",  # file patterns
                    "lf",  # format
                    "yes",  # remove whitespace
                    "",  # preserve tabs (skip - whitespace removal chosen)
                    "custom_dir",  # ignore dirs
                    "2",  # workers
                ],
            ):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_main_with_partial_args(self) -> None:
        """Test main function with partial arguments triggering interactive mode."""
        # Only provide root_dir, should trigger interactive for file_patterns
        test_args = ["normalize.py", self.test_dir]

        with patch("sys.argv", test_args):
            with patch(
                "builtins.input",
                side_effect=[
                    ".txt",  # file patterns
                    "lf",  # format
                    "n",  # remove whitespace
                    "y",  # preserve tabs
                    "",  # ignore dirs (default)
                    "",  # workers (default)
                ],
            ):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_time_formatting_minutes(self) -> None:
        """Test time formatting for different durations."""
        # Mock time.time to simulate different execution times
        with patch("time.time", side_effect=[0, 90]):  # 90 seconds
            test_args = ["normalize.py", self.test_dir, ".txt", "--non-interactive"]

            with patch("sys.argv", test_args):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_time_formatting_hours(self) -> None:
        """Test time formatting for hours."""
        with patch("time.time", side_effect=[0, 3700]):  # 1+ hour
            test_args = ["normalize.py", self.test_dir, ".txt", "--non-interactive"]

            with patch("sys.argv", test_args):
                result = normalize.main()
                self.assertEqual(result, 0)

    def test_debug_logging_level(self) -> None:
        """Test debug logging functionality."""
        original_level = normalize.logger.level
        normalize.logger.setLevel(logging.DEBUG)

        try:
            # Create file that triggers debug logging
            debug_file = os.path.join(self.test_dir, "debug.txt")
            with open(debug_file, "wb") as f:
                f.write(b"Debug test\r\n")

            result = normalize.process_file(debug_file, "lf", False, True)
            self.assertTrue(result)
        finally:
            normalize.logger.setLevel(original_level)

    def test_interactive_ignore_dirs_input(self) -> None:
        """Test interactive input for ignore directories."""
        # Use minimal args to trigger interactive mode
        test_args = ["normalize.py"]

        with patch("sys.argv", test_args):
            with patch(
                "builtins.input",
                side_effect=[
                    "",  # root_dir (use default current dir)
                    "",  # file_patterns (use default .txt)
                    "",  # format (use default)
                    "n",  # remove_whitespace
                    "n",  # preserve_tabs
                    ".custom .ignore",  # ignore_dirs - this tests line 546
                    "",  # workers (use default)
                ],
            ):
                with patch("normalize.find_files", return_value=[]):
                    with patch("os.getcwd", return_value=self.test_dir):
                        result = normalize.main()
                        self.assertEqual(result, 0)

    def test_interactive_workers_input(self) -> None:
        """Test interactive input for worker threads."""
        # Use minimal args to trigger interactive mode
        test_args = ["normalize.py"]

        with patch("sys.argv", test_args):
            with patch(
                "builtins.input",
                side_effect=[
                    "",  # root_dir (use default current dir)
                    "",  # file_patterns (use default .txt)
                    "",  # format (use default)
                    "n",  # remove_whitespace
                    "n",  # preserve_tabs
                    "",  # ignore_dirs (use default)
                    "4",  # workers - this tests line 550
                ],
            ):
                with patch("normalize.find_files", return_value=[]):
                    with patch("os.getcwd", return_value=self.test_dir):
                        result = normalize.main()
                        self.assertEqual(result, 0)

    def test_debug_traceback_logging(self) -> None:
        """Test debug traceback logging in main exception handler."""
        test_args = ["normalize.py", "nonexistent_dir", ".txt", "--verbose"]

        with patch("sys.argv", test_args):
            with patch("normalize.find_files", side_effect=RuntimeError("Test error")):
                # Set debug level to trigger traceback logging
                with patch.object(normalize.logger, "level", logging.DEBUG):
                    result = normalize.main()
                    self.assertEqual(result, 1)

    def test_main_module_execution(self) -> None:
        """Test the main module execution path (__name__ == '__main__')."""
        # Test executing the module directly to cover line 655
        result = subprocess.run(
            [sys.executable, "normalize.py", "--version"],
            capture_output=True,
            text=True,
            check=False,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )

        # Should exit successfully with version output
        self.assertEqual(result.returncode, 0)
        self.assertIn("LineForge", result.stderr)  # Version goes to stderr in argparse

    def test_debug_traceback_exact(self) -> None:
        """Test debug traceback logging to cover lines 648-650."""
        test_args = ["normalize.py", "invalid_dir", ".txt", "--verbose"]

        with patch("sys.argv", test_args):
            # Mock find_files to raise an exception
            with patch(
                "normalize.find_files", side_effect=RuntimeError("Intentional error")
            ):
                # Ensure logger is at debug level to trigger traceback lines
                original_level = normalize.logger.level
                normalize.logger.setLevel(logging.DEBUG)

                try:
                    result = normalize.main()
                    self.assertEqual(result, 1)
                finally:
                    normalize.logger.setLevel(original_level)

    def test_main_direct_execution(self) -> None:
        """Test direct script execution to cover line 655."""
        # Simple direct execution test - the line is hard to cover in unittest
        # but we can at least verify the script executes correctly when run directly
        result = subprocess.run(
            [sys.executable, "normalize.py", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        # Should execute successfully and show version
        self.assertEqual(result.returncode, 0)
        self.assertIn("LineForge", result.stdout or result.stderr)

    def test_import_traceback_branch(self) -> None:
        """Test the import traceback branch in debug exception handling."""
        test_args = ["normalize.py", ".", ".nonexistent"]

        # Create a scenario where we hit the debug logging with traceback
        with patch("sys.argv", test_args):
            with patch("normalize.logger.level", logging.DEBUG):
                with patch("normalize.find_files", return_value=[]):
                    # Mock os.path.isdir to fail and trigger exception
                    with patch(
                        "os.path.isdir", side_effect=Exception("Directory check failed")
                    ):
                        result = normalize.main()
                        self.assertEqual(result, 1)

    def test_complete_module_import_execution(self) -> None:
        """Ensure the module can be imported and executed correctly."""
        # This ensures we can import the module (which we do in tests)
        # and also that it can be executed directly
        self.assertTrue(hasattr(normalize, "main"))
        self.assertTrue(hasattr(normalize, "process_file"))
        self.assertTrue(hasattr(normalize, "find_files"))
        self.assertTrue(hasattr(normalize, "is_binary_file"))

        # Test that main returns proper exit codes
        with patch("sys.argv", ["normalize.py", "--version"]):
            with patch("sys.exit"):
                try:
                    normalize.main()
                except SystemExit as e:
                    # argparse --version causes SystemExit
                    self.assertEqual(e.code, 0)


if __name__ == "__main__":
    unittest.main()
