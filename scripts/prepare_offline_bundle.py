"""
prepare_offline_bundle.py — Download and verify offline model bundle for Solace Dignity Care.

Usage:
    python prepare_offline_bundle.py --download
    python prepare_offline_bundle.py --verify
    python prepare_offline_bundle.py --help

The --verify flag monkeypatches socket.socket to raise an error if any network connection
is attempted, ensuring fastembed loads completely offline from local cache/vendored weights.
"""

import sys
import os
import argparse

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"


def download_model_bundle(target_dir: str, model_name: str = DEFAULT_MODEL_NAME) -> bool:
    """Downloads fastembed ONNX model weights into target_dir."""
    print(f"[bundle] Downloading model '{model_name}' into '{target_dir}'...")
    os.makedirs(target_dir, exist_ok=True)
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name=model_name, cache_dir=target_dir)
        test_out = list(model.embed(["probe offline download"]))
        if test_out and len(test_out[0]) > 0:
            print(f"[bundle] Successfully downloaded and cached '{model_name}' (dim {len(test_out[0])}) in '{target_dir}'.")
            return True
        else:
            print("[bundle] Model download returned empty embedding.")
            return False
    except Exception as e:
        print(f"[bundle] Download failed with error: {e}")
        return False


def verify_offline_operation(target_dir: str, model_name: str = DEFAULT_MODEL_NAME) -> bool:
    """
    Verifies that the embedding model operates completely offline without network access.
    Monkeypatches socket.socket to block all network calls.
    """
    print(f"[verify] Testing offline initialization for '{model_name}'...")
    
    import socket
    orig_socket = socket.socket

    class BlockedSocket:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("[OFFLINE_VIOLATION] Attempted network socket creation in offline mode!")

    socket.socket = BlockedSocket

    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name=model_name, cache_dir=target_dir if os.path.exists(target_dir) else None)
        
        test_sentences = [
            "what is your cancellation policy",
            "what is the difference between standard and deluxe tier",
            "i am not sure what to choose"
        ]
        embeddings = list(model.embed(test_sentences))
        
        if len(embeddings) != len(test_sentences):
            print(f"[verify] FAILED: expected {len(test_sentences)} embeddings, got {len(embeddings)}")
            return False

        dim = len(embeddings[0])
        if dim != 384:
            print(f"[verify] FAILED: expected 384 dimensions, got {dim}")
            return False

        print(f"[verify] PASSED: Successfully loaded model and generated 384-dim embeddings with network blocked.")
        return True
    except Exception as e:
        print(f"[verify] FAILED with error: {e}")
        return False
    finally:
        socket.socket = orig_socket


def main():
    parser = argparse.ArgumentParser(description="Prepare and verify offline model bundle for Solace Dignity Care.")
    parser.add_argument("--download", action="store_true", help="Download ONNX model weights to local models/ directory.")
    parser.add_argument("--verify", action="store_true", help="Verify model loads and runs with network strictly blocked.")
    parser.add_argument("--target-dir", default=None, help="Target directory for model weights (default: models/).")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="Model name (default: BAAI/bge-small-en-v1.5).")

    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = args.target_dir or os.path.join(base_dir, "models")

    if not args.download and not args.verify:
        parser.print_help()
        sys.exit(0)

    success = True
    if args.download:
        success = download_model_bundle(target_dir, args.model)
        if not success:
            sys.exit(1)

    if args.verify:
        success = verify_offline_operation(target_dir, args.model)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
