#!/usr/bin/env python3
"""
LineForge

A cross-platform Python script to normalize line endings in text files.
"""

import argparse
import concurrent.futures
import logging
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional, Set

from tqdm import tqdm

# Define version
__version__ = "1.0.0"
__author__ = "tboy1337"


# Set up logging with thread-safe handler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("lineforge.log", mode="a")],
)
logger = logging.getLogger("LineForge")
# Add a thread lock for logging
log_lock = threading.Lock()


def is_binary_file(
    file_path: str,
) -> bool:  # pylint: disable=too-many-return-statements
    """
    Check if a file is binary by examining its content.
    Uses multiple heuristics to improve accuracy.
    """
    try:
        # Check file size first - empty files are not binary
        if os.path.getsize(file_path) == 0:
            return False

        # Common binary file extensions
        binary_extensions = {
            ".bin",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".obj",
            ".o",
            ".a",
            ".lib",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".ico",
            ".tif",
            ".tiff",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".xz",
            ".7z",
            ".rar",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".class",
            ".pyc",
            ".pyo",
            ".pyd",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
        }

        # Check extension first for common binary formats
        ext: str = os.path.splitext(file_path)[1].lower()
        if ext in binary_extensions:
            return True

        # Read the first chunk of the file
        with open(file_path, "rb") as f:
            chunk: bytes = f.read(8192)

        # Empty files are not binary
        if not chunk:
            return False

        # Check for NULL bytes (common in binary files)
        if b"\x00" in chunk:
            return True

        # Check for common binary file signatures/magic numbers
        if chunk.startswith(
            (b"\x89PNG", b"GIF8", b"BM", b"\xff\xd8\xff", b"%PDF", b"PK\x03\x04")
        ):
            return True

        # Check for non-text bytes
        # This is a heuristic, might need refinement
        text_characters: bytearray = bytearray(
            {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F}
        )
        non_text: bytes = chunk.translate(None, bytes(text_characters))
        return (
            float(len(non_text)) / len(chunk) > 0.2
        )  # Lowered threshold for better detection
    except Exception as e:  # pylint: disable=broad-exception-caught
        with log_lock:
            logger.error("Error checking if file is binary %s: %s", file_path, str(e))
        return True  # Assume binary on error for safety


def process_file(  # pylint: disable=too-many-return-statements,too-many-branches,too-many-statements
    file_path: str, newline_format: str, remove_whitespace: bool, preserve_tabs: bool
) -> bool:
    """Process a file to normalize line endings and optionally handle whitespace."""
    try:
        # Check if the file exists
        if not os.path.exists(file_path):
            with log_lock:
                logger.error("File not found: %s", file_path)
            return False

        # Check if the file is empty
        if os.path.getsize(file_path) == 0:
            with log_lock:
                logger.debug("Skipping empty file: %s", file_path)
            return False

        # Check if the file is a binary file
        if is_binary_file(file_path):
            with log_lock:
                logger.debug("Skipping binary file: %s", file_path)
            return False

        # Check if the file is readable
        if not os.access(file_path, os.R_OK):
            with log_lock:
                logger.error("File is not readable: %s", file_path)
            return False

        # Check if the file is writable
        if not os.access(file_path, os.W_OK):
            with log_lock:
                logger.error("File is not writable: %s", file_path)
            return False

        # First try with UTF-8 encoding
        content: str
        encoding_used: str
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                content = f.read()
            encoding_used = "utf-8"
        except UnicodeDecodeError:
            # If UTF-8 fails, try with latin-1 encoding (handles any byte sequence)
            with log_lock:
                logger.warning(
                    "UTF-8 decoding failed for %s, falling back to latin-1", file_path
                )
            try:
                with open(file_path, "r", newline="", encoding="latin-1") as f:
                    content = f.read()
                encoding_used = "latin-1"
            except Exception as e:  # pylint: disable=broad-exception-caught
                with log_lock:
                    logger.error(
                        "Failed to read file with latin-1 encoding: %s, error: %s",
                        file_path,
                        str(e),
                    )
                return False

        # Store original content for comparison
        original_content: str = content

        # Create a temporary content variable to hold modified content
        modified_content: str = content

        # Handle whitespace if requested
        if remove_whitespace:
            # Remove extra blank lines (multiple consecutive newlines)
            modified_content = re.sub(
                r"\n\s*\n", "\n\n", modified_content
            )  # Limit to just one blank line
            # Remove trailing whitespace from each line
            modified_content = re.sub(
                r"[ \t]+$", "", modified_content, flags=re.MULTILINE
            )

        # If not preserving tabs, convert tabs to spaces (4 spaces per tab)
        if not preserve_tabs:
            modified_content = modified_content.replace("\t", "    ")

        # Normalize line endings to the requested format
        if newline_format == "crlf":
            # First normalize all to LF, then convert to CRLF
            modified_content = modified_content.replace("\r\n", "\n").replace(
                "\r", "\n"
            )
            modified_content = modified_content.replace("\n", "\r\n")
        else:  # newline_format is 'lf'
            # Normalize all to LF
            modified_content = modified_content.replace("\r\n", "\n").replace(
                "\r", "\n"
            )

        # Only write back if content has changed
        if original_content != modified_content:
            try:
                # Create a backup of the original file
                temp_backup = file_path + ".bak"
                try:
                    shutil.copy2(file_path, temp_backup)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    with log_lock:
                        logger.warning(
                            "Could not create backup of %s: %s", file_path, str(e)
                        )

                # Write with the same encoding we read with
                with open(file_path, "w", newline="", encoding=encoding_used) as f:
                    f.write(modified_content)

                # Remove the backup if write was successful
                if os.path.exists(temp_backup):
                    os.remove(temp_backup)

                with log_lock:
                    logger.debug("Updated file: %s", file_path)
                return True
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Try to restore from backup if write failed
                if os.path.exists(temp_backup):
                    try:
                        shutil.copy2(temp_backup, file_path)
                        os.remove(temp_backup)
                        with log_lock:
                            logger.info(
                                "Restored original file from backup after write error: %s",
                                file_path,
                            )
                    except (
                        Exception
                    ) as restore_err:  # pylint: disable=broad-exception-caught
                        with log_lock:
                            logger.error(
                                "Failed to restore from backup for %s: %s",
                                file_path,
                                str(restore_err),
                            )

                with log_lock:
                    logger.error("Error writing to %s: %s", file_path, str(e))
                return False
        else:
            with log_lock:
                logger.debug("No changes needed for file: %s", file_path)
            return False
    except PermissionError as e:
        with log_lock:
            logger.error("Permission denied accessing %s: %s", file_path, str(e))
        return False
    except Exception as e:  # pylint: disable=broad-exception-caught
        with log_lock:
            logger.error("Error processing %s: %s", file_path, str(e))
        return False


def find_files(
    root_dir: str,
    file_patterns: Optional[List[str]],
    ignore_dirs: Optional[List[str]] = None,
) -> List[str]:
    """Find all files matching the given patterns recursively."""
    if ignore_dirs is None:
        ignore_dirs = [
            ".git",
            ".github",
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
        ]

    all_files: List[str] = []
    ignore_dirs_set: Set[str] = set(ignore_dirs)

    # Handle empty or None file_patterns
    if not file_patterns:
        file_patterns = [".txt"]  # Default to text files if nothing specified

    for pattern in file_patterns:
        pattern = pattern.strip()
        if not pattern:  # Skip empty patterns
            continue

        # Check if pattern is just an extension
        if pattern.startswith(".") and "/" not in pattern and "\\" not in pattern:
            # It's just an extension, make it a glob pattern
            glob_pattern: str = f"*{pattern}"
        else:
            # It's already a proper pattern
            glob_pattern = pattern

        # Walk the directory tree to find matching files
        for root, dirs, files in os.walk(root_dir):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs_set]

            # Find matching files in current directory
            for filename in files:
                file_path: str = os.path.join(root, filename)
                try:
                    if Path(filename).match(glob_pattern):
                        all_files.append(file_path)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    with log_lock:
                        logger.error(
                            "Error matching pattern '%s' to file '%s': %s",
                            glob_pattern,
                            filename,
                            str(e),
                        )

    return all_files


def process_files_parallel(  # pylint: disable=too-many-locals
    files: List[str],
    newline_format: str,
    remove_whitespace: bool,
    preserve_tabs: bool,
    max_workers: Optional[int] = None,
) -> int:
    """Process files in parallel using ThreadPoolExecutor."""
    processed_count: int = 0
    error_count: int = 0
    skipped_count: int = 0

    # Calculate optimal number of workers if not specified
    if max_workers is None:
        # Use minimum of (number of CPUs * 2) or 32, but not more than number of files
        cpu_count: Optional[int] = os.cpu_count()
        max_workers = min((cpu_count or 2) * 2, 32, len(files))
    else:
        # Ensure max_workers is reasonable and not excessive
        max_workers = min(max_workers, 32, len(files))

    with log_lock:
        logger.debug(
            "Using %d worker threads for processing %d files", max_workers, len(files)
        )

    # Process files in batches to avoid excessive memory usage for large file lists
    batch_size = 1000
    for i in range(0, len(files), batch_size):
        batch_files = files[i : i + batch_size]

        with tqdm(
            total=len(batch_files),
            desc=f"Processing files (batch {i//batch_size + 1})",
            unit="file",
        ) as pbar:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                # Submit all file processing tasks
                future_to_file = {
                    executor.submit(
                        process_file,
                        file_path,
                        newline_format,
                        remove_whitespace,
                        preserve_tabs,
                    ): file_path
                    for file_path in batch_files
                }

                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        result = future.result()
                        if result:
                            processed_count += 1
                        else:
                            skipped_count += 1
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        error_count += 1
                        with log_lock:
                            logger.error(
                                "Unhandled error processing %s: %s", file_path, str(e)
                            )
                    finally:
                        pbar.update(1)

    with log_lock:
        if error_count > 0:
            logger.warning("Encountered errors while processing %d files", error_count)
        logger.info(
            "Processed: %d, Skipped: %d, Errors: %d",
            processed_count,
            skipped_count,
            error_count,
        )

    return processed_count


def main() -> (
    int
):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    try:
        # Get the program version from the module
        version: str = getattr(sys.modules[__name__], "__version__", "1.0.0")
        logger.info("LineForge v%s - Line Ending Normalizer", version)

        parser = argparse.ArgumentParser(
            description="Normalize line endings in text files"
        )
        parser.add_argument(
            "root_dir",
            nargs="?",
            default=None,
            help="Root directory to process (default: current directory)",
        )
        parser.add_argument(
            "file_patterns",
            nargs="?",
            default=None,
            help="File patterns to match (e.g., '.txt .py .md')",
        )
        parser.add_argument(
            "--format",
            choices=["crlf", "lf"],
            default="crlf",
            help="Target line ending format (default: crlf)",
        )
        parser.add_argument(
            "--remove-whitespace",
            action="store_true",
            help="Remove extra white space and blank lines",
        )
        parser.add_argument(
            "--preserve-tabs",
            action="store_true",
            help="Preserve tab characters (default: convert to spaces)",
        )
        parser.add_argument(
            "--non-interactive",
            action="store_true",
            help="Run in non-interactive mode with provided options",
        )
        parser.add_argument(
            "--ignore-dirs",
            nargs="+",
            default=[],
            help="Directories to ignore during processing "
            "(default: .git, .github, __pycache__, node_modules, venv, .venv)",
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Enable verbose logging"
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=None,
            help="Number of worker threads for parallel processing "
            "(default: auto-detect based on CPU count)",
        )
        parser.add_argument(
            "--version",
            action="version",
            version=f"LineForge v{version}",
            help="Show program version and exit",
        )

        args = parser.parse_args()

        # Set logging level based on verbosity
        if args.verbose:
            logger.setLevel(logging.DEBUG)

        # Interactive mode if arguments are not provided
        if not args.non_interactive and (
            args.root_dir is None or args.file_patterns is None
        ):
            if args.root_dir is None:
                args.root_dir = input(
                    "Normalize what root directory? [default: current directory] "
                ).strip()
                if not args.root_dir:
                    args.root_dir = os.getcwd()

            if args.file_patterns is None:
                args.file_patterns = input(
                    "Normalize files that end with what? (e.g., '.txt .py') "
                ).strip()
                if not args.file_patterns:
                    args.file_patterns = ".txt"

            format_choice = (
                input("Convert to which line ending format? [crlf/lf, default: crlf] ")
                .strip()
                .lower()
            )
            if format_choice in ["lf", "crlf"]:
                args.format = format_choice

            remove_whitespace = (
                input(
                    "Would you like to get rid of extra white space (y/n)? "
                    "[default: n] "
                )
                .strip()
                .lower()
            )
            args.remove_whitespace = remove_whitespace.startswith("y")

            if not args.remove_whitespace:
                preserve_tabs = (
                    input("Would you like to preserve tabs? (y/n)? [default: n] ")
                    .strip()
                    .lower()
                )
                args.preserve_tabs = preserve_tabs.startswith("y")

            ignore_dirs_input = input(
                "Directories to ignore (space-separated)? "
                "[default: .git .github __pycache__ node_modules venv .venv] "
            ).strip()
            if ignore_dirs_input:
                args.ignore_dirs = ignore_dirs_input.split()

            workers_input = input("Number of worker threads? [default: auto] ").strip()
            if workers_input and workers_input.isdigit():
                args.workers = int(workers_input)

        # Ensure root_dir exists and is valid
        root_dir: str = args.root_dir if args.root_dir else os.getcwd()
        if not os.path.isdir(root_dir):
            logger.error("Error: '%s' is not a valid directory.", root_dir)
            return 1

        # Convert root_dir to absolute path
        root_dir = os.path.abspath(root_dir)

        # Parse file patterns
        file_patterns: List[str] = (
            args.file_patterns.split() if args.file_patterns else [".txt"]
        )

        # Default ignore directories
        default_ignore_dirs: List[str] = [
            ".git",
            ".github",
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
        ]
        ignore_dirs: List[str] = (
            args.ignore_dirs if args.ignore_dirs else default_ignore_dirs
        )

        # Validate workers count
        if args.workers is not None and args.workers <= 0:
            logger.warning(
                "Invalid worker count (%d), using auto-detection instead", args.workers
            )
            args.workers = None

        # Find all matching files
        logger.info(
            "Searching for files in %s matching patterns: %s",
            root_dir,
            " ".join(file_patterns),
        )
        logger.info("Ignoring directories: %s", ", ".join(ignore_dirs))
        logger.info("Target line ending format: %s", args.format.upper())
        logger.info("Remove whitespace: %s", "Yes" if args.remove_whitespace else "No")
        logger.info("Preserve tabs: %s", "Yes" if args.preserve_tabs else "No")

        # Measure execution time
        start_time: float = time.time()

        files: List[str] = find_files(root_dir, file_patterns, ignore_dirs)

        if not files:
            logger.warning("No matching files found.")
            return 0

        logger.info("Found %d files to process.", len(files))

        # Process files with parallel execution
        processed_count: int = process_files_parallel(
            files,
            args.format,
            args.remove_whitespace,
            args.preserve_tabs,
            max_workers=args.workers,
        )

        # Calculate execution time
        execution_time: float = time.time() - start_time

        # Format the execution time nicely
        if execution_time < 60:
            time_str = f"{execution_time:.2f} seconds"
        elif execution_time < 3600:
            minutes = int(execution_time // 60)
            seconds = execution_time % 60
            time_str = (
                f"{minutes} minute{'s' if minutes != 1 else ''} {seconds:.2f} seconds"
            )
        else:
            hours = int(execution_time // 3600)
            minutes = int((execution_time % 3600) // 60)
            seconds = execution_time % 60
            time_str = (
                f"{hours} hour{'s' if hours != 1 else ''} "
                f"{minutes} minute{'s' if minutes != 1 else ''} "
                f"{seconds:.2f} seconds"
            )

        logger.info(
            "Done! Processed %d of %d files in %s.",
            processed_count,
            len(files),
            time_str,
        )
        return 0
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
        return 130
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("An unexpected error occurred: %s", str(e))
        if logger.level <= logging.DEBUG:
            import traceback  # pylint: disable=import-outside-toplevel

            logger.debug("Traceback: %s", traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
