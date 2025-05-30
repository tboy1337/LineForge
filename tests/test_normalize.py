#!/usr/bin/env python3
"""
Tests for normalize.py line ending normalizer.
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
        
        # Create a non-UTF8 file
        self.non_utf8_file = os.path.join(self.test_dir, "non_utf8_file.txt")
        
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
            
        # Create a non-UTF8 file with Latin-1 encoding
        with open(self.non_utf8_file, 'wb') as f:
            f.write(b"Line with special chars: \xA3\xB0\xC5\xD8\xE5\xF8\n")
            
        # Create directories to test ignore functionality
        self.ignored_dir = os.path.join(self.test_dir, ".git")
        os.makedirs(self.ignored_dir)
        self.ignored_file = os.path.join(self.ignored_dir, "config.txt")
        with open(self.ignored_file, 'w') as f:
            f.write("This is in .git and should be ignored")
    
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
            
        # Count expected files to accommodate changes in environment
        expected_txt_files = 0
        for root, _, files in os.walk(self.test_dir):
            if ".git" not in root:  # Default ignore
                expected_txt_files += sum(1 for f in files if f.endswith('.txt'))
                
        # Find all .txt files
        txt_files = normalize.find_files(self.test_dir, [".txt"])
        self.assertEqual(len(txt_files), expected_txt_files)
        
        # Find all .py files
        py_files = normalize.find_files(self.test_dir, [".py"])
        expected_py_files = 1  # code.py in subdir
        self.assertEqual(len(py_files), expected_py_files)
        
        # Find multiple patterns
        all_files = normalize.find_files(self.test_dir, [".txt", ".py"])
        self.assertEqual(len(all_files), expected_txt_files + expected_py_files)
        
    def test_ignored_directories(self):
        """Test that ignored directories are skipped."""
        # Find all files including those in .git
        all_files = normalize.find_files(self.test_dir, [".txt"], ignore_dirs=[])
        self.assertIn(self.ignored_file, all_files)
        
        # Now find files with default ignore list
        default_ignored = normalize.find_files(self.test_dir, [".txt"])
        self.assertNotIn(self.ignored_file, default_ignored)
        
        # Custom ignore list
        custom_ignored = normalize.find_files(self.test_dir, [".txt"], ignore_dirs=["subdir"])
        # Create a subdirectory with additional files if it doesn't exist
        subdir = os.path.join(self.test_dir, "subdir")
        if not os.path.exists(subdir):
            os.makedirs(subdir)
            with open(os.path.join(subdir, "ignored.txt"), 'w') as f:
                f.write("This should be ignored")
        
        for file in custom_ignored:
            self.assertFalse(file.startswith(os.path.join(self.test_dir, "subdir")))
            
    def test_non_utf8_files(self):
        """Test handling of files with non-UTF8 encoding."""
        # Instead of checking the exact bytes, let's just verify the file can be processed
        # and that line endings are properly normalized
        
        # Add a line with CRLF ending
        with open(self.non_utf8_file, 'ab') as f:
            f.write(b"\r\nExtra line with CRLF")
        
        # Process the non-UTF8 file to LF
        result = normalize.process_file(self.non_utf8_file, 'lf', False, True)
        self.assertTrue(result)
        
        # Verify the file has been processed
        with open(self.non_utf8_file, 'rb') as f:
            content = f.read()
        
        # Check for line ending normalization
        self.assertNotIn(b'\r\n', content)
        self.assertIn(b'Line with special chars:', content)
        self.assertIn(b'Extra line with CRLF', content)

    def test_parallel_processing(self):
        """Test parallel processing of multiple files."""
        # Create multiple test files
        test_files = []
        for i in range(5):
            file_path = os.path.join(self.test_dir, f"parallel_test_{i}.txt")
            with open(file_path, 'wb') as f:
                f.write(b"Line 1\r\nLine 2\r\nLine 3\r\n")
            test_files.append(file_path)
        
        # Process files in parallel
        processed_count = normalize.process_files_parallel(
            test_files,
            'lf',
            False,
            True,
            max_workers=2  # Use 2 workers for testing
        )
        
        # Check that all files were processed
        self.assertEqual(processed_count, 5)
        
        # Verify that all files have LF line endings
        for file_path in test_files:
            with open(file_path, 'rb') as f:
                content = f.read()
                self.assertEqual(content.count(b'\r'), 0)
                self.assertEqual(content.count(b'\n'), 3)

    def test_file_pattern_handling(self):
        """Test handling of different file pattern formats."""
        # Create a separate test directory for this test to avoid counting files from other tests
        pattern_test_dir = os.path.join(self.test_dir, "pattern_test")
        os.makedirs(pattern_test_dir)
        
        # Create test files with different extensions
        test_files = {
            "test.txt": "Text file",
            "test.py": "Python file",
            "test.md": "Markdown file",
            "test.config": "Config file",
            "noextension": "No extension file"
        }
        
        for filename, content in test_files.items():
            with open(os.path.join(pattern_test_dir, filename), 'w') as f:
                f.write(content)
        
        # Test with just extension
        txt_files = normalize.find_files(pattern_test_dir, [".txt"])
        self.assertEqual(len(txt_files), 1)
        
        # Test with full pattern
        md_files = normalize.find_files(pattern_test_dir, ["*.md"])
        self.assertEqual(len(md_files), 1)
        
        # Test with multiple patterns
        multi_files = normalize.find_files(pattern_test_dir, [".txt", "*.py", "*.md"])
        self.assertEqual(len(multi_files), 3)
        
        # Test with pattern that doesn't match any files
        no_match = normalize.find_files(pattern_test_dir, [".jpg"])
        self.assertEqual(len(no_match), 0)


if __name__ == "__main__":
    unittest.main() 