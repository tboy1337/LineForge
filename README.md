# LineForge

A cross-platform Python utility for normalizing line endings in text files. Easily convert between CRLF and LF line endings while also handling whitespace cleanup.

## Features

- Convert line endings to CRLF (Windows) or LF (Unix/Linux/macOS)
- Normalize mixed line endings within a single file
- Remove trailing whitespace from lines
- Collapse multiple blank lines
- Convert tabs to spaces (optional)
- Process files recursively across directories
- Filter files by extension patterns
- Ignore specific directories (.git, .github, node_modules, etc.)
- Progress bar for tracking file processing
- Robust handling of different file encodings (UTF-8, Latin-1)
- Detailed logging for monitoring and debugging
- Interactive and non-interactive modes

## Installation

Clone the repository:

```bash
git clone https://github.com/tboy1337/LineForge.git
cd LineForge
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Interactive Mode

Run the script without arguments for interactive mode:

```bash
python normalize.py
```

You'll be prompted for:
- Root directory to process (default: current directory)
- File patterns to match (e.g., '.txt .py .md')
- Target line ending format (CRLF or LF)
- Whether to remove extra whitespace
- Whether to preserve tabs
- Directories to ignore

### Command Line Arguments

```bash
python normalize.py [root_dir] [file_patterns] [options]
```

#### Options:

- `--format {crlf,lf}`: Target line ending format (default: crlf)
- `--remove-whitespace`: Remove extra white space and blank lines
- `--preserve-tabs`: Preserve tab characters (default: convert to spaces)
- `--non-interactive`: Run in non-interactive mode with provided options
- `--ignore-dirs`: Directories to ignore during processing (default: .git, .github, __pycache__, node_modules, venv, .venv)
- `--verbose`: Enable verbose logging

### Examples

Convert all .txt files in the current directory to CRLF line endings:
```bash
python normalize.py . ".txt" --format crlf
```

Convert all Python and Markdown files in a specific directory to LF, remove whitespace, and convert tabs to spaces:
```bash
python normalize.py /path/to/project ".py .md" --format lf --remove-whitespace
```

Process all text files but ignore certain directories:
```bash
python normalize.py . ".txt .md .py" --format lf --ignore-dirs .git build dist
```

Enable verbose logging for detailed information:
```bash
python normalize.py . ".txt" --verbose
```

## Testing

LineForge includes comprehensive tests to ensure correct functionality:

```bash
python -m unittest tests/test_normalize.py
```

## License

LineForge is released under the MIT License. See [LICENSE.txt](LICENSE.txt) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 