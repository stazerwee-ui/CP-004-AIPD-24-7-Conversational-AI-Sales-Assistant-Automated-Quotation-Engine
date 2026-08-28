"""
Downloads the Kokoro-82M voice model weights.

These files are ~338 MB combined, well over GitHub's 100 MB per-file limit, so
they are fetched at setup time rather than committed to the repository.

This lives in its own file rather than inside install_dependencies.bat because a
multi-line `python -c "..."` does not work in a batch script: cmd treats every
line after the first as a separate command, so the download silently never runs
while the script still reports success.

Run directly, or via install_dependencies.bat:
    python scripts/download_models.py
"""

import os
import sys
import urllib.request

BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"

# Minimum plausible size for each file. A partial download that stops early
# leaves a small file behind that would otherwise look like a success, so the
# size is checked rather than just the file's existence.
FILES = [
    ("kokoro-v1.0.onnx", 300_000_000),
    ("voices-v1.0.bin", 20_000_000),
]

MODELS_DIR = "models"


def show_progress(block_num, block_size, total_size):
    if total_size > 0:
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 // total_size)
        mb = downloaded / 1048576
        total_mb = total_size / 1048576
        sys.stdout.write(f"\r    {percent:3d}%  ({mb:.0f} / {total_mb:.0f} MB)")
        sys.stdout.flush()


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    failures = []

    for name, min_size in FILES:
        dest = os.path.join(MODELS_DIR, name)

        if os.path.exists(dest) and os.path.getsize(dest) >= min_size:
            print(f"    {name} already present, skipping.")
            continue

        print(f"    Downloading {name} ...")
        try:
            urllib.request.urlretrieve(BASE_URL + name, dest, show_progress)
            print()
            size = os.path.getsize(dest)
            if size < min_size:
                failures.append(
                    f"{name} is only {size:,} bytes - the download was cut short"
                )
                os.remove(dest)  # a truncated file is worse than none
            else:
                print(f"    OK  {name}  ({size / 1048576:.0f} MB)")
        except Exception as exc:
            failures.append(f"{name} failed: {exc}")
            if os.path.exists(dest):
                os.remove(dest)

    print()
    if failures:
        print("  DOWNLOAD FAILED:")
        for f in failures:
            print(f"    - {f}")
        print()
        print("  The app will still run, but spoken replies will fall back to")
        print("  the browser's built-in voice instead of Kokoro.")
        return 1

    print("  Kokoro voice models ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
