"""
Kuroshin Ajan Konseyi v1.0 — Smolagents Framework
===================================================
Port 9004 — FastAPI servis
- Teknisyen Ajan: kod yazma, dosya düzenleme, shell komutları
- Gözcü Ajan: web tarama, GitHub/HF hype takibi
Her ikisi de llama-server port 8080 (Gemma4) kullanır — sıfır ekstra VRAM.
"""

import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    LiteLLMModel,
    DuckDuckGoSearchTool,
    tool,
)

# ─────────────────────────────────────────
# SABİTLER
# ─────────────────────────────────────────
SERVICE_PORT   = 9004
LLAMA_BASE_URL = "http://127.0.0.1:8080/v1"
LLAMA_MODEL    = "mlabonne_Qwen3-8B-abliterated-Q5_K_M.gguf"
COUNCIL_LOG    = "/root/kuroshin/logs/council.log"

Path(COUNCIL_LOG).parent.mkdir(parents=True, exist_ok=True)

def _log(msg: str):
    print(msg, flush=True)
    try:
        with open(COUNCIL_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# ─────────────────────────────────────────
# MODEL (llama-server, ekstra VRAM yok)
# ─────────────────────────────────────────
gemma4 = LiteLLMModel(
    model_id=f"openai/{LLAMA_MODEL}",
    api_base=LLAMA_BASE_URL,
    api_key="dummy",
    max_tokens=2048,
)

# ─────────────────────────────────────────
# ARAÇLAR
# ─────────────────────────────────────────
@tool
def read_file(path: str) -> str:
    """WSL dosyasını oku ve içeriğini döndür.

    Args:
        path: Okunacak dosyanın tam yolu (/mnt/c/... formatında)
    """
    try:
        p = Path(path)
        if not p.exists():
            return f"Dosya bulunamadı: {path}"
        return p.read_text(encoding="utf-8", errors="replace")[:8000]
    except Exception as e:
        return f"Okuma hatası: {e}"


@tool
def write_file(path: str, content: str) -> str:
    """WSL dosyasına içerik yaz.

    Args:
        path: Yazılacak dosyanın tam yolu (/mnt/c/... formatında)
        content: Dosyaya yazılacak içerik
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Yazıldı: {path} ({len(content)} karakter)"
    except Exception as e:
        return f"Yazma hatası: {e}"


@tool
def run_shell(command: str) -> str:
    """WSL bash komutu çalıştır ve çıktısını döndür.

    Args:
        command: Çalıştırılacak bash komutu
    """
    import subprocess
    BLOCKED = ["rm ", "rmdir", "mkfs", "dd ", "format", ":(){", "fork bomb"]
    if any(b in command.lower() for b in BLOCKED):
        return "ENGELLENDI: Tehlikeli komut."
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True, text=True, timeout=30
        )
        out = result.stdout[:3000]
        err = result.stderr[:500]
        return out if out else (err if err else "(çıktı yok)")
    except subprocess.TimeoutExpired:
        return "Zaman aşımı (30sn)"
    except Exception as e:
        return f"Komut hatası: {e}"


# ─────────────────────────────────────────
# AJANLAR
# ─────────────────────────────────────────
def make_teknisyen():
    return ToolCallingAgent(
        name="Teknisyen",
        description=(
            "Kuroshin İmparatorluğu'nun Baş Teknisyeni. "
            "Kod yazar, dosya okur/düzenler, shell komutları çalıştırır. "
            "Türkçe yanıt verir, 'Lordum' diye hitap eder."
        ),
        model=gemma4,
        tools=[read_file, write_file, run_shell],
        max_steps=4,
    )

def make_gozcu():
    return ToolCallingAgent(
        name="Gozcu",
        description=(
            "Kuroshin İmparatorluğu'nun Küresel Gözcüsü. "
            "Web'i tarar, GitHub/HuggingFace trendlerini takip eder, "
            "yeni teknolojileri keşfeder. "
            "Türkçe rapor üretir, 'Lordum' diye hitap eder."
        ),
        model=gemma4,
        tools=[DuckDuckGoSearchTool()],
        max_steps=4,
    )

# ─────────────────────────────────────────
# FASTAPI
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    _log(f"\n🔱 KUROSHIN AJAN KONSEYİ v1.0 AKTİF (Port {SERVICE_PORT})")
    _log(f"   Teknisyen: araçlar=read_file,write_file,run_shell")
    _log(f"   Gözcü: araçlar=DuckDuckGoSearch")
    _log(f"   Model: {LLAMA_MODEL} @ {LLAMA_BASE_URL}\n")
    yield


app = FastAPI(lifespan=lifespan)


class CouncilRequest(BaseModel):
    agent: str   # "teknisyen" veya "gozcu"
    task: str


@app.get("/health")
def health():
    return {"status": "ready", "version": "1.0", "agents": ["teknisyen", "gozcu"]}


@app.post("/task")
def run_task(req: CouncilRequest):
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Görev boş olamaz.")

    agent_name = req.agent.lower().strip()
    if agent_name not in ("teknisyen", "gozcu"):
        raise HTTPException(status_code=400, detail="agent: 'teknisyen' veya 'gozcu' olmalı.")

    agent = make_teknisyen() if agent_name == "teknisyen" else make_gozcu()
    _log(f"[KONSEY] [{agent_name.upper()}] Yeni Görev: {req.task}")

    t0 = time.time()
    try:
        result = agent.run(req.task)
        elapsed = round(time.time() - t0, 1)
        _log(f"[KONSEY] [{agent_name.upper()}] Tamamlandı ({elapsed}s)")
        return {"result": str(result), "agent": agent_name, "elapsed": elapsed}
    except Exception as e:
        import traceback
        _log(f"[KONSEY] HATA: {traceback.format_exc()}")
        return {"result": f"[HATA] {e}", "agent": agent_name, "elapsed": round(time.time() - t0, 1)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=SERVICE_PORT, loop="asyncio", log_level="warning", log_config=None)
