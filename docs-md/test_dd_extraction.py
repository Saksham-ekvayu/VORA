#!/usr/bin/env python3
"""Test script for deployment document extraction API."""

import httpx
import asyncio
import json

# Configuration
API_BASE_URL = "http://localhost:8007"

async def test_deployment_document_extraction():
    """Test the deployment document extraction endpoint."""
    
    print("=" * 80)
    print("DEPLOYMENT DOCUMENT EXTRACTION API TEST")
    print("=" * 80)
    
    # Example deployment document ID (replace with actual ID)
    dd_id = "test_dd_001"  # Replace with actual deployment document ID
    
    endpoint = f"{API_BASE_URL}/deployment-document/{dd_id}/ai-extract"
    
    print(f"\nEndpoint: POST {endpoint}")
    print(f"Deployment Document ID: {dd_id}")
    print(f"\nNote: Only dd_id needed - file is already in the deployment document!")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint)
            
            print(f"Status Code: {response.status_code}")
            print(f"\nResponse:")
            print(json.dumps(response.json(), indent=2))
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                extraction_id = data.get("extraction_id")
                file_hash = data.get("file_hash")
                
                if extraction_id:
                    print(f"\n✅ Extraction started successfully!")
                    print(f"Extraction ID: {extraction_id}")
                    print(f"File Hash: {file_hash}")
                    
                    if file_hash:
                        print(f"\nTo check extraction status, call:")
                        print(f"GET {API_BASE_URL}/document-extraction/{file_hash}")
                else:
                    print(f"\n⚠️ Response successful but no extraction_id returned")
            else:
                print(f"\n❌ Request failed with status {response.status_code}")
                
    except httpx.ConnectError:
        print(f"❌ Connection error - make sure the service is running at {API_BASE_URL}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_deployment_document_extraction())
