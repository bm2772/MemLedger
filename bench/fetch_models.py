"""Download the checker models into the Hugging Face cache (slides 11-13, 16). Weights never go into git.

    python -m bench.fetch_models            # all default models; the gated Prompt Guard 2 only if HF_TOKEN is set
    python -m bench.fetch_models --check    # report what is cached, download nothing

Already-cached files are skipped, and models that cannot be fetched (offline, gated) are reported and skipped,
so `make setup-models` never fails on a laptop without Wi-Fi.
"""

from __future__ import annotations

import argparse
import os
import sys

# PyTorch weights + tokenizer/config only: skips the ONNX/OpenVINO copies (nli-deberta is 5.9 GB with them)
TORCH = ["*.json", "*.txt", "*.model", "*.safetensors", "pytorch_model.bin"]
# (model id, allow_patterns, gated)
MODELS: list[tuple[str, list[str] | None, bool]] = [
    ("lytang/MiniCheck-RoBERTa-Large", TORCH, False),  # hallucination check; weights are pytorch_model.bin
    ("cross-encoder/nli-deberta-v3-base", TORCH, False),  # contradiction check
    ("protectai/deberta-v3-base-prompt-injection-v2", TORCH, False),  # input screen layer 3
    ("BAAI/bge-m3", [*TORCH, "1_Pooling/*"], False),  # embeddings (sentence-transformers)
    ("meta-llama/Llama-Prompt-Guard-2-86M", TORCH, True),  # gated: accept the licence on huggingface.co first
]


def fetch(model_id: str, patterns: list[str] | None, check_only: bool = False) -> str:
    from huggingface_hub import snapshot_download

    path = snapshot_download(model_id, allow_patterns=patterns, local_files_only=check_only)
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(path) for f in fs)
    return f"{size / 1e9:.2f} GB at {path}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="only report what is already cached")
    a = ap.parse_args(argv)
    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        print("huggingface_hub missing: pip install -e '.[models]'", file=sys.stderr)
        return 1
    missing = 0
    for model_id, patterns, gated in MODELS:
        if gated and not os.environ.get("HF_TOKEN"):
            print(f"{model_id}: skipped (gated; accept the licence and export HF_TOKEN)")
            continue
        try:
            print(f"{model_id}: {fetch(model_id, patterns, a.check)}")
        except Exception as e:  # noqa: BLE001  offline/gated/not cached (hub error types vary by version)
            missing += 1
            print(f"{model_id}: skipped ({type(e).__name__}: {str(e).splitlines()[0][:120]})")
    return 0 if not a.check or not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
