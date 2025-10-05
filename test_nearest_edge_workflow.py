#!/usr/bin/env python3
"""
Test script demonstrating the nearest edge workflow:
1. Load nearest edge using /api/v1/transport/graphs/nearest/lookup
2. Modify it with /api/v1/transport/graphs/nearest
3. Read nearest edge again to verify changes

This script follows the project's Python 3.11 + FastAPI + PEP 8 standards.

Usage:
    uv run python test_nearest_edge_workflow.py

Requirements:
    - The API server must be running on http://localhost:8000
    - httpx dependency (included in project dependencies)
"""

import asyncio
import json
from typing import Any, Dict

import httpx


class NearestEdgeWorkflow:
    """Demonstrates the nearest edge lookup and modification workflow."""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        """Initialize the workflow client."""
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self) -> "NearestEdgeWorkflow":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.client.aclose()

    async def lookup_nearest_edge(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Load the nearest transit edge using the lookup endpoint.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Edge details from the lookup response
            
        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        url = f"{self.base_url}/api/v1/transport/graphs/nearest/lookup"
        payload = {
            "latitude": latitude,
            "longitude": longitude,
        }
        
        print(f"🔍 Looking up nearest edge at ({latitude}, {longitude})...")
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        edge = data["edge"]
        
        print(f"✅ Found nearest edge:")
        print(f"   Mode: {edge['mode']}")
        print(f"   Source: {edge['source']} -> Target: {edge['target']}")
        print(f"   Key: {edge['key']}")
        print(f"   Weight: {edge['weight']} seconds")
        if "distance_to_point_km" in edge:
            print(f"   Distance to point: {edge['distance_to_point_km']:.4f} km")
        
        return edge

    async def modify_nearest_edge(
        self, 
        latitude: float, 
        longitude: float, 
        new_weight: float
    ) -> Dict[str, Any]:
        """
        Modify the nearest transit edge with a new weight.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            new_weight: New weight in seconds
            
        Returns:
            Updated edge details
            
        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
        url = f"{self.base_url}/api/v1/transport/graphs/nearest"
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "weight": new_weight,
        }
        
        print(f"🔧 Modifying nearest edge with weight {new_weight} seconds...")
        response = await self.client.patch(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        edge = data["edge"]
        
        print(f"✅ Edge updated successfully:")
        print(f"   Mode: {edge['mode']}")
        print(f"   Source: {edge['source']} -> Target: {edge['target']}")
        print(f"   Key: {edge['key']}")
        print(f"   New weight: {edge['weight']} seconds")
        if "distance_to_point_km" in edge:
            print(f"   Distance to point: {edge['distance_to_point_km']:.4f} km")
        
        return edge

    async def run_workflow(
        self, 
        latitude: float, 
        longitude: float, 
        new_weight: float
    ) -> None:
        """
        Run the complete nearest edge workflow.
        
        Args:
            latitude: Latitude coordinate for the test point
            longitude: Longitude coordinate for the test point
            new_weight: New weight to apply to the nearest edge
        """
        print("=" * 60)
        print("🚀 Starting Nearest Edge Workflow Test")
        print("=" * 60)
        
        try:
            # Step 1: Lookup the nearest edge
            print("\n📋 Step 1: Lookup nearest edge")
            print("-" * 40)
            original_edge = await self.lookup_nearest_edge(latitude, longitude)
            original_weight = original_edge["weight"]
            
            # Step 2: Modify the nearest edge
            print(f"\n📋 Step 2: Modify nearest edge (weight: {original_weight} -> {new_weight})")
            print("-" * 40)
            modified_edge = await self.modify_nearest_edge(latitude, longitude, new_weight)
            
            # Step 3: Verify the change by looking up again
            print(f"\n📋 Step 3: Verify changes by looking up again")
            print("-" * 40)
            verified_edge = await self.lookup_nearest_edge(latitude, longitude)
            
            # Summary
            print(f"\n📊 Workflow Summary")
            print("=" * 60)
            print(f"Original weight:  {original_weight} seconds")
            print(f"Modified weight:  {modified_edge['weight']} seconds")
            print(f"Verified weight:   {verified_edge['weight']} seconds")
            
            # Verify the change was applied
            if abs(verified_edge['weight'] - new_weight) < 0.01:
                print("✅ SUCCESS: Weight change was applied and verified!")
            else:
                print("❌ FAILURE: Weight change was not applied correctly!")
                
            # Check if it's the same edge
            if (original_edge['mode'] == verified_edge['mode'] and 
                original_edge['source'] == verified_edge['source'] and 
                original_edge['target'] == verified_edge['target'] and 
                original_edge['key'] == verified_edge['key']):
                print("✅ SUCCESS: Same edge was modified!")
            else:
                print("⚠️  WARNING: Different edge was found - this might be expected if the graph changed")
                
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise


async def main() -> None:
    """Main function to run the nearest edge workflow test."""
    # Test coordinates (Krakow area)
    test_latitude = 50.062
    test_longitude = 19.938
    new_weight = 600.0  # 10 minutes (different from current 450.0)
    
    async with NearestEdgeWorkflow() as workflow:
        await workflow.run_workflow(test_latitude, test_longitude, new_weight)


if __name__ == "__main__":
    asyncio.run(main())
