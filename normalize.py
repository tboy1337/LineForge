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
import concurrent.futures
import threading


# Set up logging with thread-safe handler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('lineforge.log', mode='a')
    ]
)
logger = logging.getLogger('LineForge')
# Add a thread lock for logging
log_lock = threading.Lock()


def is_binary_file(file_path):
    """
    Check if a file is binary by reading the first 8192 bytes.
    If it contains NULL bytes or other binary characters, it's likely binary.
    """
    try:
        # Read the first chunk of the file
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            
        # Check for NULL bytes (common in binary files)
        if b'\x00' in chunk:
            return True
            
        # Check for non-text bytes
        # This is a simplified heuristic, might need refinement
        text_characters = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
        non_text = chunk.translate(None, text_characters)
        return float(len(non_text)) / len(chunk) > 0.3
    except Exception as e:
        with log_lock:
            logger.error(f"Error checking if file is binary {file_path}: {str(e)}")
        return True  # Assume binary on error for safety


def process_file(file_path, newline_format, remove_whitespace, preserve_tabs):
    """Process a file to normalize line endings and optionally handle whitespace."""
    try:
        # Check if the file is a binary file
        if is_binary_file(file_path):
            with log_lock:
                logger.debug(f"Skipping binary file: {file_path}")
            return False
            
        # First try with UTF-8 encoding
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with latin-1 encoding (which should handle any byte sequence)
            with log_lock:
                logger.warning(f"UTF-8 decoding failed for {file_path}, falling back to latin-1")
            with open(file_path, 'r', newline='', encoding='latin-1') as f:
                content = f.read()
        
        # Store original content for comparison
        original_content = content
            
        # Create a temporary content variable to hold modified content
        modified_content = content
            
        # Handle whitespace if requested
        if remove_whitespace:
            # Remove extra blank lines (multiple consecutive newlines)
            modified_content = re.sub(r'\n\s*\n', '\n\n', modified_content)  # Limit to just one blank line
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
        if original_content != modified_content:
            # Try to write with the same encoding we read with
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    f.write(modified_content)
                with log_lock:
                    logger.debug(f"Updated file: {file_path}")
                return True
            except UnicodeEncodeError:
                with open(file_path, 'w', newline='', encoding='latin-1') as f:
                    f.write(modified_content)
                with log_lock:
                    logger.debug(f"Updated file: {file_path} (with latin-1 encoding)")
                return True
        else:
            with log_lock:
                logger.debug(f"No changes needed for file: {file_path}")
            return False
    except Exception as e:
        with log_lock:
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
        # Check if pattern is just an extension
        if pattern.startswith('.') and len(pattern.split('.')) == 2:
            # It's just an extension, make it a glob pattern
            glob_pattern = f"*{pattern}"
        else:
            # It's already a proper pattern
            glob_pattern = pattern
            
        # Walk the directory tree to find matching files
        for root, dirs, files in os.walk(root_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs_set]
            
            # Find matching files in current directory
            for filename in files:
                file_path = os.path.join(root, filename)
                if Path(filename).match(glob_pattern):
                    all_files.append(file_path)
                    
    return all_files


def process_files_parallel(files, newline_format, remove_whitespace, preserve_tabs, max_workers=None):
    """Process files in parallel using ThreadPoolExecutor."""
    processed_count = 0
    with tqdm(total=len(files), desc="Processing files", unit="file") as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all file processing tasks
            future_to_file = {
                executor.submit(process_file, file_path, newline_format, remove_whitespace, preserve_tabs): file_path
                for file_path in files
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                with log_lock:
                    logger.debug(f"Processing {file_path}...")
                try:
                    result = future.result()
                    if result:
                        processed_count += 1
                except Exception as e:
                    with log_lock:
                        logger.error(f"Error processing {file_path}: {str(e)}")
                finally:
                    pbar.update(1)
                
    return processed_count


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
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker threads (default: auto-detect based on CPU count)"
    )
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Interactive mode if arguments are not provided
    if not args.non_interactive and (args.root_dir is None or args.file_patterns is None):
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
    
    # Process files with parallel execution
    processed_count = process_files_parallel(
        files, 
        args.format, 
        args.remove_whitespace, 
        args.preserve_tabs,
        max_workers=args.workers
    )
            
    logger.info(f"Done! Processed {processed_count} of {len(files)} files.")


if __name__ == "__main__":
    main() 