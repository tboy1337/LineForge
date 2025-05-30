# LineForge

A cross-platform Python script to normalize line endings in text files between CRLF (Windows) and LF (Unix/Linux/macOS).

## Features

- Convert text files to CRLF or LF line endings
- Process files recursively in a directory structure
- Optional whitespace cleaning (removal of extra blank lines and trailing spaces)
- Tab preservation options
- Both interactive and command-line modes
- Cross-platform compatibility (Windows, macOS, Linux)
- UTF-8 encoding support with fallback error handling

## Requirements

- Python 3.6 or higher

## Usage

### Basic Usage

```bash
# Run in interactive mode
python normalize.py

# Process all .txt files in the current directory, converting to CRLF
python normalize.py . .txt

# Process all .py files in a specific directory, converting to LF
python normalize.py /path/to/directory .py --format lf

# Process multiple file types
python normalize.py /path/to/directory ".txt .py .md" --format crlf
```

### Command Line Arguments

```
usage: normalize.py [-h] [--format {crlf,lf}] [--remove-whitespace] 
                   [--preserve-tabs] [--non-interactive]
                   [root_dir] [file_patterns]

Normalize line endings in text files

positional arguments:
  root_dir              Root directory to process (default: current directory)
  file_patterns         File patterns to match (e.g., '.txt .py .md')

options:
  -h, --help            show this help message and exit
  --format {crlf,lf}    Target line ending format (default: crlf)
  --remove-whitespace   Remove extra white space and blank lines
  --preserve-tabs       Preserve tab characters (default: convert to spaces)
  --non-interactive     Run in non-interactive mode with provided options
```

### Examples

**Convert all Python files to Unix/Linux line endings (LF):**
```bash
python normalize.py . .py --format lf
```

**Convert all text files to Windows line endings (CRLF) and remove extra whitespace:**
```bash
python normalize.py . .txt --format crlf --remove-whitespace
```

**Process multiple file types in non-interactive mode:**
```bash
python normalize.py /path/to/project ".py .js .html" --format lf --non-interactive
```

## Notes

- The script operates on files in-place, so make sure to back up important files before processing.
- By default, tabs are converted to spaces (4 spaces per tab) unless the `--preserve-tabs` option is used.
- The script attempts to handle various text encodings, but works best with UTF-8 encoded files.

## Repository

This project is hosted at [https://github.com/tboy1337/LineForge](https://github.com/tboy1337/LineForge)

## License

This tool is provided as open-source software under the MIT License. See the [LICENSE](LICENSE.txt) file for details. 