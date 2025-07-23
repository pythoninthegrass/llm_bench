# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Dependencies

```bash
# Install dependencies (if pyproject.toml is updated)
uv sync

# Install with development dependencies
uv sync --group dev

# Install with test dependencies
uv sync --group test
```

### Running the Script

```bash
# Direct execution with uv
uv run main.py <model-path>

# Or make executable and run directly
chmod +x main.py
./main.py <model-path>

# Download LocalScore binary
./main.py --download-localscore

# Download a model from HuggingFace
./main.py --download-model

# Download and benchmark in one command
./main.py --download-model --download-localscore
```

### Code Quality

```bash
# Lint and format python code
ruff check
ruff format

# Run ruff with auto-fix
ruff check --fix

# Type checking
uv run mypy main.py
```

### Testing

```bash
# Run all tests with pytest
uv run pytest

# Run with coverage
uv run pytest --cov

# Run tests in parallel
pytest -n auto

# Run with detailed output
pytest -v -s
```

## Development Best Practices

- Always use `uv run` to activate the virtual environment for one-off commands

## Architecture Overview

### Core Structure

This is a Python-based benchmarking tool for GGUF format LLM models using the LocalScore benchmarking utility. The project is designed to be run as a standalone script using uv.

### Key Components

The codebase consists of a single main.py script that:
1. Downloads and manages the LocalScore binary for benchmarking
2. Downloads GGUF models from HuggingFace repositories
3. Runs LocalScore benchmarks against specified models

**Core Functions**:
- `find_localscore()`: Locates the LocalScore binary in PATH or current directory
- `download_localscore()`: Downloads the LocalScore binary from blob.localscore.ai
- `download_model_from_hf()`: Downloads GGUF models from HuggingFace using huggingface-hub
- `run_localscore()`: Executes LocalScore benchmarks using the sh library

### Environment Configuration

Uses `python-decouple` for environment variable management with `.env` file support for local overrides.

Environment variables (can be set in .env file):
- `LOCALSCORE_VERSION`: Version of LocalScore to download (default: 0.9.3)
- `HF_HUB_DISABLE_TELEMETRY`: Disable HuggingFace telemetry (default: 1)
- `HF_REPO_ID`: Default HuggingFace repository for model downloads (default: TheBloke/Llama-2-7B-Chat-GGUF)
- `MODEL_DIR`: Directory for storing downloaded models (default: ./models)

### File Structure Context

- `main.py`: Single-file script with all functionality
- `models/`: Directory for downloaded GGUF models
- `pyproject.toml`: Project dependencies and tool configuration (ruff)
- `ruff.toml`: Ruff configuration for linting/formatting
- `TODO.md`: Project roadmap and future enhancements

### Development Notes

**Code Standards**:
- Line length: 130 characters
- Python 3.13+ requirement
- Ruff for linting/formatting with extensive rule set
- Import ordering and style consistency

**Model Management**:
- Supports automatic GGUF file detection from HuggingFace repos
- Prefers Q4 quantization models when available
- Models stored with original filenames in MODEL_DIR

<!-- ! This section should always be located at the end of the markdown file -->
## Documentation References

- [LocalScore benchmarking tool](https://www.localscore.ai/)
- [LocalScore GitHub repository](https://github.com/cjpais/LocalScore)
- [HuggingFace Hub documentation](https://huggingface.co/docs/huggingface_hub/index)
