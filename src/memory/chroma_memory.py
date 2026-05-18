import os
import time
import hashlib
from typing import Dict, List, Any, Optional
import chromadb
from chromadb.config import Settings


class KuroshinMemory:
    """
    Kuroshin OS Memory System - ChromaDB Integration
    Web scraping sonuçlarını kalıcı hafızada saklar
    """
    
    def __init__(self, persist_directory: str = "/mnt/c/Kuroshin/data/chroma_db"):
        self.persist_directory = persist_directory
        
        # ChromaDB persist klasörünü oluştur
        os.makedirs(persist_directory, exist_ok=True)
        
        # ChromaDB client'ı başlat
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Web scraping collection'ı oluştur/al
        try:
            self.web_collection = self.client.get_collection("kuroshin_web_data")
        except:
            self.web_collection = self.client.create_collection(
                name="kuroshin_web_data",
                metadata={"description": "Web scraping sonuçları ve metadata"}
            )
    
    def save_web_content(
        self,
        url: str,
        content: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Web içeriğini hafızaya kaydet"""
        
        # Unique ID oluştur (URL hash)
        content_id = hashlib.md5(url.encode()).hexdigest()
        
        # Metadata hazırla
        doc_metadata = {
            "url": url,
            "timestamp": time.time(),
            "content_type": "web_scraping",
            "summary_length": len(summary),
            "content_length": len(content),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Ek metadata varsa ekle
        if metadata:
            doc_metadata.update(metadata)
        
        # ChromaDB'ye kaydet
        try:
            # Önce var mı kontrol et
            existing = self.web_collection.get(ids=[content_id])
            
            if existing['ids']:
                # Güncelle
                self.web_collection.update(
                    ids=[content_id],
                    documents=[f"URL: {url}\n\nSUMMARY:\n{summary}\n\nCONTENT:\n{content}"],
                    metadatas=[doc_metadata]
                )
                action = "updated"
            else:
                # Yeni kayıt ekle
                self.web_collection.add(
                    ids=[content_id],
                    documents=[f"URL: {url}\n\nSUMMARY:\n{summary}\n\nCONTENT:\n{content}"],
                    metadatas=[doc_metadata]
                )
                action = "added"
                
            return f"Memory {action}: {content_id}"
            
        except Exception as e:
            return f"Memory error: {str(e)}"
    
    def search_memory(
        self,
        query: str,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """Hafızada arama yap"""
        
        try:
            results = self.web_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            return {
                "success": True,
                "results": results,
                "count": len(results['ids'][0]) if results['ids'] else 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_recent_entries(self, limit: int = 10) -> List[Dict]:
        """Son kayıtları getir"""
        
        try:
            # Tüm kayıtları al (ChromaDB'de tarih sıralaması için)
            all_data = self.web_collection.get(include=["metadatas"])
            
            if not all_data['metadatas']:
                return []
            
            # Timestamp'e göre sırala
            entries_with_timestamps = [
                (meta, idx) for idx, meta in enumerate(all_data['metadatas'])
                if 'timestamp' in meta
            ]
            
            # Son kayıtları al
            entries_with_timestamps.sort(key=lambda x: x[0]['timestamp'], reverse=True)
            recent_entries = entries_with_timestamps[:limit]
            
            return [entry[0] for entry in recent_entries]
            
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Hafıza istatistikleri"""
        
        try:
            all_data = self.web_collection.get(include=["metadatas"])
            
            total_entries = len(all_data['metadatas']) if all_data['metadatas'] else 0
            
            if total_entries == 0:
                return {
                    "total_entries": 0,
                    "total_content_size": 0,
                    "average_content_size": 0,
                    "oldest_entry": None,
                    "newest_entry": None
                }
            
            # İstatistikler hesapla
            content_sizes = [meta.get('content_length', 0) for meta in all_data['metadatas']]
            timestamps = [meta.get('timestamp', 0) for meta in all_data['metadatas']]
            
            return {
                "total_entries": total_entries,
                "total_content_size": sum(content_sizes),
                "average_content_size": sum(content_sizes) // len(content_sizes),
                "oldest_entry": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(min(timestamps))),
                "newest_entry": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(max(timestamps)))
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def clear_memory(self) -> str:
        """Tüm hafızayı temizle (Dikkatli kullan!)"""
        try:
            self.client.delete_collection("kuroshin_web_data")
            self.web_collection = self.client.create_collection(
                name="kuroshin_web_data",
                metadata={"description": "Web scraping sonuçları ve metadata"}
            )
            return "Memory cleared successfully"
        except Exception as e:
            return f"Clear memory error: {str(e)}"


# Global instance
_memory_instance = None

def get_memory() -> KuroshinMemory:
    """Global memory instance döndür"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = KuroshinMemory()
    return _memory_instance