#!/usr/bin/env python3
"""
Kuroshin Skill Memory v1.0
Iron Inquisitor test sonuçlarını ChromaDB'ye kaydeder.
PASS pattern'leri → eğitimde bağlam olarak kullanılır.
FAIL pattern'leri → sistem prompt düzeltmelerine yol gösterir.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

CHROMA_DIR        = "/root/kuroshin/memory/chroma"
COLLECTION_NAME   = "kuroshin_skill_memory"
MAX_SKILLS_RETURN = 5


class KuroshinSkillMemory:
    def __init__(self):
        self._client     = None
        self._collection = None

    def _connect(self):
        if self._collection:
            return True
        if not CHROMA_AVAILABLE:
            return False
        try:
            self._client = chromadb.PersistentClient(path=CHROMA_DIR)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Kuroshin Iron Inquisitor skill patterns"}
            )
            return True
        except Exception as e:
            return False

    def save_skill(self, test_id: str, tool: str, prompt: str,
                   output: str, score: float, status: str):
        """PASS veya FAIL sonucunu kaydet."""
        if not self._connect():
            return
        try:
            doc_id = f"{test_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            document = (
                f"Tool: {tool}\n"
                f"Status: {status}\n"
                f"Prompt: {prompt[:300]}\n"
                f"Output: {output[:300]}"
            )
            metadata = {
                "test_id":  test_id,
                "tool":     tool,
                "status":   status,
                "score":    score,
                "ts":       datetime.now().isoformat(),
            }
            self._collection.add(
                ids=[doc_id],
                documents=[document],
                metadatas=[metadata],
            )
        except Exception as e:
            print(f"[SKILL_MEM] save_skill hatası: {e}")

    def get_relevant_skills(self, tool_name: str, n: int = MAX_SKILLS_RETURN) -> list[dict]:
        """Belirli bir araç için geçmiş PASS pattern'lerini getir."""
        if not self._connect():
            return []
        try:
            results = self._collection.query(
                query_texts=[f"Tool: {tool_name} Status: PASS"],
                n_results=n,
                where={"status": {"$eq": "PASS"}},
            )
            skills = []
            for i, doc in enumerate(results.get("documents", [[]])[0]):
                meta = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
                skills.append({"document": doc, "metadata": meta})
            return skills
        except Exception as e:
            print(f"[SKILL_MEM] get_relevant_skills hatası: {e}")
            return []

    def get_failure_lessons(self, tool_name: str = "", n: int = 10) -> list[dict]:
        """FAIL pattern'lerini listele — sistem prompt düzeltmelerine girdi sağlar."""
        if not self._connect():
            return []
        try:
            query = f"Tool: {tool_name} Status: FAIL" if tool_name else "Status: FAIL"
            if tool_name:
                where = {"$and": [{"status": {"$eq": "FAIL"}}, {"tool": {"$eq": tool_name}}]}
            else:
                where = {"status": {"$eq": "FAIL"}}
            results = self._collection.query(
                query_texts=[query],
                n_results=n,
                where=where,
            )
            lessons = []
            for i, doc in enumerate(results.get("documents", [[]])[0]):
                meta = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
                lessons.append({"document": doc, "metadata": meta})
            return lessons
        except Exception as e:
            print(f"[SKILL_MEM] get_failure_lessons hatası: {e}")
            return []

    def get_skill_summary(self) -> dict:
        """Collection istatistiklerini döndür."""
        if not self._connect():
            return {}
        try:
            count = self._collection.count()
            return {"total_skills": count, "collection": COLLECTION_NAME}
        except Exception as e:
            return {"error": str(e)}

    def build_context_for_prompt(self, tools: list[str]) -> str:
        """Verilen araçlar için geçmiş başarı örneklerini prompt'a eklenebilir metin olarak döndür."""
        if not self._connect():
            return ""
        lines = ["## Geçmiş Başarılı Araç Kullanımları (Skill Memory)\n"]
        for tool in tools:
            skills = self.get_relevant_skills(tool, n=2)
            if skills:
                lines.append(f"### {tool}")
                for s in skills:
                    doc = s["document"]
                    lines.append(f"- {doc[:200]}")
        return "\n".join(lines) if len(lines) > 1 else ""


# Singleton
_skill_memory_instance = None

def get_skill_memory() -> KuroshinSkillMemory:
    global _skill_memory_instance
    if _skill_memory_instance is None:
        _skill_memory_instance = KuroshinSkillMemory()
    return _skill_memory_instance


# Standalone test
if __name__ == "__main__":
    print("[SKILL_MEM] Test başlıyor...")
    sm = get_skill_memory()

    # Test kaydı
    sm.save_skill(
        test_id="echo-01-test",
        tool="kuroshin-echo",
        prompt="echo aracıyla 'SKILL_TEST' yaz",
        output="SKILL_TEST",
        score=1.0,
        status="PASS",
    )
    sm.save_skill(
        test_id="search-fail-test",
        tool="kuroshin-search",
        prompt="web_search ile Python ara",
        output="Araç çağrılmadı, direkt cevap verildi",
        score=0.0,
        status="FAIL",
    )

    summary = sm.get_skill_summary()
    print(f"[SKILL_MEM] Collection: {summary}")

    skills = sm.get_relevant_skills("kuroshin-echo")
    print(f"[SKILL_MEM] Echo PASS skills: {len(skills)} kayıt")

    lessons = sm.get_failure_lessons("kuroshin-search")
    print(f"[SKILL_MEM] Search FAIL lessons: {len(lessons)} kayıt")

    ctx = sm.build_context_for_prompt(["kuroshin-echo", "kuroshin-search"])
    print(f"[SKILL_MEM] Context için {len(ctx)} karakter üretildi")
    print("[SKILL_MEM] Test tamamlandı ✅")
