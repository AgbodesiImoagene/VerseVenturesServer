import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_aws_credentials():
    """Get temporary AWS credentials using the API key"""
    import requests

    url = "http://0.0.0.0:8080/credentials"
    headers = {"X-API-Key": os.environ.get("SERVICE_API_KEY", "default-dev-key")}

    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting credentials: {response.status_code}")
        print(response.text)
        return None


async def test_websocket():
    # First, get temporary AWS credentials (for demonstration purposes)
    credentials = get_aws_credentials()
    if not credentials:
        print("Failed to get AWS credentials. Exiting.")
        return

    # uri = "ws://nm4cqppvgm.eu-west-1.awsapprunner.com/ws/semantic-search"
    uri = "ws://x2glbxzr4k.execute-api.eu-west-1.amazonaws.com/default/search/ws/semantic-search"

    # Connect to WebSocket (no AWS authentication headers needed)
    async with websockets.connect(uri) as websocket:
        request = {
            "query": "love your neighbor",
            "threshold": 0.6,
            "bible_version": "kjv",
        }
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        print(json.loads(response))


asyncio.run(test_websocket())
