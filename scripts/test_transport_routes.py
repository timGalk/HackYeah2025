#!/usr/bin/env python3
"""
Transport Routes Testing Script

This script tests the transport routes API endpoints with various scenarios
including basic routing, incident impacts, edge modifications, and different
transport modes.

Usage:
    python test_transport_routes.py [--base-url BASE_URL] [--verbose]
"""

import argparse
import asyncio
import json
import random
import sys
from typing import Dict, List, Optional, Tuple
import aiohttp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TransportRoutesTester:
    """Test suite for transport routes API endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Load node mappings for realistic testing
        self.node_mappings = self._load_node_mappings()
        
        # Test scenarios
        self.test_scenarios = [
            {
                "name": "Basic Route Planning",
                "description": "Test basic route planning between popular stops",
                "test_cases": self._get_basic_routing_cases()
            },
            {
                "name": "Transport Modes",
                "description": "Test different transport modes",
                "test_cases": self._get_transport_mode_cases()
            },
            {
                "name": "Edge Modifications",
                "description": "Test edge weight modifications and nearest edge lookups",
                "test_cases": self._get_edge_modification_cases()
            },
            {
                "name": "Incident Impact",
                "description": "Test route planning with incident impacts",
                "test_cases": self._get_incident_impact_cases()
            }
        ]
    
    def _load_node_mappings(self) -> Dict[str, str]:
        """Load node name mappings from JSON file."""
        try:
            with open('node_name_mapping.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("node_name_mapping.json not found, using fallback mappings")
            return {
                "Dworzec Główny": "stop_744_106082",
                "Rondo Mogilskie": "stop_95_12508",
                "Plac Centralny": "stop_353_274449",
                "Czyżyny": "stop_296_40704",
                "Bronowice": "stop_64_8905",
                "Nowa Huta": "stop_336_46504",
                "Podgórze": "stop_820_315829",
                "Kazimierz": "stop_263_36002",
                "Wawel": "stop_2311_32502",
                "AGH": "stop_1626_311102"
            }
    
    def _get_basic_routing_cases(self) -> List[Dict]:
        """Get basic routing test cases."""
        # Use known working node pairs from the actual graph
        test_cases = [
            {
                "source": "Czyżyny",
                "target": "Bronowice",
                "source_id": self.node_mappings.get("Czyżyny", "stop_296_40704"),
                "target_id": self.node_mappings.get("Bronowice", "stop_64_8905"),
                "modes": ["bus"]
            },
            {
                "source": "Mistrzejowice",
                "target": "Os. Złotego Wieku",
                "source_id": self.node_mappings.get("Mistrzejowice", "stop_271_37505"),
                "target_id": self.node_mappings.get("Os. Złotego Wieku", "stop_272_37704"),
                "modes": ["bus"]
            },
            {
                "source": "Rondo Mogilskie",
                "target": "Hala Targowa",
                "source_id": self.node_mappings.get("Rondo Mogilskie", "stop_95_12508"),
                "target_id": self.node_mappings.get("Hala Targowa", "stop_265_36302"),
                "modes": ["bus"]
            }
        ]
        
        return test_cases
    
    def _get_transport_mode_cases(self) -> List[Dict]:
        """Get transport mode test cases."""
        return [
            {
                "source": "Czyżyny",
                "target": "Bronowice",
                "source_id": self.node_mappings.get("Czyżyny", "stop_296_40704"),
                "target_id": self.node_mappings.get("Bronowice", "stop_64_8905"),
                "modes": ["bus", "walking", "bike"]
            },
            {
                "source": "Mistrzejowice",
                "target": "Os. Złotego Wieku",
                "source_id": self.node_mappings.get("Mistrzejowice", "stop_271_37505"),
                "target_id": self.node_mappings.get("Os. Złotego Wieku", "stop_272_37704"),
                "modes": ["bus"]
            }
        ]
    
    def _get_edge_modification_cases(self) -> List[Dict]:
        """Get edge modification test cases."""
        return [
            {
                "type": "nearest_lookup",
                "latitude": 50.062,
                "longitude": 19.938
            },
            {
                "type": "nearest_update",
                "latitude": 50.062,
                "longitude": 19.938,
                "weight": 220.0
            }
            # Note: Edge update test commented out as it requires actual edge IDs from the graph
            # {
            #     "type": "edge_update",
            #     "mode": "walking",
            #     "source": "stop_a",
            #     "target": "stop_b",
            #     "key": "walk-stop_a-stop_b",
            #     "speed_kmh": 6.0
            # }
        ]
    
    def _get_incident_impact_cases(self) -> List[Dict]:
        """Get incident impact test cases."""
        return [
            {
                "incident": {
                    "latitude": 50.062,
                    "longitude": 19.938,
                    "description": "Test traffic congestion",
                    "category": "Traffic",
                    "username": "test_user",
                    "approved": False,
                    "reporter_social_score": 25.0
                },
                "route_test": {
                    "source": "Czyżyny",
                    "target": "Bronowice",
                    "source_id": self.node_mappings.get("Czyżyny", "stop_296_40704"),
                    "target_id": self.node_mappings.get("Bronowice", "stop_64_8905"),
                    "mode": "bus"
                }
            },
            {
                "incident": {
                    "latitude": 50.068,
                    "longitude": 19.945,
                    "description": "Test crush incident - approved",
                    "category": "Crush",
                    "username": "test_user",
                    "approved": True,
                    "reporter_social_score": 10.0
                },
                "route_test": {
                    "source": "Mistrzejowice",
                    "target": "Os. Złotego Wieku",
                    "source_id": self.node_mappings.get("Mistrzejowice", "stop_271_37505"),
                    "target_id": self.node_mappings.get("Os. Złotego Wieku", "stop_272_37704"),
                    "mode": "bus"
                }
            }
        ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_api_health(self) -> bool:
        """Test if the API is accessible."""
        try:
            async with self.session.get(f"{self.base_url}/api/v1/transport/modes") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"API is healthy. Available modes: {data.get('modes', [])}")
                    return True
                else:
                    logger.error(f"API health check failed with status {response.status}")
                    return False
        except Exception as e:
            logger.error(f"API health check failed: {e}")
            return False
    
    async def test_basic_routing(self, test_case: Dict) -> Dict:
        """Test basic route planning."""
        results = {}
        
        for mode in test_case["modes"]:
            try:
                url = f"{self.base_url}/api/v1/transport/routes"
                params = {
                    "mode": mode,
                    "source": test_case["source_id"],
                    "target": test_case["target_id"]
                }
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results[mode] = {
                            "status": "success",
                            "incident_detected": data.get("incident_detected", False),
                            "has_default_path": "default_path" in data,
                            "has_suggested_path": "suggested_path" in data,
                            "response_time_ms": response.headers.get("X-Response-Time", "unknown")
                        }
                        logger.info(f"✓ {test_case['source']} → {test_case['target']} ({mode}): "
                                  f"Incident detected: {data.get('incident_detected', False)}")
                    else:
                        error_text = await response.text()
                        results[mode] = {
                            "status": "error",
                            "status_code": response.status,
                            "error": error_text
                        }
                        logger.error(f"✗ {test_case['source']} → {test_case['target']} ({mode}): "
                                   f"Status {response.status}")
            except Exception as e:
                results[mode] = {
                    "status": "exception",
                    "error": str(e)
                }
                logger.error(f"✗ {test_case['source']} → {test_case['target']} ({mode}): {e}")
        
        return results
    
    async def test_edge_modifications(self, test_case: Dict) -> Dict:
        """Test edge modifications and nearest edge lookups."""
        result = {"status": "unknown"}
        
        try:
            if test_case["type"] == "nearest_lookup":
                url = f"{self.base_url}/api/v1/transport/graphs/nearest/lookup"
                payload = {
                    "latitude": test_case["latitude"],
                    "longitude": test_case["longitude"]
                }
                
                async with self.session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = {
                            "status": "success",
                            "edge_found": "edge" in data,
                            "edge_mode": data.get("edge", {}).get("mode"),
                            "distance_km": data.get("edge", {}).get("distance_to_point_km")
                        }
                        logger.info(f"✓ Nearest edge lookup: {data.get('edge', {}).get('mode', 'unknown')} "
                                  f"at {data.get('edge', {}).get('distance_to_point_km', 'unknown')} km")
                    else:
                        error_text = await response.text()
                        result = {
                            "status": "error",
                            "status_code": response.status,
                            "error": error_text
                        }
                        logger.error(f"✗ Nearest edge lookup failed: Status {response.status}")
            
            elif test_case["type"] == "nearest_update":
                url = f"{self.base_url}/api/v1/transport/graphs/nearest"
                payload = {
                    "latitude": test_case["latitude"],
                    "longitude": test_case["longitude"],
                    "weight": test_case["weight"]
                }
                
                async with self.session.patch(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = {
                            "status": "success",
                            "edge_updated": "edge" in data,
                            "new_weight": data.get("edge", {}).get("weight")
                        }
                        logger.info(f"✓ Nearest edge update: Weight set to {data.get('edge', {}).get('weight', 'unknown')}")
                    else:
                        error_text = await response.text()
                        result = {
                            "status": "error",
                            "status_code": response.status,
                            "error": error_text
                        }
                        logger.error(f"✗ Nearest edge update failed: Status {response.status}")
            
            elif test_case["type"] == "edge_update":
                url = f"{self.base_url}/api/v1/transport/graphs/{test_case['mode']}/edges/{test_case['source']}/{test_case['target']}"
                payload = {
                    "key": test_case["key"],
                    "speed_kmh": test_case["speed_kmh"]
                }
                
                async with self.session.patch(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = {
                            "status": "success",
                            "edge_updated": "edge" in data,
                            "new_speed": data.get("edge", {}).get("speed_kmh"),
                            "new_weight": data.get("edge", {}).get("weight")
                        }
                        logger.info(f"✓ Edge update: Speed set to {data.get('edge', {}).get('speed_kmh', 'unknown')} km/h")
                    else:
                        error_text = await response.text()
                        result = {
                            "status": "error",
                            "status_code": response.status,
                            "error": error_text
                        }
                        logger.error(f"✗ Edge update failed: Status {response.status}")
        
        except Exception as e:
            result = {
                "status": "exception",
                "error": str(e)
            }
            logger.error(f"✗ Edge modification test failed: {e}")
        
        return result
    
    async def test_incident_impact(self, test_case: Dict) -> Dict:
        """Test incident impact on routing."""
        result = {"status": "unknown"}
        
        try:
            # First, create an incident
            incident_url = f"{self.base_url}/api/v1/incidents"
            async with self.session.post(incident_url, json=test_case["incident"]) as response:
                if response.status == 201:
                    incident_data = await response.json()
                    incident_id = incident_data.get("incident_id")
                    logger.info(f"✓ Created incident: {incident_id}")
                    
                    # Wait a moment for incident to be processed
                    await asyncio.sleep(2)
                    
                    # Test route planning
                    route_test = test_case["route_test"]
                    route_url = f"{self.base_url}/api/v1/transport/routes"
                    params = {
                        "mode": route_test["mode"],
                        "source": route_test["source_id"],
                        "target": route_test["target_id"]
                    }
                    
                    async with self.session.get(route_url, params=params) as response:
                        if response.status == 200:
                            route_data = await response.json()
                            default_path = route_data.get("default_path") or {}
                            suggested_path = route_data.get("suggested_path") or {}
                            result = {
                                "status": "success",
                                "incident_id": incident_id,
                                "incident_detected": route_data.get("incident_detected", False),
                                "has_alternative": "suggested_path" in route_data and route_data["suggested_path"] is not None,
                                "default_path_weight": default_path.get("total_current_weight"),
                                "suggested_path_weight": suggested_path.get("total_current_weight")
                            }
                            logger.info(f"✓ Route test with incident: Detected={route_data.get('incident_detected', False)}, "
                                      f"Alternative={result['has_alternative']}")
                        else:
                            error_text = await response.text()
                            result = {
                                "status": "error",
                                "incident_id": incident_id,
                                "status_code": response.status,
                                "error": error_text
                            }
                            logger.error(f"✗ Route test with incident failed: Status {response.status}")
                else:
                    error_text = await response.text()
                    result = {
                        "status": "error",
                        "status_code": response.status,
                        "error": error_text
                    }
                    logger.error(f"✗ Incident creation failed: Status {response.status}")
        
        except Exception as e:
            result = {
                "status": "exception",
                "error": str(e)
            }
            logger.error(f"✗ Incident impact test failed: {e}")
        
        return result
    
    async def run_test_scenario(self, scenario: Dict) -> Dict:
        """Run a complete test scenario."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {scenario['name']}")
        logger.info(f"Description: {scenario['description']}")
        logger.info(f"{'='*60}")
        
        results = {
            "scenario": scenario["name"],
            "description": scenario["description"],
            "test_results": []
        }
        
        for i, test_case in enumerate(scenario["test_cases"], 1):
            logger.info(f"\nTest Case {i}/{len(scenario['test_cases'])}")
            
            if scenario["name"] == "Basic Route Planning":
                test_result = await self.test_basic_routing(test_case)
            elif scenario["name"] == "Transport Modes":
                test_result = await self.test_basic_routing(test_case)
            elif scenario["name"] == "Edge Modifications":
                test_result = await self.test_edge_modifications(test_case)
            elif scenario["name"] == "Incident Impact":
                test_result = await self.test_incident_impact(test_case)
            else:
                test_result = {"status": "skipped", "reason": "Unknown scenario"}
            
            results["test_results"].append({
                "test_case": test_case,
                "result": test_result
            })
        
        return results
    
    async def run_all_tests(self) -> Dict:
        """Run all test scenarios."""
        logger.info("Starting Transport Routes API Test Suite")
        logger.info(f"Base URL: {self.base_url}")
        
        # Check API health first
        if not await self.test_api_health():
            logger.error("API health check failed. Exiting.")
            return {"status": "failed", "reason": "API not accessible"}
        
        all_results = {
            "base_url": self.base_url,
            "scenarios": []
        }
        
        for scenario in self.test_scenarios:
            try:
                scenario_result = await self.run_test_scenario(scenario)
                all_results["scenarios"].append(scenario_result)
            except Exception as e:
                logger.error(f"Scenario '{scenario['name']}' failed: {e}")
                all_results["scenarios"].append({
                    "scenario": scenario["name"],
                    "status": "failed",
                    "error": str(e)
                })
        
        return all_results
    
    def print_summary(self, results: Dict):
        """Print test results summary."""
        logger.info(f"\n{'='*60}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*60}")
        
        total_scenarios = len(results.get("scenarios", []))
        successful_scenarios = 0
        
        for scenario_result in results.get("scenarios", []):
            scenario_name = scenario_result.get("scenario", "Unknown")
            test_results = scenario_result.get("test_results", [])
            
            successful_tests = 0
            total_tests = len(test_results)
            
            for test_result in test_results:
                result = test_result.get("result", {})
                # For routing tests, check if any mode succeeded
                if isinstance(result, dict):
                    if result.get("status") == "success":
                        successful_tests += 1
                    else:
                        # Check if it's a multi-mode result (for routing tests)
                        mode_results = [v for k, v in result.items() 
                                      if isinstance(v, dict) and "status" in v]
                        if mode_results and any(m.get("status") == "success" for m in mode_results):
                            successful_tests += 1
            
            success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            logger.info(f"{scenario_name}: {successful_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
            
            if success_rate == 100:
                successful_scenarios += 1
        
        overall_success_rate = (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0
        logger.info(f"\nOverall: {successful_scenarios}/{total_scenarios} scenarios passed ({overall_success_rate:.1f}%)")
        
        if overall_success_rate == 100:
            logger.info("🎉 All tests passed!")
        elif overall_success_rate >= 80:
            logger.info("✅ Most tests passed!")
        else:
            logger.info("❌ Many tests failed. Check the logs above for details.")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Transport Routes API")
    parser.add_argument("--base-url", default="http://localhost:8000",
                       help="Base URL of the API (default: http://localhost:8000)")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    async with TransportRoutesTester(args.base_url) as tester:
        results = await tester.run_all_tests()
        
        tester.print_summary(results)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Test results saved to {args.output}")
        
        # Exit with appropriate code
        if results.get("status") == "failed":
            sys.exit(1)
        
        # Check if all scenarios passed
        scenarios = results.get("scenarios", [])
        failed_scenarios = [s for s in scenarios if s.get("status") == "failed"]
        if failed_scenarios:
            sys.exit(1)
        
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
