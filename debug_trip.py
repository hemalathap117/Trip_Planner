#!/usr/bin/env python3
"""
Debug script to test trip creation and data retrieval
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_trip_flow():
    """Test the complete trip creation and data flow"""
    
    async with httpx.AsyncClient() as client:
        print("🔍 Testing trip creation and data flow...")
        
        # Step 1: Create a trip
        print("\n1. Creating a trip...")
        create_payload = {
            "trip_name": "Test Trip",
            "organizer_name": "Test User"
        }
        
        try:
            response = await client.post(f"{BASE_URL}/create-trip", json=create_payload)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                trip_data = response.json()
                join_code = trip_data["join_code"]
                print(f"   ✅ Trip created with join code: {join_code}")
                
                # Step 2: Test trip-data endpoint
                print(f"\n2. Testing /trip-data/{join_code}...")
                data_response = await client.get(f"{BASE_URL}/trip-data/{join_code}")
                print(f"   Status: {data_response.status_code}")
                
                if data_response.status_code == 200:
                    data = data_response.json()
                    print(f"   ✅ Trip data retrieved successfully")
                    print(f"   Trip name: {data.get('name')}")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Preferences: {len(data.get('preferences', []))}")
                    print(f"   Recommendations: {len(data.get('recommendations', []))}")
                    print(f"   Votes: {len(data.get('votes', []))}")
                else:
                    print(f"   ❌ Failed to get trip data: {data_response.text}")
                
                # Step 3: Test dashboard endpoint
                print(f"\n3. Testing /dashboard/{join_code}...")
                dashboard_response = await client.get(f"{BASE_URL}/dashboard/{join_code}")
                print(f"   Status: {dashboard_response.status_code}")
                
                if dashboard_response.status_code == 200:
                    print(f"   ✅ Dashboard loads successfully")
                    # Check if it contains trip.js
                    if "trip.js" in dashboard_response.text:
                        print(f"   ✅ trip.js is included")
                    else:
                        print(f"   ⚠️  trip.js not found in response")
                else:
                    print(f"   ❌ Dashboard failed: {dashboard_response.text}")
                    
            else:
                print(f"   ❌ Failed to create trip: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_trip_flow())