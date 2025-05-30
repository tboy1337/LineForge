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
import logging
from pathlib import Path
from tqdm import tqdm


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('lineforge.log', mode='a')
    ]
)
logger = logging.getLogger('LineForge')


def process_file(file_path, newline_format, remove_whitespace, preserve_tabs):
    """Process a file to normalize line endings and optionally handle whitespace."""
    try:
        # First try with UTF-8 encoding
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with latin-1 encoding (which should handle any byte sequence)
            logger.warning(f"UTF-8 decoding failed for {file_path}, falling back to latin-1")
            with open(file_path, 'r', newline='', encoding='latin-1') as f:
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
            # Try to write with the same encoding we read with
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    f.write(modified_content)
            except UnicodeEncodeError:
                with open(file_path, 'w', newline='', encoding='latin-1') as f:
                    f.write(modified_content)
            return True
        return False
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return False


def find_files(root_dir, file_patterns, ignore_dirs=None):
    """Find all files matching the given patterns recursively."""
    if ignore_dirs is None:
        ignore_dirs = ['.git', '.github', '__pycache__', 'node_modules', 'venv', '.venv']
    
    all_files = []
    ignore_dirs_set = set(ignore_dirs)
    
    for pattern in file_patterns:
        pattern = pattern.strip()
        # Make sure the pattern has a leading dot if it's just an extension
        if pattern.startswith('.'):
            pattern = f"*{pattern}"
            
        # Walk the directory tree to find matching files
        for root, dirs, files in os.walk(root_dir):
            # Remove ignored directories from dirs to prevent walk from traversing them
            dirs[:] = [d for d in dirs if d not in ignore_dirs_set]
            
            # Find matching files in current directory
            for filename in files:
                if Path(filename).match(pattern):
                    all_files.append(os.path.join(root, filename))
                    
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
    parser.add_argument(
        "--ignore-dirs",
        nargs="+",
        default=[],
        help="Directories to ignore during processing (default: .git, .github, __pycache__, node_modules, venv, .venv)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
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
            
        ignore_dirs_input = input("Directories to ignore (space-separated)? [default: .git .github __pycache__ node_modules venv .venv] ").strip()
        if ignore_dirs_input:
            args.ignore_dirs = ignore_dirs_input.split()
    
    # Ensure root_dir exists and is valid
    root_dir = args.root_dir if args.root_dir else os.getcwd()
    if not os.path.isdir(root_dir):
        logger.error(f"Error: '{root_dir}' is not a valid directory.")
        sys.exit(1)
        
    # Parse file patterns
    file_patterns = args.file_patterns.split() if args.file_patterns else [".txt"]
    
    # Default ignore directories
    default_ignore_dirs = ['.git', '.github', '__pycache__', 'node_modules', 'venv', '.venv']
    ignore_dirs = args.ignore_dirs if args.ignore_dirs else default_ignore_dirs
    
    # Find all matching files
    logger.info(f"Searching for files in {root_dir} matching patterns: {' '.join(file_patterns)}")
    logger.info(f"Ignoring directories: {', '.join(ignore_dirs)}")
    files = find_files(root_dir, file_patterns, ignore_dirs)
    
    if not files:
        logger.warning("No matching files found.")
        sys.exit(0)
        
    logger.info(f"Found {len(files)} files to process.")
    
    # Process files with progress bar
    processed_count = 0
    with tqdm(total=len(files), desc="Processing files", unit="file") as pbar:
        for file_path in files:
            logger.debug(f"Processing {file_path}...")
            if process_file(file_path, args.format, args.remove_whitespace, args.preserve_tabs):
                processed_count += 1
            pbar.update(1)
            
    logger.info(f"Done! Processed {processed_count} of {len(files)} files.")


if __name__ == "__main__":
    main() 