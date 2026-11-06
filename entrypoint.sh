#!/usr/bin/env bash
# =============================================================================
# GameScaling-9B-S3 inference server entrypoint.
#   * serves the baked weights from ${MODEL_DIR}
#   * OpenAI-compatible endpoint, model name: "gamescaling"
#   * --host 0.0.0.0 is REQUIRED inside a container (official serve_vllm.sh
#     omits it, which makes "-p 8000:8000" unreachable).
# =============================================================================
set -euo pipefail

MODEL_DIR="${MODEL_DIR:-/models/GameScaling-9B-S3}"
PORT="${PORT:-8000}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.85}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"

if [ ! -f "${MODEL_DIR}/model.safetensors" ]; then
  echo "[entrypoint] FATAL: ${MODEL_DIR}/model.safetensors not found" >&2
  exit 1
fi

args=(
  serve "${MODEL_DIR}"
  --served-model-name gamescaling
  --host 0.0.0.0
  --port "${PORT}"
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}"
  --dtype bfloat16
  --max-model-len "${MAX_MODEL_LEN}"
  --limit-mm-per-prompt '{"image": 8}'
  --gpu-memory-utilization "${GPU_MEM_UTIL}"
  --trust-remote-code
)

if [ -n "${VLLM_API_KEY:-}" ]; then
  args+=(--api-key "${VLLM_API_KEY}")
fi

echo "[entrypoint] serving ${MODEL_DIR} on 0.0.0.0:${PORT} (model=gamescaling)"
exec vllm "${args[@]}"
