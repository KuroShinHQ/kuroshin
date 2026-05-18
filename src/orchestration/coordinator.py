import asyncio
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add src to path for imports
sys.path.append('/mnt/c/Kuroshin/src')

from core import get_llm_client
from memory import get_memory
from agents.deerflow.deerflow_core import DeerFlowCore


class KuroshinCoordinator:
    """
    Kuroshin OS Central Coordinator
    DeerFlow, Claw-Code-Parity ve diğer ajanları koordine eden merkezi sinir sistemi
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.memory = get_memory()
        self.deerflow = DeerFlowCore()
        self.active_tasks = {}
        self.task_history = []
        
    async def orchestrate_web_to_code(
        self,
        url: str,
        code_task_description: str = None
    ) -> Dict[str, Any]:
        """
        Web scraping'den kod yazımına kadar tam pipeline
        """
        
        task_id = f"web2code_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            print(f"🔱 [{task_id}] Web-to-Code Pipeline başlatılıyor...")
            print(f"📡 URL: {url}")
            
            # Phase 1: DeerFlow ile web scraping
            print("📊 Phase 1: Web scraping...")
            web_result = await self.deerflow.process_url(url)
            
            if "Hata:" in web_result:
                return {
                    "success": False,
                    "task_id": task_id,
                    "error": f"Web scraping failed: {web_result}",
                    "phase": "web_scraping"
                }
            
            # Phase 2: İçeriği analiz et ve kod gereksinimleri çıkar
            print("🧠 Phase 2: İçerik analizi...")
            analysis_result = await self.analyze_web_content_for_coding(web_result, code_task_description)
            
            # Phase 3: Hafızadan ilgili kodları ara
            print("🔍 Phase 3: Hafıza araması...")
            memory_search = self.memory.search_memory(
                query=f"{url} {code_task_description or 'coding requirements'}",
                n_results=3
            )
            
            # Phase 4: Code generation planning
            print("⚡ Phase 4: Kod planlama...")
            code_plan = await self.create_code_plan(analysis_result, memory_search)
            
            # Sonuç paketi
            result = {
                "success": True,
                "task_id": task_id,
                "phases": {
                    "web_scraping": {"status": "completed", "data": web_result[:500] + "..."},
                    "content_analysis": {"status": "completed", "data": analysis_result},
                    "memory_search": {"status": "completed", "count": memory_search.get("count", 0)},
                    "code_planning": {"status": "completed", "plan": code_plan}
                },
                "next_actions": self.suggest_next_actions(code_plan),
                "timestamp": datetime.now().isoformat()
            }
            
            # Task history'ye ekle
            self.task_history.append(result)
            
            print(f"✅ [{task_id}] Pipeline tamamlandı!")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "task_id": task_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.task_history.append(error_result)
            return error_result
    
    async def analyze_web_content_for_coding(
        self,
        web_content: str,
        user_task: str = None
    ) -> Dict[str, Any]:
        """Web içeriğini kod yazımı açısından analiz et"""
        
        analysis_prompt = f"""
        Web scraping sonucu elde edilen bu içeriği kod yazımı açısından analiz et:
        
        {web_content[:2000]}
        
        Kullanıcının isteği: {user_task or 'Belirtilmedi'}
        
        Analiz et:
        1. Bu içerikten hangi tür kodlar yazılabilir?
        2. Teknik gereksinimler nelerdir?
        3. Kullanılması gereken teknolojiler/kütüphaneler?
        4. Öncelik sırası nasıl olmalı?
        
        Kısa ve öz yanıtla.
        """
        
        result = self.llm_client.chat_completion(
            message=analysis_prompt,
            temperature=0.3
        )
        
        return result
    
    async def create_code_plan(
        self,
        analysis_result: Dict[str, Any],
        memory_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analiz sonuçlarına göre kod planı oluştur"""
        
        planning_prompt = f"""
        İçerik analizi: {analysis_result.get('content', 'N/A')}
        Hafızadaki ilgili bilgi sayısı: {memory_context.get('count', 0)}
        
        Bu bilgilere dayanarak bir kod yazım planı oluştur:
        1. Hangi dosyalar oluşturulmalı?
        2. Kod mimarisi nasıl olmalı?
        3. Adım adım uygulama sırası?
        4. Test stratejisi?
        
        JSON formatında yanıtla.
        """
        
        result = self.llm_client.chat_completion(
            message=planning_prompt,
            temperature=0.4
        )
        
        return result
    
    def suggest_next_actions(self, code_plan: Dict[str, Any]) -> List[str]:
        """Sonraki adımları öner"""
        
        suggestions = [
            "Claw-Code-Parity ajanını aktive et",
            "Kod dosyalarını oluştur",
            "Test senaryolarını hazırla",
            "Dokümantasyon yaz",
            "Kod review sürecini başlat"
        ]
        
        return suggestions
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Sistem durumunu raporla"""
        
        # LLM durumu
        llm_status = self.llm_client.get_available_models()
        
        # Memory istatistikleri
        memory_stats = self.memory.get_statistics()
        
        # Recent tasks
        recent_tasks = self.task_history[-5:]
        
        return {
            "llm_connection": {"status": "connected" if not llm_status.get("error") else "error"},
            "memory_stats": memory_stats,
            "recent_tasks_count": len(recent_tasks),
            "active_tasks_count": len(self.active_tasks),
            "system_health": "operational"
        }
    
    async def search_memory_interactive(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """İnteraktif hafıza araması"""
        
        search_result = self.memory.search_memory(query, limit)
        
        if search_result.get("success"):
            # Sonuçları LLM ile özetle
            summarize_prompt = f"""
            Hafıza araması: "{query}"
            Sonuç sayısı: {search_result.get('count', 0)}
            
            Bu arama sonuçlarını kullanıcı dostu bir şekilde özetle.
            """
            
            summary = self.llm_client.chat_completion(
                message=summarize_prompt,
                temperature=0.5
            )
            
            return {
                "query": query,
                "results_count": search_result.get('count', 0),
                "summary": summary.get('content', 'Özet oluşturulamadı'),
                "raw_results": search_result
            }
        else:
            return {
                "query": query,
                "error": search_result.get("error"),
                "results_count": 0
            }
    
    async def close(self):
        """Kaynakları temizle"""
        await self.deerflow.close()


# Global coordinator instance
_coordinator_instance = None

def get_coordinator() -> KuroshinCoordinator:
    """Global coordinator instance döndür"""
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = KuroshinCoordinator()
    return _coordinator_instance


async def quick_web_to_code_pipeline(url: str, task_description: str = None) -> Dict[str, Any]:
    """Hızlı web-to-code pipeline başlatıcı"""
    coordinator = get_coordinator()
    result = await coordinator.orchestrate_web_to_code(url, task_description)
    return result