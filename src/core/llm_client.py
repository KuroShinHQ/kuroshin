import requests
import json
from typing import Dict, Any, Optional


class KuroshinLLMClient:
    """
    Kuroshin OS Central LLM Client
    Merkezi yerel LLM (LiteLLM) bağlantı sağlayıcısı
    """
    
    def __init__(
        self, 
        base_url: str = "http://127.0.0.1:6000/v1",
        api_key: str = "kuroshin-secret",
        default_model: str = "qwen3-abliterated"
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.default_model = default_model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_available_models(self) -> Dict[str, Any]:
        """Mevcut modelleri listele"""
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Status: {response.status_code}, Detail: {response.text}"}
        except Exception as e:
            return {"error": f"Connection failed: {str(e)}"}
    
    def chat_completion(
        self,
        message: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Chat completion API çağrısı"""
        
        model = model or self.default_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "content": result['choices'][0]['message']['content'],
                    "usage": result.get('usage', {}),
                    "model": model
                }
            else:
                return {
                    "success": False,
                    "error": f"Status: {response.status_code}",
                    "detail": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
    
    def summarize_text(
        self,
        text: str,
        language: str = "Turkish",
        bullet_points: int = 5
    ) -> Dict[str, Any]:
        """Özel özetleme metodu"""
        
        system_prompt = f"""Sen bir uzman özetleyici asistansın. 
        Verilen metni {language} dilinde {bullet_points} madde halinde özetle.
        Her madde kısa ve öz olsun."""
        
        message = f"Bu metni özetle:\n\n{text[:4000]}"
        
        return self.chat_completion(
            message=message,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )


# Global instance - singleton pattern
_client_instance = None

def get_llm_client() -> KuroshinLLMClient:
    """Global LLM client instance döndür"""
    global _client_instance
    if _client_instance is None:
        _client_instance = KuroshinLLMClient()
    return _client_instance


def reset_client(base_url: str = None, api_key: str = None, model: str = None):
    """Client ayarlarını sıfırla"""
    global _client_instance
    _client_instance = KuroshinLLMClient(
        base_url=base_url or "http://127.0.0.1:6000/v1",
        api_key=api_key or "kuroshin-secret", 
        default_model=model or "qwen3-abliterated"
    )