#!/usr/bin/env python3
"""Bake THUSI-Lab/GameScaling-9B-S3 into the image at BUILD time (pinned revision).

Runs on the ACR overseas builder, which can reach huggingface.co. At run time
the container never needs network access. Files land directly in MODEL_DIR
(local_dir), so there is no second copy in the HF cache.
"""
import os

from huggingface_hub import snapshot_download

REPO = os.environ.get("MODEL_ID", "THUSI-Lab/GameScaling-9B-S3")
REV = os.environ.get("MODEL_REVISION", "673fcdc5b442467bbf73102f38defb2ba93d5c9b")
DST = os.environ.get("MODEL_DIR", "/models/GameScaling-9B-S3")
WORKERS = int(os.environ.get("HF_MAX_WORKERS", "8"))

print(f"[weights] {REPO}@{REV} -> {DST} (workers={WORKERS})", flush=True)
path = snapshot_download(
    repo_id=REPO,
    repo_type="model",
    revision=REV,
    local_dir=DST,
    max_workers=WORKERS,
    # Documentation/licence text is not needed at inference time, but
    # chat_template.jinja, all configs, the tokenizer and the weights ARE.
    ignore_patterns=["*.md", "LICENSE", ".gitattributes"],
)
print(f"[weights] snapshot complete: {path}", flush=True)
