#!/usr/bin/env python3
"""Test the full LLM flow with realistic prompts."""
import asyncio
import sys
sys.path.insert(0, '/app')

from llm import call_ollama
from prompt import build_system_messages
from response_parser import parse_llm_response
from models import Preference
from datetime import date

async def test_full_flow():
    # Create mock preferences
    class MockPref:
        def __init__(self):
            self.budget = "medium"
            self.interests = ["beaches", "culture", "food"]
            self.date_from = date(2026, 6, 1)
            self.date_to = date(2026, 6, 15)
    
    prefs = [MockPref(), MockPref()]
    
    # Build system message
    system_msg = build_system_messages(prefs)
    print("=" * 60)
    print("SYSTEM MESSAGE:")
    print("=" * 60)
    print(system_msg)
    print()
    
    # Build messages
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": "Suggest exactly 3 travel destinations."}
    ]
    
    print("=" * 60)
    print("CALLING OLLAMA...")
    print("=" * 60)
    
    try:
        # Call LLM
        raw_response = await call_ollama(messages)
        print(f"Raw response length: {len(raw_response)} characters")
        print(f"Raw response: {raw_response[:500]}")
        print()
        
        # Parse response
        print("=" * 60)
        print("PARSING RESPONSE...")
        print("=" * 60)
        destinations, success = parse_llm_response(raw_response)
        
        if success:
            print(f"✅ SUCCESS! Got {len(destinations)} destinations:")
            for i, dest in enumerate(destinations, 1):
                print(f"\n{i}. {dest.name}")
                print(f"   {dest.rationale}")
        else:
            print("❌ FAILED to parse response")
            
        return success
        
    except Exception as e:
        print(f"❌ EXCEPTION: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_full_flow())
    print(f"\n{'='*60}")
    print(f"Test {'PASSED ✅' if result else 'FAILED ❌'}")
    print(f"{'='*60}")
