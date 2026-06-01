#!/usr/bin/env python3
"""Tek-seferlik gerçek-mod (test_mode=false) inject — _get_chroma_context (Hybrid RAG) canlı tetikle."""
import json, pathlib
pathlib.Path("/tmp/kuroshin_test_inject.json").write_text(
    json.dumps({
        "chat_id": YOUR_TELEGRAM_CHAT_ID_HERE,
        "text": "Hafizanda github push ve commit konusunda ne kayitli, kisaca ozetle",
        "test_mode": False,
    }, ensure_ascii=False),
    encoding="utf-8",
)
print("INJECTED (test_mode=false, memory query)")
