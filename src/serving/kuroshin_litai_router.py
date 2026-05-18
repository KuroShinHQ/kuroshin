#!/usr/bin/env python3
"""
🔱 KUROSHIN LLM ROUTER v2.0
============================
LiteLLM → llama-server otomatik fallback, retry + timeout + logging.
Kullanım: from kuroshin_litai_router import kuroshin_chat, kuroshin_chat_async
Model: qwen3-abliterated (DEFAULT_MODEL değiştirilebilir)
"""

import asyncio
import httpx
import json
import time
import sys
from typing import Optional

LITELLM_BASE  = "http://127.0.0.1:6000/v1"
LLAMA_BASE    = "http://127.0.0.1:8080/v1"
API_KEY       = "kuroshin-secret"
DEFAULT_MODEL = "qwen3-abliterated"
MAX_RETRIES   = 3
TIMEOUT       = 120.0


def _build_payload(messages: list, max_tokens: int = 4096, temperature: float = 0.7) -> dict:
    return {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }


def _extract_content(data: dict) -> str:
    try:
        msg = data["choices"][0]["message"]
        return (
            msg.get("reasoning_content", "") or
            msg.get("content", "") or
            ""
        ).strip()
    except (KeyError, IndexError):
        return ""


async def kuroshin_chat_async(
    messages: list,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    prefer_litellm: bool = True,
) -> str:
    """Async chat: LiteLLM önce, başarısız olursa llama-server direkt."""
    endpoints = [
        (LITELLM_BASE, "LiteLLM"),
        (LLAMA_BASE,   "llama-server"),
    ]
    if not prefer_litellm:
        endpoints = list(reversed(endpoints))

    payload = _build_payload(messages, max_tokens, temperature)
    last_err = ""

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for base_url, name in endpoints:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    t0 = time.time()
                    resp = await client.post(
                        f"{base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                        json=payload,
                    )
                    elapsed = round(time.time() - t0, 2)

                    if resp.status_code == 200:
                        content = _extract_content(resp.json())
                        if content:
                            print(f"[LitAI] ✅ {name} #{attempt} → {elapsed}s", file=sys.stderr)
                            return content
                        last_err = f"{name}: boş yanıt"
                    else:
                        last_err = f"{name} HTTP {resp.status_code}: {resp.text[:200]}"

                except (httpx.ConnectError, httpx.TimeoutException) as e:
                    last_err = f"{name} bağlantı hatası: {e}"
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(1.5 * attempt)

    return f"❌ LitAI Router başarısız ({MAX_RETRIES} deneme): {last_err}"


def kuroshin_chat(
    messages: list,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    prefer_litellm: bool = True,
) -> str:
    """Sync wrapper (subprocess/thread ortamı için)."""
    return asyncio.run(kuroshin_chat_async(messages, max_tokens, temperature, prefer_litellm))


if __name__ == "__main__":
    test_messages = [{"role": "user", "content": "Merhaba Kuroshin, kısa bir selamlama yap."}]
    print("🔱 LitAI Router testi başlıyor...")
    result = kuroshin_chat(test_messages, max_tokens=128)
    print(f"\nYanıt:\n{result}")
