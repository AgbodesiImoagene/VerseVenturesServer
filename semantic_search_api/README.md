# Semantic Search API

A Flask-based API for semantic search using sentence transformers and FAISS for efficient similarity search.

## Features

- Semantic search using sentence transformers
- Efficient similarity search with FAISS
- REST API and WebSocket endpoints
- AWS Lambda deployment support
- Environment-based configuration
- Comprehensive test suite

## Project Structure

```
semantic_search_api/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── test_api.py           # API test script
├── test_websocket.py     # WebSocket test script
├── .env                  # Environment variables (not in repo)
└── README.md             # This file
```

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your configuration:
   ```
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=eu-west-1
   SERVICE_API_KEY=your_api_key
   ```

## Running Locally

1. Start the Flask server:
   ```bash
   python app.py
   ```
2. The API will be available at `http://localhost:5000`

## API Endpoints

### REST API

- `POST /search`: Semantic search endpoint
  ```bash
  curl -X POST http://localhost:5000/search \
    -H "Content-Type: application/json" \
    -H "X-API-Key: your_api_key" \
    -d '{"query": "love your neighbor", "threshold": 0.6}'
  ```

### WebSocket API

- `ws://localhost:5000/ws/semantic-search`: WebSocket endpoint for real-time semantic search

  ```python
  import websockets
  import json

  # Include API key in the connection headers
  headers = {
      "X-API-Key": "your_api_key"
  }

  async with websockets.connect('ws://localhost:5000/ws/semantic-search', extra_headers=headers) as websocket:
      await websocket.send(json.dumps({
          "query": "love your neighbor",
          "threshold": 0.6
      }))
      response = await websocket.recv()
      print(json.loads(response))
  ```

## Testing

1. Run API tests:

   ```bash
   python test_api.py
   ```

2. Run WebSocket tests:
   ```bash
   python test_websocket.py
   ```

## Deployment

The API is designed to be deployed on AWS Lambda. The `app.py` file includes the necessary configuration for AWS Lambda deployment.

## Authentication

The API uses a two-step authentication process:

1. **API Key Authentication**: Used for all endpoints to verify client identity

   - Pass the API key in the `X-API-Key` header for all requests
   - The API key should be set in the `SERVICE_API_KEY` environment variable on the server

2. **AWS IAM Authentication**: Used for secure access to AWS resources
   - REST API: Uses AWS Signature Version 4 for request signing
   - WebSocket API: Uses AWS Signature Version 4 for connection authentication

To authenticate requests:

1. Include your API key in the `X-API-Key` header for all requests
2. Include your AWS credentials in the `.env` file
3. The API will automatically sign requests using these credentials
4. For WebSocket connections, the authentication is handled automatically by the test script

## Error Handling

The API includes comprehensive error handling for:

- Invalid requests
- Authentication failures (including missing or invalid API keys)
- Search errors
- WebSocket connection issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
