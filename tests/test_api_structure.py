import pytest
"""
Quick test to see what Fantasy Nerds API returns
"""

import asyncio
import httpx

@pytest.mark.asyncio
async def test_api():
    api_key = "TEST"
    base_url = "https://api.fantasynerds.com/v1/nba"
    
    print("Testing injuries endpoint...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{base_url}/injuries",
            params={"apikey": api_key}
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Type: {type(data)}")
        print(f"Content:\n{data}")
        print()
        
    print("Testing news endpoint...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{base_url}/news",
            params={"apikey": api_key}
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Type: {type(data)}")
        print(f"Content:\n{data}")

if __name__ == "__main__":
    asyncio.run(test_api())
