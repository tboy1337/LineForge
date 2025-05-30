#!/usr/bin/env python3
"""
LineForge

A cross-platform Python script to normalize line endings in text files.
"""

import os
import sys
import glob
import argparse
import re
from pathlib import Path


def process_file(file_path, newline_format, remove_whitespace, preserve_tabs):
    """Process a file to normalize line endings and optionally handle whitespace."""
    try:
        # Read the file content
        with open(file_path, 'r', newline='', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Create a temporary content variable to hold modified content
        modified_content = content
            
        # Handle whitespace if requested
        if remove_whitespace:
            # Remove extra blank lines (multiple consecutive newlines)
            modified_content = re.sub(r'\n\s*\n', '\n', modified_content)
            # Remove trailing whitespace from each line
            modified_content = re.sub(r'[ \t]+$', '', modified_content, flags=re.MULTILINE)
            
        # If not preserving tabs, convert tabs to spaces (4 spaces per tab)
        if not preserve_tabs:
            modified_content = modified_content.replace('\t', '    ')
            
        # Normalize line endings to the requested format
        if newline_format == 'crlf':
            # First normalize all to LF, then convert to CRLF
            modified_content = modified_content.replace('\r\n', '\n').replace('\r', '\n')
            modified_content = modified_content.replace('\n', '\r\n')
        else:  # newline_format is 'lf'
            # Normalize all to LF
            modified_content = modified_content.replace('\r\n', '\n').replace('\r', '\n')
            
        # Only write back if content has changed
        if content != modified_content:
            # Write the modified content back to the file
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write(modified_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False


def find_files(root_dir, file_patterns):
    """Find all files matching the given patterns recursively."""
    all_files = []
    for pattern in file_patterns:
        pattern = pattern.strip()
        # Make sure the pattern has a leading dot if it's just an extension
        if pattern.startswith('.'):
            pattern = f"*{pattern}"
        # Use recursive glob to find all matching files
        for filepath in Path(root_dir).rglob(pattern):
            if filepath.is_file():
                all_files.append(str(filepath))
    return all_files


def main():
    parser = argparse.ArgumentParser(description="Normalize line endings in text files")
    parser.add_argument(
        "root_dir", 
        nargs="?", 
        default=None, 
        help="Root directory to process (default: current directory)"
    )
    parser.add_argument(
        "file_patterns", 
        nargs="?", 
        default=None, 
        help="File patterns to match (e.g., '.txt .py .md')"
    )
    parser.add_argument(
        "--format", 
        choices=["crlf", "lf"], 
        default="crlf", 
        help="Target line ending format (default: crlf)"
    )
    parser.add_argument(
        "--remove-whitespace", 
        action="store_true", 
        help="Remove extra white space and blank lines"
    )
    parser.add_argument(
        "--preserve-tabs", 
        action="store_true", 
        help="Preserve tab characters (default: convert to spaces)"
    )
    parser.add_argument(
        "--non-interactive", 
        action="store_true", 
        help="Run in non-interactive mode with provided options"
    )
    
    args = parser.parse_args()
    
    # Interactive mode if arguments are not provided
    if not args.non_interactive:
        if args.root_dir is None:
            args.root_dir = input("Normalize what root directory? [default: current directory] ").strip()
            if not args.root_dir:
                args.root_dir = os.getcwd()
        
        if args.file_patterns is None:
            args.file_patterns = input("Normalize files that end with what? (e.g., '.txt .py') ").strip()
            if not args.file_patterns:
                args.file_patterns = ".txt"
                
        format_choice = input("Convert to which line ending format? [crlf/lf, default: crlf] ").strip().lower()
        if format_choice in ['lf', 'crlf']:
            args.format = format_choice
            
        remove_whitespace = input("Would you like to get rid of extra white space (y/n)? [default: n] ").strip().lower()
        args.remove_whitespace = remove_whitespace.startswith('y')
        
        if not args.remove_whitespace:
            preserve_tabs = input("Would you like to preserve tabs? (y/n)? [default: n] ").strip().lower()
            args.preserve_tabs = preserve_tabs.startswith('y')
    
    # Ensure root_dir exists and is valid
    root_dir = args.root_dir if args.root_dir else os.getcwd()
    if not os.path.isdir(root_dir):
        print(f"Error: '{root_dir}' is not a valid directory.")
        sys.exit(1)
        
    # Parse file patterns
    file_patterns = args.file_patterns.split() if args.file_patterns else [".txt"]
    
    # Find all matching files
    print(f"Searching for files in {root_dir} matching patterns: {' '.join(file_patterns)}")
    files = find_files(root_dir, file_patterns)
    
    if not files:
        print("No matching files found.")
        sys.exit(0)
        
    print(f"Found {len(files)} files to process.")
    
    # Process files
    processed_count = 0
    for file_path in files:
        print(f"Processing {file_path}...")
        if process_file(file_path, args.format, args.remove_whitespace, args.preserve_tabs):
            processed_count += 1
            
    print(f"Done! Processed {processed_count} of {len(files)} files.")


if __name__ == "__main__":
    main() 