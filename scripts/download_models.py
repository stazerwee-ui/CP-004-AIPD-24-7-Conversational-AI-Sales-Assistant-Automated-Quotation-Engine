"""
Downloads the model weights and support tools that are too large for GitHub.

The Kokoro voice model alone is ~310 MB, well over GitHub's 100 MB per-file
limit, so these are fetched at setup time rather than committed.

Why `requests` rather than `urllib`:
    Some Windows Python installations (notably the Microsoft Store build and
    some python.org installs) ship without a usable CA certificate bundle, so
    urllib fails with CERTIFICATE_VERIFY_FAILED on any https download.
    `requests` bundles certifi's CA store, so it works regardless. It is
    already a project dependency, so this adds nothing new to install.

Why this lives in its own file rather than inside install_dependencies.bat:
    A multi-line `python -c "..."` does not work in a batch script - cmd treats
    every line after the first as a separate command, so the download silently
    never runs while the installer still reports success.

Run directly, or via install_dependencies.bat:
    python scripts/download_models.py
"""

import os
import sys

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-windows-amd64.exe"
)

# (url, destination, minimum plausible size in bytes)
#
# The size is checked as well as the file's existence: a download that stops
# part-way leaves a small file behind that would otherwise look like a success
# and cause a confusing failure much later, at runtime.
DOWNLOADS = [
    (KOKORO_BASE + "kokoro-v1.0.onnx", os.path.join("models", "kokoro-v1.0.onnx"), 300_000_000),
    (KOKORO_BASE + "voices-v1.0.bin", os.path.join("models", "voices-v1.0.bin"), 20_000_000),
    (CLOUDFLARED_URL, os.path.join("tools", "cloudflared.exe"), 30_000_000),
]


def fetch(url, dest, min_size):
    """Download one file, showing progress. Returns None on success, else an error string."""
    if os.path.exists(dest) and os.path.getsize(dest) >= min_size:
        print(f"    {os.path.basename(dest)} already present, skipping.")
        return None

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"    Downloading {os.path.basename(dest)} ...")

    try:
        import requests
    except ImportError:
        return "the 'requests' package is not installed - run: pip install -r requirements.txt"

    try:
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            written = 0
            last_shown = -1

            with open(dest, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    written += len(chunk)

                    # Only redraw when the whole percent changes, otherwise this
                    # prints thousands of lines when the output is piped to a file.
                    if total:
                        percent = written * 100 // total
                        if percent != last_shown:
                            last_shown = percent
                            sys.stdout.write(
                                f"\r      {percent:3d}%  ({written / 1048576:.0f}"
                                f" / {total / 1048576:.0f} MB)"
                            )
                            sys.stdout.flush()
            print()

    except Exception as exc:
        if os.path.exists(dest):
            os.remove(dest)
        return f"{exc}"

    size = os.path.getsize(dest)
    if size < min_size:
        os.remove(dest)  # a truncated file is worse than none at all
        return f"only {size:,} bytes downloaded - the transfer was cut short"

    print(f"    OK  {os.path.basename(dest)}  ({size / 1048576:.0f} MB)")
    return None


def main():
    failures = []

    for url, dest, min_size in DOWNLOADS:
        error = fetch(url, dest, min_size)
        if error:
            failures.append(f"{os.path.basename(dest)}: {error}")

    print()
    if failures:
        print("  DOWNLOAD FAILED:")
        for item in failures:
            print(f"    - {item}")
        print()
        if any("CERTIFICATE_VERIFY_FAILED" in f or "SSLError" in f for f in failures):
            print("  This looks like a certificate problem rather than a network one.")
            print("  Make sure the virtual environment is active and run:")
            print("      pip install --upgrade requests certifi")
            print()
        print("  The app will still run. Spoken replies will fall back to the")
        print("  browser's built-in voice, and the phone demo tunnel will be")
        print("  unavailable, but everything else works normally.")
        return 1

    print("  All models and tools downloaded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
