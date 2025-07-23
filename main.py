#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "httpx>=0.28.1",
#     "huggingface-hub>=0.33.4",
#     "python-decouple>=3.8",
#     "sh>=2.2.2",
# ]
# [tool.uv]
# exclude-newer = "2025-07-23T00:00:00Z"
# ///

# pyright: reportMissingImports=false

"""
Usage:
    llm-bench [--download-localscore] [--download-model] <model-path>

Args:
    model-path:             Path to the GGUF model file to benchmark

Options:
    --download-localscore:  Download the localscore binary
    --download-model:       Download a model from HuggingFace

Note:
    After downloading, copy or symlink this script to a location in your PATH
    (e.g., ~/.local/bin/llm-bench) for easier access.
"""

import httpx
import os
import sh
import stat
from huggingface_hub import hf_hub_download, hf_hub_url, list_repo_files
from pathlib import Path
from sh import ErrorReturnCode

env_file = Path.cwd() / ".env"
if env_file.exists():
    from decouple import Config, RepositoryEnv
    config = Config(RepositoryEnv(env_file))
else:
    from decouple import config

LOCALSCORE_VERSION = config("LOCALSCORE_VERSION", default="0.9.3")
LOCALSCORE_URL = f"https://blob.localscore.ai/localscore-{LOCALSCORE_VERSION}"
LOCALSCORE_BIN = "localscore"
HF_HUB_DISABLE_TELEMETRY = config("HF_HUB_DISABLE_TELEMETRY", default="1")
HF_REPO_ID = config("HF_REPO_ID", default="TheBloke/Llama-2-7B-Chat-GGUF")
MODEL_DIR = Path(config("MODEL_DIR", default=str(Path.cwd() / "models"))).expanduser().resolve()


def find_localscore():
    """Find localscore binary and return its absolute path"""
    # First check PATH
    path_str = os.environ.get('PATH', '')
    path_dirs = path_str.split(os.pathsep)
    for path_dir in path_dirs:
        path_dir = Path(path_dir).expanduser().resolve()
        if path_dir.exists() and path_dir.is_dir():
            localscore_path = path_dir / LOCALSCORE_BIN
            # Check if file exists, is a file, and is executable
            if localscore_path.exists() and localscore_path.is_file() and os.access(localscore_path, os.X_OK):
                return localscore_path

    # Then check current directory
    local_path = Path.cwd() / LOCALSCORE_BIN
    if local_path.exists() and local_path.is_file() and os.access(local_path, os.X_OK):
        return local_path.resolve()

    return None


def download_localscore(force=False):
    """Download localscore binary via httpx"""
    # Check if localscore is already available
    if not force and find_localscore():
        print("localscore is already available. Use --force to download anyway.")
        return

    print(f"Downloading localscore {LOCALSCORE_VERSION}...")

    response = httpx.get(LOCALSCORE_URL, follow_redirects=True)
    response.raise_for_status()

    # Save with the version-specific name first
    temp_filename = f"localscore-{LOCALSCORE_VERSION}"
    with open(temp_filename, "wb") as f:
        f.write(response.content)

    # Make executable
    st = os.stat(temp_filename)
    os.chmod(temp_filename, st.st_mode | stat.S_IEXEC)

    # Rename to just 'localscore'
    if Path(LOCALSCORE_BIN).exists():
        os.remove(LOCALSCORE_BIN)
    os.rename(temp_filename, LOCALSCORE_BIN)

    print(f"Downloaded and made executable: {LOCALSCORE_BIN}")


def download_model_from_hf(repo_id=None, filename=None):
    """Use hf_hub_download to download models"""
    if repo_id is None:
        repo_id = HF_REPO_ID

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading model from {repo_id}...")

    try:
        if filename is None:
            # List available files and find a GGUF file
            files = list_repo_files(repo_id=repo_id)
            gguf_files = [f for f in files if f.endswith('.gguf')]

            if not gguf_files:
                print(f"Error: No GGUF files found in repository {repo_id}")
                return None

            # Use the first GGUF file found, or prefer one with 'q4' (common quantization)
            filename = next((f for f in gguf_files if 'q4' in f.lower()), gguf_files[0])
            print(f"Found GGUF file: {filename}")

        # Construct the URL for verification
        url = hf_hub_url(repo_id=repo_id, filename=filename)
        print(f"Downloading from: {url}")

        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=MODEL_DIR,
        )

        print(f"Model downloaded to: {model_path}")
        return Path(model_path)

    except Exception as e:
        print(f"Error downloading model: {e}")
        return None


def run_localscore(model_path):
    """Run localscore against a GGUF model"""
    # Find localscore binary
    localscore_path = find_localscore()
    if not localscore_path:
        print("Error: localscore not found in PATH or current directory. Run with --download-localscore first.")
        return 1

    # Use the binary name if in PATH, otherwise use absolute path
    if str(localscore_path.parent) in os.environ.get('PATH', '').split(os.pathsep):
        cmd_name = "localscore"
    else:
        cmd_name = str(localscore_path)

    # Convert model_path to Path object
    model_path = Path(model_path)

    # Track paths we've tried for better error messages
    tried_paths = []

    # If the path is relative and doesn't exist, try prepending MODEL_DIR
    if not model_path.is_absolute() and not model_path.exists():
        tried_paths.append(model_path.resolve())
        model_path_with_base = MODEL_DIR / model_path
        tried_paths.append(model_path_with_base.resolve())
        if model_path_with_base.exists():
            model_path = model_path_with_base

    # Resolve to absolute path
    model_path = model_path.resolve()

    if not model_path.exists():
        print("Error: Model file not found.\nLooked for:")
        for p in tried_paths if tried_paths else [model_path]:
            print(f"  - {p}")
        print(f"\nMODEL_DIR is set to: {MODEL_DIR}")
        return 1

    print(f"Running: {cmd_name} -m {model_path}")

    try:
        # Build the command string
        cmd_str = f'{cmd_name} -m {str(model_path)}'

        # Use sh to invoke /bin/sh with -c flag
        for line in sh.sh("-c", cmd_str, _iter=True, _err_to_out=True):
            print(line, end='')

        return 0

    except ErrorReturnCode as e:
        print(f"Error running localscore: {e}")
        return e.exit_code
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark GGUF models with localscore",
        epilog="After downloading, copy or symlink this script to a location in your PATH "
               "(e.g., ~/.local/bin/llm-bench) for easier access.",
        add_help=False
    )
    parser.add_argument("-h", "--help", action="store_true", help="show this help message and exit")
    parser.add_argument("model_path", nargs="?", help="Path to the GGUF model file")
    parser.add_argument("--download-localscore", action="store_true",
                        help="Download the localscore binary")
    parser.add_argument("--download-model", action="store_true",
                        help="Download a model from HuggingFace")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force download even if localscore is already in PATH")

    args = parser.parse_args()

    # Handle help flag
    if args.help:
        print(__doc__.strip())
        return 0

    # Handle downloads if requested
    if args.download_localscore:
        download_localscore(force=args.force)

    if args.download_model:
        model_path = download_model_from_hf()
        if model_path is None:
            print("Failed to download model.")
            return 1
        if not args.model_path:
            args.model_path = str(model_path)

    # If no model path provided and no downloads requested, show usage
    if not args.model_path:
        parser.print_help()
        return 0

    # Run localscore with the model
    return run_localscore(args.model_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")
        exit(0)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
