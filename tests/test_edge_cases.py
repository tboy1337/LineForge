#!/usr/bin/env python3
"""
Test edge cases and performance scenarios for normalize.py.
"""

import os
import sys
import unittest
import tempfile
import shutil
import time
from pathlib import Path

# Add parent directory to path to import normalize module
sys.path.insert(0, str(Path(__file__).parent.parent))
import normalize


class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_very_long_lines(self):
        """Test processing files with very long lines."""
        long_file = os.path.join(self.test_dir, "long.txt")
        long_line = "a" * 10000 + "\r\n"
        with open(long_file, 'w') as f:
            f.write(long_line * 5)
        
        result = normalize.process_file(long_file, 'lf', False, True)
        self.assertTrue(result)

    def test_many_blank_lines(self):
        """Test processing files with many consecutive blank lines."""
        blank_file = os.path.join(self.test_dir, "blank.txt")
        with open(blank_file, 'w') as f:
            f.write("Line 1\n" + "\n" * 100 + "Line 2\n")
        
        result = normalize.process_file(blank_file, 'lf', True, True)
        self.assertTrue(result)
        
        # Check that blank lines were reduced
        with open(blank_file, 'r') as f:
            content = f.read()
        self.assertLess(content.count('\n\n'), 50)  # Should be reduced

    def test_unicode_content(self):
        """Test processing files with Unicode content."""
        unicode_file = os.path.join(self.test_dir, "unicode.txt")
        with open(unicode_file, 'w', encoding='utf-8') as f:
            f.write("Hello 世界\r\nПривет мир\r\n")
        
        result = normalize.process_file(unicode_file, 'lf', False, True)
        self.assertTrue(result)

    def test_mixed_encodings(self):
        """Test handling files with mixed encoding issues."""
        mixed_file = os.path.join(self.test_dir, "mixed.txt")
        # Write with latin-1 encoding
        with open(mixed_file, 'wb') as f:
            f.write(b"Normal text\r\n")
            f.write(b"Special chars: \xe9\xe8\xe7\r\n")  # Latin-1 chars
        
        result = normalize.process_file(mixed_file, 'lf', False, True)
        self.assertTrue(result)

    def test_large_number_of_files(self):
        """Test processing many files at once."""
        # Create 50 small files
        files = []
        for i in range(50):
            file_path = os.path.join(self.test_dir, f"file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"File {i}\r\nContent\r\n")
            files.append(file_path)
        
        # Test parallel processing
        start_time = time.time()
        processed_count = normalize.process_files_parallel(
            files, 'lf', False, True, max_workers=4
        )
        end_time = time.time()
        
        self.assertEqual(processed_count, 50)
        self.assertLess(end_time - start_time, 5.0)  # Should complete quickly

    def test_file_patterns_edge_cases(self):
        """Test find_files with various pattern edge cases."""
        # Create files with different extensions
        test_files = [
            "test.txt", "test.py", "test.md", "test.config",
            "noextension", ".hidden", "file.txt.backup"
        ]
        
        for filename in test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content\n")
        
        # Test empty patterns
        result = normalize.find_files(self.test_dir, [])
        self.assertIsInstance(result, list)
        
        # Test None patterns
        result = normalize.find_files(self.test_dir, None)
        self.assertIsInstance(result, list)
        
        # Test whitespace patterns
        result = normalize.find_files(self.test_dir, ["  ", ".txt", "  "])
        self.assertGreater(len(result), 0)
        
        # Test complex patterns
        result = normalize.find_files(self.test_dir, ["*.txt", "*.py"])
        self.assertGreater(len(result), 0)

    def test_deep_directory_structure(self):
        """Test processing files in deeply nested directories."""
        # Create a deep directory structure
        deep_dir = self.test_dir
        for i in range(10):
            deep_dir = os.path.join(deep_dir, f"level_{i}")
            os.makedirs(deep_dir, exist_ok=True)
            
            # Add a file at each level
            file_path = os.path.join(deep_dir, f"file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Level {i} content\r\n")
        
        files = normalize.find_files(self.test_dir, [".txt"])
        self.assertGreater(len(files), 5)  # Should find files at multiple levels

    def test_special_characters_in_filenames(self):
        """Test processing files with special characters in names."""
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
        ]
        
        # Add some files that might cause issues in different OS
        if os.name != 'nt':  # Unix systems
            special_names.append("file:with:colons.txt")
        
        for filename in special_names:
            try:
                file_path = os.path.join(self.test_dir, filename)
                with open(file_path, 'w') as f:
                    f.write("Special filename test\r\n")
                
                result = normalize.process_file(file_path, 'lf', False, True)
                self.assertTrue(result)
            except OSError:
                # Skip if filename not allowed on this OS
                continue

    def test_worker_thread_limits(self):
        """Test various worker thread configurations."""
        # Create a few test files
        files = []
        for i in range(5):
            file_path = os.path.join(self.test_dir, f"worker_test_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Worker test {i}\r\n")
            files.append(file_path)
        
        # Test with 1 worker
        result = normalize.process_files_parallel(
            files, 'lf', False, True, max_workers=1
        )
        self.assertEqual(result, 5)
        
        # Test with many workers (should be limited)
        result = normalize.process_files_parallel(
            files, 'lf', False, True, max_workers=100
        )
        self.assertEqual(result, 0)  # Files already processed, no changes

    def test_time_formatting(self):
        """Test the time formatting in main function."""
        # Create a single file for quick processing
        test_file = os.path.join(self.test_dir, "time_test.txt")
        with open(test_file, 'w') as f:
            f.write("Time test\r\n")
        
        test_args = [
            "normalize.py",
            self.test_dir,
            ".txt",
            "--non-interactive",
            "--format", "lf"
        ]
        
        from unittest.mock import patch
        with patch('sys.argv', test_args):
            result = normalize.main()
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
