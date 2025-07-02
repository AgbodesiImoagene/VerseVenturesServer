#!/usr/bin/env python3
"""
Test script for the Semantic Search Lambda function
This script simulates API Gateway events to test the lambda function locally
"""

import json
import os
from lambda_function import handler

# Mock environment variables for testing
os.environ.update(
    {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "DB_NAME": "test_db",
    }
)


def create_api_gateway_event(http_method, path, body=None):
    """Create a mock API Gateway event"""
    event = {
        "httpMethod": http_method,
        "path": path,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body) if body else None,
    }
    return event


def test_health_check():
    """Test the health check endpoint"""
    print("🧪 Testing health check endpoint...")

    event = create_api_gateway_event("GET", "/health")
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_supported_versions():
    """Test the supported bible versions endpoint"""
    print("🧪 Testing supported bible versions endpoint...")

    event = create_api_gateway_event("GET", "/supported-bible-versions")
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_semantic_search():
    """Test the semantic search endpoint"""
    print("🧪 Testing semantic search endpoint...")

    search_body = {
        "query": "love your neighbor",
        "threshold": 0.7,
        "bible_version": "kjv",
        "max_results": 5,
    }

    event = create_api_gateway_event("POST", "/semantic-search", search_body)
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_semantic_search_invalid_version():
    """Test semantic search with invalid bible version"""
    print("🧪 Testing semantic search with invalid bible version...")

    search_body = {
        "query": "love your neighbor",
        "threshold": 0.7,
        "bible_version": "invalid_version",
        "max_results": 5,
    }

    event = create_api_gateway_event("POST", "/semantic-search", search_body)
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_semantic_search_invalid_threshold():
    """Test semantic search with invalid threshold"""
    print("🧪 Testing semantic search with invalid threshold...")

    search_body = {
        "query": "love your neighbor",
        "threshold": 1.5,  # Invalid threshold > 1
        "bible_version": "kjv",
        "max_results": 5,
    }

    event = create_api_gateway_event("POST", "/semantic-search", search_body)
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_semantic_search_invalid_max_results():
    """Test semantic search with invalid max_results"""
    print("🧪 Testing semantic search with invalid max_results...")

    search_body = {
        "query": "love your neighbor",
        "threshold": 0.7,
        "bible_version": "kjv",
        "max_results": 150,  # Invalid max_results > 100
    }

    event = create_api_gateway_event("POST", "/semantic-search", search_body)
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_semantic_search_empty_query():
    """Test semantic search with empty query"""
    print("🧪 Testing semantic search with empty query...")

    search_body = {
        "query": "",
        "threshold": 0.7,
        "bible_version": "kjv",
        "max_results": 5,
    }

    event = create_api_gateway_event("POST", "/semantic-search", search_body)
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_invalid_json():
    """Test with invalid JSON"""
    print("🧪 Testing with invalid JSON...")

    event = {
        "httpMethod": "POST",
        "path": "/semantic-search",
        "headers": {"Content-Type": "application/json"},
        "body": "invalid json",
    }

    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def test_cors_preflight():
    """Test CORS preflight request"""
    print("🧪 Testing CORS preflight request...")

    event = {
        "httpMethod": "OPTIONS",
        "path": "/semantic-search",
        "headers": {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    }

    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Headers: {response['headers']}")
    print()


def test_unknown_endpoint():
    """Test unknown endpoint"""
    print("🧪 Testing unknown endpoint...")

    event = create_api_gateway_event("GET", "/unknown")
    response = handler(event, {})

    print(f"Status Code: {response['statusCode']}")
    print(f"Response: {response['body']}")
    print()


def main():
    """Run all tests"""
    print("🚀 Starting Lambda function tests...")
    print("=" * 50)

    # Test basic endpoints
    test_health_check()
    test_supported_versions()

    # Test CORS
    test_cors_preflight()

    # Test semantic search (will fail without database connection)
    print("⚠️  Note: Semantic search tests will fail without a database connection")
    print("   This is expected behavior for local testing")
    print()

    test_semantic_search()
    test_semantic_search_invalid_version()
    test_semantic_search_invalid_threshold()
    test_semantic_search_invalid_max_results()
    test_semantic_search_empty_query()

    # Test error handling
    test_invalid_json()
    test_unknown_endpoint()

    print("=" * 50)
    print("✅ All tests completed!")
    print()
    print("📝 Notes:")
    print("   • Semantic search tests require a database connection")
    print("   • Error handling tests should return appropriate error responses")
    print("   • CORS tests should return proper headers")
    print("   • Health check and supported versions should work without database")


if __name__ == "__main__":
    main()
