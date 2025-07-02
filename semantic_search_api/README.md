# Semantic Search API

A Flask-based API for semantic search using sentence transformers and FAISS for efficient similarity search.

## Features

- Semantic search using sentence transformers
- Efficient similarity search with FAISS
- REST API and WebSocket endpoints
- AWS Lambda deployment support
- Environment-based configuration
- Comprehensive test suite
- **Semantic Search**: Search Bible verses using sentence transformers
- **Multiple Bible Versions**: Support for KJV, ASV, NET, WEB, and more
- **Dynamic Version Management**: Add new bible versions without code changes
- **WebSocket Support**: Real-time search capabilities
- **HTTP Endpoints**: RESTful API for search operations
- **AWS Integration**: Temporary credential generation for AWS services
- **CORS Support**: Cross-origin resource sharing enabled

## Dynamic Bible Version Management

The API now supports dynamic bible version management, allowing you to add new bible versions without requiring code changes or service restarts.

### How It Works

1. **Database-Driven**: Bible versions are detected by querying available database schemas
2. **Caching**: Results are cached for 5 minutes to improve performance
3. **Fallback**: If database is unavailable, falls back to default versions
4. **Auto-Discovery**: Automatically detects new schemas that match bible version patterns

### Managing Bible Versions

Use the management script to add or remove bible versions:

```bash
# List all available bible versions
python manage_bible_versions.py list

# Add a new bible version (e.g., ESV)
python manage_bible_versions.py add --version esv

# Remove a bible version
python manage_bible_versions.py remove --version esv
```

### Adding New Bible Versions

1. **Create Schema**: The script automatically creates the required database schema
2. **Create Tables**: Verses and embeddings tables are created with proper indexes
3. **Load Data**: You'll need to populate the tables with verse data and embeddings
4. **Auto-Detection**: The API will automatically detect and support the new version

### Database Schema

Each bible version uses its own schema with the following structure:

```sql
-- Schema: {version_name} (e.g., 'esv', 'niv')
CREATE TABLE {version_name}.verses (
    id SERIAL PRIMARY KEY,
    book VARCHAR(50) NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE {version_name}.embeddings (
    verse_id INTEGER REFERENCES {version_name}.verses(id),
    encoding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (verse_id)
);
```

### Supported Version Codes

The system supports these bible version codes:

- `asv` - American Standard Version
- `kjv` - King James Version
- `net` - New English Translation
- `web` - World English Bible
- `esv` - English Standard Version
- `niv` - New International Version
- `nlt` - New Living Translation
- `nasb` - New American Standard Bible
- `nkjv` - New King James Version

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
