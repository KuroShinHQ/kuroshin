#!/usr/bin/env python3
"""
Kuroshin LitServe Proxy v2.0
LitServe 0.2.17 MCPServer bug'ı yüzünden saf FastAPI proxy kullanıyoruz.
llama-server (8080) → bu proxy (6001) → OpenAI uyumlu endpoint
"""
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import json

LLAMA_BASE = "http://127.0.0.1:8080"

app = FastAPI(title="KuroshinLitServe", version="2.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "kuroshin-litserve", "port": 6001}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    stream = body.get("stream", False)

    async with httpx.AsyncClient(timeout=120.0) as client:
        if stream:
            async def stream_response():
                async with client.stream(
                    "POST",
                    f"{LLAMA_BASE}/v1/chat/completions",
                    json=body,
                    headers={"Authorization": "Bearer kuroshin-secret"},
                ) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk

            return StreamingResponse(stream_response(), media_type="text/event-stream")
        else:
            resp = await client.post(
                f"{LLAMA_BASE}/v1/chat/completions",
                json=body,
                headers={"Authorization": "Bearer kuroshin-secret"},
            )
            return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/v1/models")
async def list_models():
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{LLAMA_BASE}/v1/models")
        return JSONResponse(content=resp.json())


if __name__ == "__main__":
    print("KuroshinLitServe (FastAPI proxy) baslatiliyor → port 6001")
    uvicorn.run(app, host="0.0.0.0", port=6001, log_level="warning")
