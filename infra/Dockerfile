# MemLedger GPU image (slide 16): Python 3.11, vLLM (OpenAI-compatible server for the 8-12B main model),
# transformers (MiniCheck / DeBERTa-v3 / Prompt Guard 2) and sentence-transformers (BGE-M3).
# Build:  docker build -f infra/Dockerfile -t memledger:gpu .
# Run:    docker run --gpus all -p 8000:8000 -v $HOME/.cache/huggingface:/root/.cache/huggingface \
#           -e HF_TOKEN memledger:gpu            (starts vLLM; override CMD to run eval/)
# No weights or datasets are baked in: they are pulled at run time into the mounted cache.
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common git curl \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends python3.11 python3.11-venv python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python3.11 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Heavy, slow-changing layer first so code edits do not reinstall vLLM.
RUN pip install --upgrade pip && pip install "vllm>=0.6" "transformers>=4.44" sentence-transformers

WORKDIR /workspace/MemLedger
COPY pyproject.toml README.md ./
COPY memledger ./memledger
RUN pip install -e ".[dev,store]"
COPY . .

ENV MODEL=Qwen/Qwen3-8B \
    PORT=8000 \
    MAX_MODEL_LEN=16384
EXPOSE 8000
CMD ["sh", "-c", "vllm serve \"$MODEL\" --host 0.0.0.0 --port \"$PORT\" --max-model-len \"$MAX_MODEL_LEN\" --served-model-name main"]
