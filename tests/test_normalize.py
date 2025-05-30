#!/usr/bin/env python3
"""
Tests for normalize.py line ending normalizer.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize

class TestNormalizer(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        
        # Create test files with different line endings
        self.crlf_file = os.path.join(self.test_dir, "crlf_file.txt")
        self.lf_file = os.path.join(self.test_dir, "lf_file.txt")
        self.mixed_file = os.path.join(self.test_dir, "mixed_file.txt")
        self.whitespace_file = os.path.join(self.test_dir, "whitespace_file.txt")
        self.tabs_file = os.path.join(self.test_dir, "tabs_file.txt")
        
        # Create content with CRLF line endings
        with open(self.crlf_file, 'wb') as f:
            f.write(b"Line 1\r\nLine 2\r\nLine 3\r\n")
            
        # Create content with LF line endings
        with open(self.lf_file, 'wb') as f:
            f.write(b"Line 1\nLine 2\nLine 3\n")
            
        # Create content with mixed line endings
        with open(self.mixed_file, 'wb') as f:
            f.write(b"Line 1\r\nLine 2\nLine 3\rLine 4\r\n")
            
        # Create content with extra whitespace
        with open(self.whitespace_file, 'wb') as f:
            f.write(b"Line 1   \nLine 2\n\n\nLine 3\n  Line 4  \n")
            
        # Create content with tabs
        with open(self.tabs_file, 'wb') as f:
            f.write(b"Line 1\n\tIndented Line\n\t\tDouble Indented Line\n")
    
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_crlf_conversion(self):
        """Test conversion to CRLF line endings."""
        # Process the LF file to CRLF
        normalize.process_file(self.lf_file, 'crlf', False, True)
        
        # Read the file as binary to check actual line endings
        with open(self.lf_file, 'rb') as f:
            content = f.read()
            
        # Check that all line endings are CRLF
        self.assertEqual(content.count(b'\r\n'), 3)
        self.assertEqual(content.count(b'\n') - content.count(b'\r\n'), 0)
    
    def test_lf_conversion(self):
        """Test conversion to LF line endings."""
        # Process the CRLF file to LF
        normalize.process_file(self.crlf_file, 'lf', False, True)
        
        # Read the file as binary to check actual line endings
        with open(self.crlf_file, 'rb') as f:
            content = f.read()
            
        # Check that all line endings are LF and no CR exists
        self.assertEqual(content.count(b'\r'), 0)
        # Count the actual number of newlines
        original_newlines = 3
        self.assertEqual(content.count(b'\n'), original_newlines)
    
    def test_mixed_line_endings(self):
        """Test normalization of mixed line endings."""
        # Process the mixed file to LF
        normalize.process_file(self.mixed_file, 'lf', False, True)
        
        # Read the file as binary to check actual line endings
        with open(self.mixed_file, 'rb') as f:
            content = f.read()
            
        # Check that all line endings are normalized to LF
        self.assertEqual(content.count(b'\r'), 0)
        self.assertEqual(content.count(b'\n'), 4)
        
        # Process the mixed file to CRLF
        normalize.process_file(self.mixed_file, 'crlf', False, True)
        
        # Read the file as binary to check actual line endings
        with open(self.mixed_file, 'rb') as f:
            content = f.read()
            
        # Check that all line endings are normalized to CRLF
        self.assertEqual(content.count(b'\r\n'), 4)
    
    def test_whitespace_removal(self):
        """Test removal of extra whitespace."""
        # Process the whitespace file with whitespace removal
        normalize.process_file(self.whitespace_file, 'lf', True, True)
        
        # Read the file as binary to check actual whitespace removal
        with open(self.whitespace_file, 'rb') as f:
            content = f.read()
            
        # There should be no trailing whitespace
        self.assertNotIn(b'   \n', content)
        self.assertNotIn(b'  \n', content)
        # Multiple blank lines should be reduced to one
        self.assertNotIn(b'\n\n\n', content)
    
    def test_tab_conversion(self):
        """Test conversion of tabs to spaces."""
        # Process the tabs file without preserving tabs
        normalize.process_file(self.tabs_file, 'lf', False, False)
        
        # Read the file as text
        with open(self.tabs_file, 'r', newline='', encoding='utf-8') as f:
            content = f.read()
            
        # Tabs should be converted to spaces
        self.assertNotIn('\t', content)
        self.assertIn('    Indented Line', content)
        self.assertIn('        Double Indented Line', content)
    
    def test_find_files(self):
        """Test finding files with specific patterns."""
        # Create a subdirectory with additional files
        subdir = os.path.join(self.test_dir, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "subfile.txt"), 'w') as f:
            f.write("Subdir file")
        with open(os.path.join(subdir, "code.py"), 'w') as f:
            f.write("print('hello')")
            
        # Find all .txt files
        txt_files = normalize.find_files(self.test_dir, [".txt"])
        self.assertEqual(len(txt_files), 6)  # 5 in root + 1 in subdir
        
        # Find all .py files
        py_files = normalize.find_files(self.test_dir, [".py"])
        self.assertEqual(len(py_files), 1)
        
        # Find multiple patterns
        all_files = normalize.find_files(self.test_dir, [".txt", ".py"])
        self.assertEqual(len(all_files), 7)  # 5 txt + 1 py + 1 txt in subdir


if __name__ == "__main__":
    unittest.main() 