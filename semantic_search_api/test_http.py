import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")


def get_aws_credentials():
    """Get temporary AWS credentials using the API key"""
    url = "https://je13jp2mtl.execute-api.eu-west-1.amazonaws.com/credentials"
    API_KEY = "8eyxtBRzAVZccPtKMIsxiFueNY/A8bpyXNY6Tn5bgPw="
    headers = {"X-API-Key": API_KEY}

    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting credentials: {response.status_code}")
        print(response.text)
        return None


def test_http_endpoint():
    # First, get temporary AWS credentials (for demonstration purposes)
    # credentials = get_aws_credentials()
    # print(credentials)
    # if not credentials:
    #     print("Failed to get AWS credentials. Exiting.")
    #     return

    # URL for the HTTP endpoint
    url = "https://je13jp2mtl.execute-api.eu-west-1.amazonaws.com/semantic-search"

    # Request payload
    payload = {
        "query": "love your neighbour",
        "threshold": 0.6,
        "bible_version": "kjv",
    }

    # Send POST request (no AWS authentication headers needed)
    response = requests.post(url, json=payload)

    # Check if request was successful
    if response.status_code == 200:
        results = response.json()
        print("Search results:")
        print(json.dumps(results, indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    test_http_endpoint()
