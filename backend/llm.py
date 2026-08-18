"""OpenAI-compatible LLM client (Qwen Cloud Token Plan by default)."""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

DEFAULT_BASE = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "deepseek-v4-flash-0731"


def settings() -> dict[str, str]:
    key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("DASHSCOPE_API_KEY")
        or os.environ.get("QWEN_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or ""
    ).strip()
    base = (os.environ.get("LLM_BASE_URL") or DEFAULT_BASE).rstrip("/")
    model = (os.environ.get("LLM_MODEL") or DEFAULT_MODEL).strip()
    return {"api_key": key, "base_url": base, "model": model}


def configured() -> bool:
    return bool(settings()["api_key"])


def status() -> dict[str, Any]:
    cfg = settings()
    return {
        "llm": bool(cfg["api_key"]),
        "llmModel": cfg["model"] if cfg["api_key"] else None,
        "llmProvider": "qwen-cloud" if cfg["api_key"] else None,
    }


def extract_json(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        raise ValueError("empty LLM content")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in LLM content")
    data = json.loads(m.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM JSON was not an object")
    return data


async def complete_json(system: str, user: str, timeout: float = 45.0) -> dict:
    cfg = settings()
    if not cfg["api_key"]:
        raise RuntimeError("LLM_API_KEY is not set")
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "enable_thinking": False,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
    body = resp.json()
    content = (((body.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    return extract_json(content)
