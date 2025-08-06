#!/usr/bin/env python3
"""
Performance Testing Script for ChatterboxTTS Optimization
Tests both old (subprocess) and new (persistent service) approaches
"""

import time
import requests
import subprocess
import asyncio
import httpx

# Configuration
CHATTERBOX_SERVICE_URL = "http://localhost:8001"
TEST_TEXT = "Hello, this is a test of the Indian accent voice synthesis system."

def test_old_method():
    """Test the old subprocess method"""
    print("🔄 Testing OLD method (subprocess)...")
    
    start_time = time.time()
    
    try:
        command = f"""conda run -n chatter_box python /var/www/html/zsapiens/hindi_english/pronunciation_analysis/chatterbox/testing_chatter.py "{TEST_TEXT}" """
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        
        duration = time.time() - start_time
        print(f"✅ OLD method completed in {duration:.2f} seconds")
        return duration
        
    except subprocess.CalledProcessError as e:
        print(f"❌ OLD method failed: {e}")
        return None

async def test_new_method():
    """Test the new persistent service method"""
    print("🚀 Testing NEW method (persistent service)...")
    
    start_time = time.time()
    
    try:
        # Check service health first
        async with httpx.AsyncClient(timeout=5.0) as client:
            health_response = await client.get(f"{CHATTERBOX_SERVICE_URL}/health")
            if health_response.status_code != 200:
                print(f"❌ Service not healthy: {health_response.status_code}")
                return None
            
            health_data = health_response.json()
            if not health_data.get("model_loaded", False):
                print("❌ Model not loaded in service")
                return None
        
        # Generate speech
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CHATTERBOX_SERVICE_URL}/generate",
                json={
                    "text": TEST_TEXT,
                    "output_path": "/tmp/test_output.wav"
                }
            )
            
            if response.status_code != 200:
                print(f"❌ Generation failed: {response.status_code}")
                return None
            
            result = response.json()
        
        duration = time.time() - start_time
        generation_time = result.get("generation_time", 0)
        
        print(f"✅ NEW method completed in {duration:.2f} seconds")
        print(f"   - Pure generation time: {generation_time:.2f} seconds")
        print(f"   - Network + overhead: {duration - generation_time:.2f} seconds")
        
        return duration
        
    except Exception as e:
        print(f"❌ NEW method failed: {e}")
        return None

def performance_comparison():
    """Run performance comparison between methods"""
    print("🎯 ChatterboxTTS Performance Comparison")
    print("=" * 50)
    
    # Test old method
    old_duration = test_old_method()
    
    print("\n" + "-" * 30 + "\n")
    
    # Test new method
    new_duration = asyncio.run(test_new_method())
    
    print("\n" + "=" * 50)
    print("📊 RESULTS:")
    
    if old_duration and new_duration:
        improvement = ((old_duration - new_duration) / old_duration) * 100
        speedup = old_duration / new_duration
        
        print(f"   📅 OLD method: {old_duration:.2f} seconds")
        print(f"   🚀 NEW method: {new_duration:.2f} seconds")
        print(f"   ⚡ Improvement: {improvement:.1f}% faster")
        print(f"   🔥 Speedup: {speedup:.1f}x faster")
        
        if improvement > 80:
            print("   🎉 EXCELLENT performance improvement!")
        elif improvement > 50:
            print("   ✅ Good performance improvement!")
        else:
            print("   ⚠️  Moderate improvement, consider further optimization")
    
    elif new_duration:
        print(f"   🚀 NEW method: {new_duration:.2f} seconds")
        print("   📅 OLD method: Failed to run")
        print("   ✅ NEW method is working!")
    
    elif old_duration:
        print(f"   📅 OLD method: {old_duration:.2f} seconds")
        print("   🚀 NEW method: Failed to run")
        print("   ⚠️  Service may not be running. Check setup.")
    
    else:
        print("   ❌ Both methods failed. Check configuration.")

if __name__ == "__main__":
    performance_comparison()