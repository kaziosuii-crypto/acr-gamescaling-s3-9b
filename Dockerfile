# syntax=docker/dockerfile:1
# =============================================================================
# GameScaling-9B-S3 inference server image (server-side only)
#   weights (18.8 GB BF16) + vLLM 0.17.0 OpenAI-compatible server
#   Target: linux/amd64. Built on the ACR *overseas* builder so huggingface.co
#   is reachable. Nothing is downloaded at run time.
#
#   This image is the SERVER. The official `gamescaling` client package is
#   intentionally NOT baked in: it belongs to the caller side.
# =============================================================================
FROM vllm/vllm-openai:v0.17.0@sha256:14ea8b431aaaf75eb873c46c8ebfbad2b4b0790d30c66126d789d8cb9bd0aab9

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/tmp/hf-cache \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    MODEL_ID=THUSI-Lab/GameScaling-9B-S3 \
    MODEL_REVISION=673fcdc5b442467bbf73102f38defb2ba93d5c9b \
    MODEL_DIR=/models/GameScaling-9B-S3 \
    GS_ROOT=/opt/GameScaling \
    PORT=8000

WORKDIR ${GS_ROOT}

# ---- Layer 1: small deps. Fast, cached, never invalidates the weights layer.
RUN python3 -m pip install --no-cache-dir \
        "hf_transfer>=0.1.9" "requests>=2.31" \
 && apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---- Layer 2: server assets (entrypoint + weight fetcher + self test).
COPY download_weights.py verify_weights.py smoke_test.py  ${GS_ROOT}/
COPY requirements-runtime.txt    ${GS_ROOT}/requirements.txt
COPY entrypoint.sh               /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
 && python3 -m pip install --no-cache-dir -r ${GS_ROOT}/requirements.txt \
 && python3 -c "import requests; print('requests', requests.__version__)"

# ---- Layer 3 (LAST, heaviest): bake the weights into the image.
# Keeping this last means editing layers 1-2 never re-downloads 18.8 GB.
# HF_HOME points at /tmp so hf_transfer's staging files are removed in the
# same layer -> the image does NOT contain a second 18.8 GB copy.
RUN set -eux; \
    mkdir -p "${MODEL_DIR}"; \
    python3 ${GS_ROOT}/download_weights.py; \
    python3 ${GS_ROOT}/verify_weights.py; \
    rm -rf "${HF_HOME}"; \
    du -sh "${MODEL_DIR}"; \
    ls -lh "${MODEL_DIR}"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=900s --retries=30 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/v1/models" >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
