# Semantic Search Lambda

A serverless version of the VerseVentures semantic search functionality, designed for AWS Lambda deployment. This lambda function provides the same core features as the semantic search API but optimized for serverless execution.

## Features

- **Semantic Search**: Search Bible verses using sentence embeddings
- **Multiple Bible Versions**: Support for KJV, ASV, NET, and WEB
- **Configurable Parameters**: Threshold, max results, and bible version selection
- **CORS Support**: Full CORS headers for web client integration
- **Error Handling**: Comprehensive error handling and logging
- **Health Check**: Health check endpoint for monitoring

## API Endpoints

### Semantic Search

```http
POST /semantic-search
Content-Type: application/json

{
  "query": "love your neighbor",
  "threshold": 0.7,
  "bible_version": "kjv",
  "max_results": 10
}
```

Response:

```json
[
  {
    "book": "Matthew",
    "chapter": 22,
    "verse": 39,
    "text": "And the second is like unto it, Thou shalt love thy neighbour as thyself."
  }
]
```

### Supported Bible Versions

```http
GET /supported-bible-versions
```

Response:

```json
{
  "supported_bible_versions": ["asv", "kjv", "net", "web"]
}
```

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "healthy"
}
```

## Parameters

### Search Parameters

- **query** (string, required): The search query text
- **threshold** (float, optional, default: 0.6): Similarity threshold (0-1)
- **bible_version** (string, optional, default: "kjv"): Bible version to search
- **max_results** (integer, optional, default: 10): Maximum number of results (1-100)

### Supported Bible Versions

- `asv` - American Standard Version
- `kjv` - King James Version
- `net` - New English Translation
- `web` - World English Bible

## Deployment

### 1. Package Dependencies

The lambda function requires several large dependencies. Use a deployment package:

```bash
# Create deployment package
pip install -r requirements.txt -t ./package
cp lambda_function.py ./package/
cd package
zip -r ../semantic-search-lambda.zip .
```

### 2. AWS Lambda Configuration

- **Runtime**: Python 3.9 or later
- **Memory**: 2048 MB (recommended for sentence transformers)
- **Timeout**: 30 seconds
- **Architecture**: x86_64

### 3. Environment Variables

Set these environment variables in your Lambda function:

```bash
DB_HOST=your-rds-endpoint
DB_PORT=5432
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_NAME=your-db-name
```

### 4. API Gateway Integration

Configure API Gateway with the following routes:

- `POST /semantic-search`
- `GET /supported-bible-versions`
- `GET /health`

### 5. VPC Configuration

If your database is in a VPC, configure the Lambda function to run in the same VPC with appropriate security groups.

## Performance Considerations

### Cold Start Optimization

- The sentence transformer model is loaded on each cold start
- Consider using Lambda Provisioned Concurrency for consistent performance
- Model size: ~420MB (all-mpnet-base-v2)

### Memory and Timeout

- **Memory**: 2048 MB recommended for optimal performance
- **Timeout**: 30 seconds to handle model loading and search operations
- **Concurrency**: Monitor and adjust based on your usage patterns

### Database Connection

- Connection pooling is configured for Lambda environment
- Connections are properly closed after each request
- Consider using RDS Proxy for better connection management

## Monitoring and Logging

### CloudWatch Logs

The function logs important events:

- Request parameters
- Search results count
- Error details
- Performance metrics

### Metrics to Monitor

- Invocation count
- Duration
- Error rate
- Memory usage
- Database connection errors

## Error Handling

The function handles various error scenarios:

- Invalid JSON requests
- Missing or invalid parameters
- Database connection errors
- Model loading errors
- Invalid bible versions

## CORS Support

The function includes CORS headers for web client integration:

```json
{
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
}
```

## Security

### Database Security

- Use IAM authentication for RDS when possible
- Ensure Lambda has minimal required permissions
- Use VPC security groups to restrict access

### API Security

- Consider adding API key authentication
- Use API Gateway throttling
- Monitor for abuse and implement rate limiting

## Cost Optimization

### Lambda Costs

- Optimize memory allocation for your use case
- Use provisioned concurrency for consistent workloads
- Monitor and optimize function duration

### Database Costs

- Use RDS reserved instances for predictable workloads
- Consider Aurora Serverless for variable workloads
- Monitor query performance and optimize indexes

## Troubleshooting

### Common Issues

1. **Cold Start Delays**

   - Use provisioned concurrency
   - Consider using a smaller model
   - Implement caching strategies

2. **Memory Issues**

   - Increase Lambda memory allocation
   - Monitor memory usage in CloudWatch
   - Optimize model loading

3. **Database Connection Issues**

   - Check VPC configuration
   - Verify security group rules
   - Test database connectivity

4. **Timeout Issues**
   - Increase Lambda timeout
   - Optimize database queries
   - Check for slow model loading

### Debugging

Enable detailed logging by setting the log level:

```python
logger.setLevel(logging.DEBUG)
```

## Comparison with API Version

| Feature                 | Lambda     | API       |
| ----------------------- | ---------- | --------- |
| Semantic Search         | ✅         | ✅        |
| Multiple Bible Versions | ✅         | ✅        |
| WebSocket Support       | ❌         | ✅        |
| Real-time Search        | ❌         | ✅        |
| Connection Pooling      | ✅         | ✅        |
| CORS Support            | ✅         | ✅        |
| Health Check            | ✅         | ✅        |
| Deployment              | Serverless | Container |
| Scaling                 | Auto       | Manual    |
| Cold Starts             | Yes        | No        |

## Future Enhancements

- **Model Optimization**: Use quantized models for faster loading
- **Caching**: Implement Redis caching for frequent queries
- **Batch Processing**: Support for batch search requests
- **Custom Models**: Allow custom embedding models
- **Analytics**: Add usage analytics and metrics
