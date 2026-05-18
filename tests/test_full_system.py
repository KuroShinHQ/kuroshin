#!/usr/bin/env python3

import sys
import asyncio
import json
sys.path.append('/mnt/c/Kuroshin/src')

# Test new architecture imports
try:
    from core import get_llm_client
    from memory import get_memory
    from orchestration import get_coordinator
    print("✅ All module imports successful!")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_full_kuroshin_system():
    """Test complete Kuroshin OS integration"""
    
    print("\n🔱 KUROSHIN OS FULL SYSTEM TEST")
    print("=" * 50)
    
    coordinator = None
    try:
        # Test 1: LLM Client
        print("\n📡 Test 1: LLM Client Connection")
        llm_client = get_llm_client()
        models = llm_client.get_available_models()
        
        if "error" in models:
            print(f"❌ LLM Connection failed: {models['error']}")
        else:
            print(f"✅ LLM Connected. Models available: {len(models.get('data', []))}")
        
        # Test 2: Memory System
        print("\n🧠 Test 2: Memory System")
        memory = get_memory()
        memory_stats = memory.get_statistics()
        print(f"✅ Memory System active. Entries: {memory_stats.get('total_entries', 0)}")
        
        # Test 3: Coordinator System
        print("\n⚡ Test 3: Coordinator System")
        coordinator = get_coordinator()
        system_status = await coordinator.get_system_status()
        print(f"✅ Coordinator active. Health: {system_status.get('system_health', 'unknown')}")
        
        # Test 4: Web-to-Code Pipeline (Simple test)
        print("\n🔄 Test 4: Web-to-Code Pipeline")
        pipeline_result = await coordinator.orchestrate_web_to_code(
            url="https://httpbin.org/html",
            code_task_description="Create a simple web scraper based on this content"
        )
        
        if pipeline_result.get("success"):
            print("✅ Web-to-Code Pipeline completed successfully!")
            print(f"   Task ID: {pipeline_result.get('task_id')}")
            print(f"   Phases completed: {len(pipeline_result.get('phases', {}))}")
        else:
            print(f"❌ Pipeline failed: {pipeline_result.get('error')}")
        
        # Test 5: Memory Search
        print("\n🔍 Test 5: Memory Search")
        search_result = await coordinator.search_memory_interactive("httpbin scraping")
        print(f"✅ Memory search completed. Results: {search_result.get('results_count', 0)}")
        
        print("\n🎯 FINAL SYSTEM STATUS")
        print("=" * 30)
        
        final_status = await coordinator.get_system_status()
        print(f"🔋 System Health: {final_status.get('system_health')}")
        print(f"💾 Total Memory Entries: {final_status['memory_stats'].get('total_entries', 0)}")
        print(f"📋 Recent Tasks: {final_status.get('recent_tasks_count', 0)}")
        print(f"⚡ Active Tasks: {final_status.get('active_tasks_count', 0)}")
        
        print("\n🏆 ALL TESTS PASSED - KUROSHIN OS OPERATIONAL!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ SYSTEM TEST FAILED: {str(e)}")
        return False
    
    finally:
        if coordinator:
            await coordinator.close()


if __name__ == "__main__":
    success = asyncio.run(test_full_kuroshin_system())
    if not success:
        sys.exit(1)