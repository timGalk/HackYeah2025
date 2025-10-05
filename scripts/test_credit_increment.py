#!/usr/bin/env python3
"""Test script to verify credit increment on incident approval."""

import asyncio
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

API_BASE_URL = "http://localhost:8000"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


async def test_credit_increment_workflow():
    """Test that approving an incident increments user credits by 5."""
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Create a test user in Supabase if not exists
        test_username = f"test_user_{datetime.now().timestamp()}"
        test_email = f"{test_username}@example.com"
        
        print(f"Creating test user: {test_username}")
        try:
            supabase.table("users").insert({
                "id": f"test-{datetime.now().timestamp()}",
                "email": test_email,
                "name": test_username,
                "role": "user",
                "credits": 10
            }).execute()
        except Exception as e:
            print(f"User creation: {e}")
        
        # Step 2: Get initial credits
        users_response = supabase.table("users").select("*").eq("name", test_username).execute()
        if not users_response.data:
            print("ERROR: User not found after creation")
            return
        
        initial_credits = users_response.data[0].get("credits", 0)
        print(f"Initial credits: {initial_credits}")
        
        # Step 3: Create an incident with this username
        incident_payload = {
            "latitude": 50.0641,
            "longitude": 19.9450,
            "description": "Test incident for credit verification",
            "category": "Traffic",
            "username": test_username,
            "approved": False,
            "reporter_social_score": 15.0
        }
        
        print("\nCreating incident...")
        create_response = await client.post(
            f"{API_BASE_URL}/api/v1/incidents",
            json=incident_payload
        )
        
        if create_response.status_code != 201:
            print(f"ERROR: Failed to create incident: {create_response.status_code}")
            print(create_response.text)
            return
        
        incident_id = create_response.json()["incident_id"]
        print(f"Created incident: {incident_id}")
        
        # Step 4: Approve the incident via the admin panel
        print("\nApproving incident...")
        approve_response = await client.post(
            f"{API_BASE_URL}/admin/incidents/{incident_id}/approve",
            follow_redirects=False
        )
        
        if approve_response.status_code not in [303, 200]:
            print(f"ERROR: Failed to approve incident: {approve_response.status_code}")
            print(approve_response.text)
            return
        
        print("Incident approved successfully")
        
        # Step 5: Check if credits were incremented by 5
        await asyncio.sleep(1)  # Give it a moment to process
        users_response = supabase.table("users").select("*").eq("name", test_username).execute()
        
        if not users_response.data:
            print("ERROR: User not found after approval")
            return
        
        final_credits = users_response.data[0].get("credits", 0)
        print(f"\nFinal credits: {final_credits}")
        print(f"Credits increment: {final_credits - initial_credits}")
        
        if final_credits == initial_credits + 5:
            print("\n✅ SUCCESS: Credits incremented by 5 as expected!")
        else:
            print(f"\n❌ FAILED: Expected {initial_credits + 5}, got {final_credits}")
        
        # Cleanup
        print("\nCleaning up test data...")
        try:
            user_id = users_response.data[0].get("id")
            supabase.table("users").delete().eq("id", user_id).execute()
            print("Test user deleted")
        except Exception as e:
            print(f"Cleanup error: {e}")


if __name__ == "__main__":
    asyncio.run(test_credit_increment_workflow())

