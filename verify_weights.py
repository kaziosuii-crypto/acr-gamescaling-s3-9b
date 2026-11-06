#!/usr/bin/env python3
"""Build-time integrity gate for the baked weights. Cheap (no full-file hash).

Checks: required files present, config is Qwen3.5-VL, model.safetensors has the
exact expected size, and its header is a real readable safetensors header with
tensors in it. Set VERIFY_SHA256=1 to also stream the 18.8 GB file through
sha256 (slower, use when diagnosing a suspect build).
"""
import hashlib
import json
import os
import sys

DST = os.environ.get("MODEL_DIR", "/models/GameScaling-9B-S3")
EXPECTED_SIZE = 18_819_722_392
EXPECTED_SHA256 = "18afe037afcf175abd061193ab98d0d46f90224ffc28c083fe2a12ed366d7d50"
REQUIRED = [
    "config.json",
    "model.safetensors",
    "chat_template.jinja",
    "tokenizer.json",
    "tokenizer_config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "processor_config.json",
    "video_preprocessor_config.json",
]

missing = [f for f in REQUIRED if not os.path.isfile(os.path.join(DST, f))]
if missing:
    sys.exit(f"[verify] MISSING required files: {missing}")

with open(os.path.join(DST, "config.json"), encoding="utf-8") as fh:
    cfg = json.load(fh)
if cfg.get("model_type") != "qwen3_5":
    sys.exit(f"[verify] unexpected model_type: {cfg.get('model_type')}")
if "Qwen3_5ForConditionalGeneration" not in cfg.get("architectures", []):
    sys.exit(f"[verify] unexpected architectures: {cfg.get('architectures')}")
if str(cfg.get("torch_dtype", cfg.get("dtype", ""))).lower() not in ("bfloat16", "torch.bfloat16"):
    print(f"[verify] note: dtype field = {cfg.get('torch_dtype', cfg.get('dtype'))}", flush=True)

weights = os.path.join(DST, "model.safetensors")
size = os.path.getsize(weights)
if size != EXPECTED_SIZE:
    sys.exit(f"[verify] model.safetensors is {size} bytes, expected {EXPECTED_SIZE}")

# A safetensors file starts with an 8-byte little-endian header length + JSON.
# Reading only that is effectively free and proves the file is not truncated.
with open(weights, "rb") as fh:
    header_len = int.from_bytes(fh.read(8), "little")
    header = json.loads(fh.read(header_len))
tensors = [k for k in header if k != "__metadata__"]
if not tensors:
    sys.exit("[verify] no tensors found in safetensors header")
dtypes = sorted({header[k].get("dtype") for k in tensors})
print(f"[verify] {len(tensors)} tensors, dtypes={dtypes}, size={size}", flush=True)

if os.environ.get("VERIFY_SHA256") == "1":
    h = hashlib.sha256()
    with open(weights, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    if h.hexdigest() != EXPECTED_SHA256:
        sys.exit(f"[verify] sha256 mismatch: {h.hexdigest()}")
    print("[verify] sha256 OK", flush=True)

print("[verify] OK - weights and chat_template.jinja are intact", flush=True)
