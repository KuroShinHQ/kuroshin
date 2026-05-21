import asyncio
import json
import hashlib
import time
import socket
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import httpx
import chromadb

LLAMA_URL  = "http://127.0.0.1:8080/v1/chat/completions"
WALKER_URL = "http://127.0.0.1:9002"
CHROMA_DIR = "/root/kuroshin/memory/chroma"
TIMEOUT_LLM = 90
TIMEOUT_WEB = 300

_SERVICES = {
    8080: "llama-server",
    9002: "Walker",
    8100: "ChromaDB",
    3005: "Bridge",
    9004: "Konsey",
}


def _load_model() -> str:
    state = Path("/mnt/c/Kuroshin/memory/active_model.json")
    try:
        if state.exists():
            return json.loads(state.read_text(encoding="utf-8")).get("active_model", "")
    except Exception:
        pass
    return "Huihui-Qwen3.6-35B-A3B"


LLAMA_MODEL = _load_model()


class KuroshinCoordinator:
    """Kuroshin OS Merkezi Koordinatör — DeerFlow MCP v2.0 entegreli."""

    def __init__(self):
        self.active_tasks: Dict[str, Any] = {}
        self.task_history: List[Dict[str, Any]] = []
        self._chroma_client: Optional[chromadb.PersistentClient] = None

    def _get_chroma(self) -> chromadb.PersistentClient:
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        return self._chroma_client

    async def _llm(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024) -> str:
        payload = {
            "model": LLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(LLAMA_URL, json=payload, timeout=TIMEOUT_LLM)
                if r.status_code == 200:
                    return (r.json()["choices"][0]["message"].get("content") or "").strip()
            except Exception:
                pass
        return ""

    async def _walker_research(self, task: str) -> str:
        """Walker ajanına araştırma görevi gönder (port 9002)."""
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    f"{WALKER_URL}/task",
                    json={"task": task},
                    timeout=TIMEOUT_WEB,
                )
                if r.status_code == 200:
                    return r.json().get("result", "")
                return f"Walker HTTP {r.status_code}"
            except httpx.ConnectError:
                return "Walker servisi kapalı (port 9002)"
            except httpx.TimeoutException:
                return f"Walker zaman aşımı ({TIMEOUT_WEB}s)"
            except Exception as e:
                return f"Walker hatası: {e}"

    def _memory_search(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        try:
            col = self._get_chroma().get_or_create_collection("kuroshin_memory")
            count = col.count()
            if count == 0:
                return {"success": True, "count": 0, "documents": []}
            results = col.query(query_texts=[query], n_results=min(n_results, count))
            docs = results.get("documents", [[]])[0]
            return {"success": True, "count": len(docs), "documents": docs}
        except Exception as e:
            return {"success": False, "error": str(e), "count": 0}

    def _memory_save(self, key: str, content: str, source: str = "coordinator"):
        try:
            col = self._get_chroma().get_or_create_collection("kuroshin_memory")
            doc_id = "coord_" + hashlib.md5(key.encode()).hexdigest()[:12]
            col.upsert(
                ids=[doc_id],
                documents=[f"[Coordinator] {key}\n\n{content}"],
                metadatas=[{"source": source, "ts": str(int(time.time()))}],
            )
        except Exception:
            pass

    async def orchestrate_web_to_code(
        self,
        url: str,
        code_task_description: str = None,
    ) -> Dict[str, Any]:
        """Web URL'sinden kod planına tam pipeline: Walker → LLM analiz → ChromaDB → plan."""
        task_id = f"web2code_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            print(f"[{task_id}] Web-to-Code Pipeline başlatılıyor: {url}")

            # Phase 1: Walker ile web araştırması
            walker_task = f"Şu URL'yi oku ve içeriğini özetle: {url}"
            if code_task_description:
                walker_task += f"\nÖzellikle şuna odaklan: {code_task_description}"
            web_result = await self._walker_research(walker_task)
            if not web_result or "kapalı" in web_result or "hatası" in web_result:
                return {
                    "success": False,
                    "task_id": task_id,
                    "error": f"Web araştırması başarısız: {web_result}",
                    "phase": "web_scraping",
                }

            # Phase 2: Kod analizi
            analysis = await self.analyze_web_content_for_coding(web_result, code_task_description)

            # Phase 3: Hafıza araması
            mem = self._memory_search(f"{url} {code_task_description or 'coding'}")

            # Phase 4: Kod planı
            plan = await self.create_code_plan(analysis, mem)

            result = {
                "success": True,
                "task_id": task_id,
                "phases": {
                    "web_scraping":     {"status": "completed", "data": web_result[:500] + "..."},
                    "content_analysis": {"status": "completed", "data": analysis},
                    "memory_search":    {"status": "completed", "count": mem.get("count", 0)},
                    "code_planning":    {"status": "completed", "plan": plan},
                },
                "next_actions": self.suggest_next_actions(plan),
                "timestamp": datetime.now().isoformat(),
            }
            self.task_history.append(result)
            self._memory_save(f"web2code:{url}", f"{analysis}\n\n{plan}")
            print(f"[{task_id}] Pipeline tamamlandı.")
            return result

        except Exception as e:
            err = {"success": False, "task_id": task_id, "error": str(e),
                   "timestamp": datetime.now().isoformat()}
            self.task_history.append(err)
            return err

    async def analyze_web_content_for_coding(
        self, web_content: str, user_task: str = None
    ) -> str:
        prompt = (
            f"Web içeriğini kod yazımı açısından analiz et:\n\n{web_content[:2000]}\n\n"
            f"Kullanıcı isteği: {user_task or 'Belirtilmedi'}\n\n"
            "Şunları kısaca yanıtla:\n"
            "1. Hangi tür kodlar yazılabilir?\n"
            "2. Teknik gereksinimler nelerdir?\n"
            "3. Öncelik sırası?"
        )
        return await self._llm(prompt, temperature=0.3)

    async def create_code_plan(
        self, analysis_result: str, memory_context: Dict[str, Any]
    ) -> str:
        mem_count = memory_context.get("count", 0)
        mem_docs = "\n".join(
            d[:200] for d in memory_context.get("documents", [])
        )
        prompt = (
            f"İçerik analizi:\n{analysis_result}\n\n"
            f"Hafızadan {mem_count} ilgili kayıt:\n{mem_docs}\n\n"
            "Bir kod yazım planı oluştur. JSON formatında:\n"
            "- files: oluşturulacak dosyalar listesi\n"
            "- architecture: mimari kısa açıklama\n"
            "- steps: adım sırası listesi"
        )
        return await self._llm(prompt, temperature=0.4)

    def suggest_next_actions(self, code_plan: str) -> List[str]:
        return [
            "Walker Agent ile detaylı araştırma yap",
            "Kod dosyalarını oluştur",
            "Test senaryolarını hazırla",
            "ChromaDB'ye kaydet",
        ]

    async def get_system_status(self) -> Dict[str, Any]:
        services = {}
        for port, name in _SERVICES.items():
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    services[name] = "up"
            except Exception:
                services[name] = "down"
        try:
            col = self._get_chroma().get_or_create_collection("kuroshin_memory")
            mem_count = col.count()
        except Exception:
            mem_count = -1
        return {
            "services": services,
            "memory_records": mem_count,
            "active_tasks": len(self.active_tasks),
            "task_history": len(self.task_history),
            "model": LLAMA_MODEL,
        }

    async def search_memory_interactive(self, query: str, limit: int = 5) -> Dict[str, Any]:
        result = self._memory_search(query, limit)
        if result.get("success") and result.get("count", 0) > 0:
            docs_text = "\n".join(d[:200] for d in result.get("documents", []))
            summary = await self._llm(
                f'Hafıza araması: "{query}"\n\nSonuçlar:\n{docs_text}\n\nKısa özetle.',
                temperature=0.5,
            )
            return {
                "query": query,
                "results_count": result.get("count", 0),
                "summary": summary,
                "documents": result.get("documents", []),
            }
        return {"query": query, "error": result.get("error"), "results_count": 0}

    async def close(self):
        pass


_coordinator_instance: Optional[KuroshinCoordinator] = None


def get_coordinator() -> KuroshinCoordinator:
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = KuroshinCoordinator()
    return _coordinator_instance


async def quick_web_to_code_pipeline(url: str, task_description: str = None) -> Dict[str, Any]:
    return await get_coordinator().orchestrate_web_to_code(url, task_description)
