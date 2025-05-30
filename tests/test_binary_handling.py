#!/usr/bin/env python3
"""
Test binary file handling for normalize.py.
"""

import os
import sys
import unittest
import tempfile
import shutil
import logging
from pathlib import Path

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize

# Disable logging for tests
normalize.logger.setLevel(logging.CRITICAL)

class TestBinaryHandling(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create a text file for comparison with LF line endings
        self.text_file = os.path.join(self.test_dir, "text_file.txt")
        with open(self.text_file, 'wb') as f:  # Use binary mode to control line endings exactly
            f.write(b"This is a text file\nWith multiple lines\n")  # Use LF line endings
        
        # Create a binary file
        self.binary_file = os.path.join(self.test_dir, "binary_file.bin")
        with open(self.binary_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03\xFF\xFE\xFD\xFC')
            
        # Create a PNG-like binary file with extension
        self.png_file = os.path.join(self.test_dir, "image.png")
        with open(self.png_file, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\x0DIHDR\x00\x00')
            
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_binary_file_detection(self):
        """Test that binary files are handled gracefully."""
        # Process the binary file - should not raise exceptions and return False (skipped)
        result = normalize.process_file(self.binary_file, 'lf', False, True)
        # The file shouldn't be modified because it's detected as binary
        self.assertFalse(result)
        
        # Process the PNG file - should not raise exceptions and return False (skipped)
        result = normalize.process_file(self.png_file, 'lf', False, True)
        # The file shouldn't be modified
        self.assertFalse(result)
        
        # Process the text file - should work normally
        # Converting from LF to CRLF should return True (modified)
        result = normalize.process_file(self.text_file, 'crlf', False, True)
        # Should be modified (LF to CRLF)
        self.assertTrue(result)
        
        # Verify the binary files haven't been corrupted
        with open(self.binary_file, 'rb') as f:
            binary_content = f.read()
        self.assertEqual(binary_content, b'\x00\x01\x02\x03\xFF\xFE\xFD\xFC')
        
        with open(self.png_file, 'rb') as f:
            png_content = f.read()
        self.assertEqual(png_content, b'\x89PNG\r\n\x1a\n\x00\x00\x00\x0DIHDR\x00\x00')
        
    def test_is_binary_file(self):
        """Test the is_binary_file function."""
        # Binary file should be detected as binary
        self.assertTrue(normalize.is_binary_file(self.binary_file))
        
        # PNG file should be detected as binary
        self.assertTrue(normalize.is_binary_file(self.png_file))
        
        # Text file should not be detected as binary
        self.assertFalse(normalize.is_binary_file(self.text_file))


if __name__ == "__main__":
    unittest.main() 