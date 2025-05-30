#!/usr/bin/env python3
"""
Create a test file with mixed line endings for testing the line ending normalizer.
"""

import os
from pathlib import Path

# Create the test_files directory if it doesn't exist
test_files_dir = Path(__file__).parent / "test_files"
test_files_dir.mkdir(exist_ok=True)

# Create a file with mixed line endings
test_file_path = test_files_dir / "mixed.txt"

# Define content with explicit line endings
content = (
    b"This is a line with CRLF line ending\r\n"
    b"This is a line with LF line ending\n"
    b"This is another line with CRLF line ending\r\n"
    b"This is a line with CR line ending\r"
    b"This is a line with trailing whitespace   \r\n"
    b"\tThis line has tab indentation\n"
    b"\t\tThis line has double tab indentation\r\n"
    b"\r\n"
    b"\n"
    b"\r\n"
    b"This line has multiple blank lines before it"
)

# Write content to file in binary mode
with open(test_file_path, 'wb') as f:
    f.write(content)

print(f"Created test file: {test_file_path}") 