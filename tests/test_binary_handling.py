#!/usr/bin/env python3
"""
Test binary file handling for normalize.py.
"""

import logging
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize  # pylint: disable=wrong-import-position

# Disable logging for tests
normalize.logger.setLevel(logging.CRITICAL)


class TestBinaryHandling(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

        # Create a text file for comparison with LF line endings
        self.text_file = os.path.join(self.test_dir, "text_file.txt")
        # Use binary mode to control line endings exactly
        with open(self.text_file, "wb") as f:
            # Use LF line endings
            f.write(b"This is a text file\nWith multiple lines\n")

        # Create a binary file
        self.binary_file = os.path.join(self.test_dir, "binary_file.bin")
        with open(self.binary_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe\xfd\xfc")

        # Create a PNG-like binary file with extension
        self.png_file = os.path.join(self.test_dir, "image.png")
        with open(self.png_file, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00\x00")

    def tearDown(self) -> None:
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_binary_file_detection(self) -> None:
        """Test that binary files are handled gracefully."""
        # Process the binary file - should not raise exceptions
        # and return False (skipped)
        result = normalize.process_file(self.binary_file, "lf", False, True)
        # The file shouldn't be modified because it's detected as binary
        self.assertFalse(result)

        # Process the PNG file - should not raise exceptions and return False (skipped)
        result = normalize.process_file(self.png_file, "lf", False, True)
        # The file shouldn't be modified
        self.assertFalse(result)

        # Process the text file - should work normally
        # Converting from LF to CRLF should return True (modified)
        result = normalize.process_file(self.text_file, "crlf", False, True)
        # Should be modified (LF to CRLF)
        self.assertTrue(result)

        # Verify the binary files haven't been corrupted
        with open(self.binary_file, "rb") as f:
            binary_content = f.read()
        self.assertEqual(binary_content, b"\x00\x01\x02\x03\xff\xfe\xfd\xfc")

        with open(self.png_file, "rb") as f:
            png_content = f.read()
        self.assertEqual(png_content, b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x00\x00")

    def test_is_binary_file(self) -> None:
        """Test the is_binary_file function."""
        # Binary file should be detected as binary
        self.assertTrue(normalize.is_binary_file(self.binary_file))

        # PNG file should be detected as binary
        self.assertTrue(normalize.is_binary_file(self.png_file))

        # Text file should not be detected as binary
        self.assertFalse(normalize.is_binary_file(self.text_file))

    def test_is_binary_file_extensions(self) -> None:
        """Test binary file detection by extensions."""
        # Test various binary extensions
        binary_files = [
            "test.exe",
            "test.dll",
            "test.png",
            "test.jpg",
            "test.pdf",
            "test.zip",
            "test.class",
            "test.pyc",
        ]

        for filename in binary_files:
            file_path = os.path.join(self.test_dir, filename)
            # Create file with some content to avoid empty file detection
            with open(file_path, "wb") as f:
                f.write(b"some binary content")

            result = normalize.is_binary_file(file_path)
            self.assertTrue(result, f"Should detect {filename} as binary")

    def test_is_binary_file_magic_numbers(self) -> None:
        """Test binary file detection by magic numbers."""
        magic_files = [
            ("png.txt", b"\x89PNG\r\n\x1a\n"),
            ("gif.txt", b"GIF89a"),
            ("jpg.txt", b"\xff\xd8\xff"),
            ("pdf.txt", b"%PDF-1.4"),
            ("zip.txt", b"PK\x03\x04"),
        ]

        for filename, magic in magic_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, "wb") as f:
                f.write(magic)
                f.write(b"some content after magic")

            result = normalize.is_binary_file(file_path)
            self.assertTrue(
                result, f"Should detect {filename} as binary by magic number"
            )

    def test_is_binary_file_null_bytes(self) -> None:
        """Test binary file detection by null bytes."""
        file_path = os.path.join(self.test_dir, "null_bytes.txt")
        with open(file_path, "wb") as f:
            f.write(b"normal text\x00with null bytes")

        result = normalize.is_binary_file(file_path)
        self.assertTrue(result)

    def test_is_binary_file_non_text_ratio(self) -> None:
        """Test binary file detection by non-text character ratio."""
        file_path = os.path.join(self.test_dir, "non_text.txt")
        # Create content with high ratio of non-text bytes
        with open(file_path, "wb") as f:
            f.write(b"\x01\x02\x03" * 100)  # High ratio of non-text bytes

        result = normalize.is_binary_file(file_path)
        self.assertTrue(result)

    def test_empty_file_binary_detection(self) -> None:
        """Test binary detection for empty files."""
        empty_file = os.path.join(self.test_dir, "empty.txt")
        # Create empty file
        with open(empty_file, "w", encoding="utf-8"):
            pass

        result = normalize.is_binary_file(empty_file)
        self.assertFalse(result)

    def test_empty_chunk_binary_detection(self) -> None:
        """Test binary detection for files that read as empty chunks."""
        test_file = os.path.join(self.test_dir, "test_chunk.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test")

        # Mock the file read to return empty chunk after size check
        with patch("builtins.open", mock_open(read_data=b"")):
            with patch("os.path.getsize", return_value=10):  # Non-zero size
                result = normalize.is_binary_file(test_file)
                self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
