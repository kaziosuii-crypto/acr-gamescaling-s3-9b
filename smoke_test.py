#!/usr/bin/env python3
"""In-image self test for the GameScaling-9B-S3 server.

Checks that the OpenAI-compatible endpoint is up and that the served model is
named "gamescaling". Run it inside the running container:

    docker exec -it <container> python3 /opt/GameScaling/smoke_test.py

Env:
    PORT      port of the server inside the container (default 8000)
    VLLM_API_KEY  optional bearer token
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PORT = os.environ.get("PORT", "8000")
BASE = f"http://127.0.0.1:{PORT}"
API_KEY = os.environ.get("VLLM_API_KEY", "")
TIMEOUT = float(os.environ.get("SMOKE_TIMEOUT", "120"))


def _get(path: str) -> dict:
    req = urllib.request.Request(BASE + path)
    if API_KEY:
        req.add_header("Authorization", f"Bearer {API_KEY}")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_models() -> str:
    data = _get("/v1/models")
    ids = [m.get("id") for m in data.get("data", [])]
    if "gamescaling" not in ids:
        print(f"FAIL: served model ids = {ids}, expected 'gamescaling'", file=sys.stderr)
        raise SystemExit(1)
    print(f"OK: /v1/models -> {ids}")
    return "gamescaling"


def check_chat() -> None:
    """Minimal protocol-conform completion: prefill + temperature 1.0 +
    skip_special_tokens=False, then look for the action tag."""
    body = {
        "model": "gamescaling",
        "messages": [
            {"role": "user", "content": "current game screen"},
            {"role": "assistant", "content": "<think>\n\n</think>\n\n"},
        ],
        "temperature": 1.0,
        "max_tokens": 64,
        "skip_special_tokens": False,
        "continue_final_message": True,
        "add_generation_prompt": False,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if API_KEY:
        req.add_header("Authorization", f"Bearer {API_KEY}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            out = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - diagnostic path
        print(f"FAIL: chat completion HTTP {exc.code}", file=sys.stderr)
        raise SystemExit(1)

    text = out["choices"][0]["message"].get("content", "")
    print(f"OK: chat completion -> {text[:200]!r}")
    if "<|action_start|>" not in text:
        print("WARN: no <|action_start|> in output (an image is required for a "
              "real action; text-only request is expected to be noisy)", file=sys.stderr)


def main() -> int:
    check_models()
    check_chat()
    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
