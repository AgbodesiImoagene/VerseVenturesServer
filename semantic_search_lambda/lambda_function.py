import os
import json
import logging
import time

from pgvector.psycopg2 import register_vector
import psycopg2
from sentence_transformers import SentenceTransformer

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fallback versions if database is unavailable
DEFAULT_SUPPORTED_BIBLE_VERSIONS = ["asv", "kjv", "net", "web"]


def get_verse_list(verses):
    """Convert database verse tuples to dictionary format"""
    results = []
    for x in verses:
        verse_dict = {"book": x[1], "chapter": x[2], "verse": x[3], "text": x[4]}
        results.append(verse_dict)
    return results


def semantic_search(model, conn, query, bible_version, threshold, max_results=10):
    """Perform semantic search on Bible verses"""
    register_vector(conn)
    query_embedding = model.encode(query)
    cursor = conn.cursor()
    cursor.execute(f"SET search_path TO {bible_version}, public;")
    conn.commit()

    cursor.execute(
        """
        WITH distances AS (
            SELECT verse_id, encoding <=> %s AS distance
            FROM embeddings
        )
        SELECT verse_id, 1 - distance AS similarity
        FROM distances
        WHERE 1 - distance >= %s
        ORDER BY similarity DESC
        LIMIT %s;
    """,
        (query_embedding, threshold, max_results),
    )

    similar_verses = cursor.fetchall()
    logger.info(f"Found {len(similar_verses)} similar verses after threshold filtering")

    if similar_verses:
        ids = [x[0] for x in similar_verses]
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(f"SELECT * FROM verses WHERE id IN ({placeholders})", ids)
        verses = cursor.fetchall()
        return get_verse_list(verses)
    return []


def get_conn(host=None, port=None, user=None, password=None, db=None):
    """Get database connection with connection pooling settings"""
    host = os.environ.get("DB_HOST") if not host else host
    port = os.environ.get("DB_PORT") if not port else port
    user = os.environ.get("DB_USER") if not user else user
    password = os.environ.get("DB_PASSWORD") if not password else password
    db = os.environ.get("DB_NAME") if not db else db

    url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return psycopg2.connect(
        url,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


def get_error_response(status_code=400, message="Bad Request"):
    """Generate error response"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
        "body": json.dumps({"error": message}),
    }


def get_success_response(response_object):
    """Generate success response"""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
        "body": json.dumps(response_object),
    }


def get_supported_bible_versions_from_db():
    """Fetch supported bible versions from database"""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # Query to get available schemas (bible versions)
        cursor.execute(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('asv', 'kjv', 'net', 'web', 'esv', 'niv', 'nlt')
            AND schema_name != 'information_schema'
            AND schema_name != 'pg_catalog'
            ORDER BY schema_name
        """
        )

        versions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        return versions if versions else DEFAULT_SUPPORTED_BIBLE_VERSIONS
    except Exception as e:
        logger.warning(f"Failed to fetch bible versions from database: {e}")
        return DEFAULT_SUPPORTED_BIBLE_VERSIONS


def get_supported_versions():
    """Get supported bible versions with caching"""
    # Simple in-memory cache (could be enhanced with Redis)
    if not hasattr(get_supported_versions, "_cache") or not hasattr(
        get_supported_versions, "_cache_time"
    ):
        get_supported_versions._cache = None
        get_supported_versions._cache_time = 0

    # Cache for 5 minutes
    current_time = time.time()
    if (
        get_supported_versions._cache is None
        or current_time - get_supported_versions._cache_time > 300
    ):

        get_supported_versions._cache = get_supported_bible_versions_from_db()
        get_supported_versions._cache_time = current_time

    return get_supported_versions._cache


def handle_semantic_search(event, context):
    """Handle semantic search requests"""
    try:
        body = json.loads(event.get("body", "{}"))
        query = body.get("query", "")
        threshold = float(body.get("threshold", 0.6))
        bible_version = body.get("bible_version", "kjv")
        max_results = int(body.get("max_results", 10))

        logger.info(
            f"Search request - Query: {query}, Bible Version: {bible_version}, "
            f"Threshold: {threshold}, Max Results: {max_results}"
        )

        # Validate bible version
        if bible_version not in get_supported_versions():
            return get_error_response(
                400,
                f"Invalid bible version. Supported versions: "
                f"{get_supported_versions()}",
            )

        # Validate query
        if not query.strip():
            return get_success_response([])

        # Validate parameters
        if threshold < 0 or threshold > 1:
            return get_error_response(400, "Threshold must be between 0 and 1")

        if max_results < 1 or max_results > 100:
            return get_error_response(400, "Max results must be between 1 and 100")

        # Perform search
        model = SentenceTransformer("all-mpnet-base-v2")
        conn = get_conn()

        try:
            results = semantic_search(
                model, conn, query, bible_version, threshold, max_results
            )
            return get_success_response(results)
        finally:
            conn.close()

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return get_error_response(400, "Invalid JSON format")
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return get_error_response(400, f"Invalid parameter value: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing semantic search request: {str(e)}")
        return get_error_response(500, "Internal server error")


def handle_supported_versions(event, context):
    """Handle supported bible versions request"""
    return get_success_response({"supported_bible_versions": get_supported_versions()})


def handle_health_check(event, context):
    """Handle health check request"""
    return get_success_response({"status": "healthy"})


def handler(event, context):
    """Main Lambda handler"""
    try:
        # Handle CORS preflight requests
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                },
                "body": "",
            }

        # Route requests based on path
        path = event.get("path", "")
        http_method = event.get("httpMethod", "")

        logger.info(f"Request - Method: {http_method}, Path: {path}")

        if path == "/health" and http_method == "GET":
            return handle_health_check(event, context)
        elif path == "/supported-bible-versions" and http_method == "GET":
            return handle_supported_versions(event, context)
        elif path == "/semantic-search" and http_method == "POST":
            return handle_semantic_search(event, context)
        else:
            return get_error_response(404, "Endpoint not found")

    except Exception as e:
        logger.error(f"Unexpected error in handler: {str(e)}")
        return get_error_response(500, "Internal server error")
