from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import json
import os
import logging
import boto3
from datetime import datetime

from pgvector.psycopg2 import register_vector
import psycopg2
from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv

load_dotenv(".env")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security configuration
API_KEY = os.environ.get("SERVICE_API_KEY", "default-dev-key")
SESSION_DURATION = os.environ.get("SESSION_DURATION", 900)
api_key_header = APIKeyHeader(name="X-API-Key")

app = FastAPI(title="Semantic Search API")
model = SentenceTransformer("all-mpnet-base-v2")


class SearchRequest(BaseModel):
    query: str
    threshold: float = 0.6
    bible_version: str = "kjv"


class CredentialsResponse(BaseModel):
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: datetime


def get_verse_list(verses):
    results = []
    for x in verses:
        verse_dict = {"book": x[1], "chapter": x[2], "verse": x[3], "text": x[4]}
        results.append(verse_dict)
    return results


def get_conn(host=None, port=None, user=None, password=None, db=None):
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


async def semantic_search(conn, query: str, bible_version: str, threshold: float):
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
        SELECT verse_id, 1 - distance
        FROM distances
        ORDER BY distance
        LIMIT 10;
    """,
        (query_embedding,),
    )

    similar_verses = cursor.fetchall()

    similar_verses = list(filter(lambda x: x[1] >= threshold, similar_verses))

    if similar_verses:
        ids = [x[0] for x in similar_verses]
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(f"SELECT * FROM verses WHERE id IN ({placeholders})", ids)
        verses = cursor.fetchall()
        return get_verse_list(verses)
    return []


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )
    return api_key


@app.websocket("/ws/semantic-search")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conn = get_conn()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                request_data = json.loads(data)
                search_request = SearchRequest(**request_data)

                if search_request.bible_version not in ["asv", "kjv", "net", "web"]:
                    await websocket.send_json({"error": "Invalid bible version"})
                    continue

                if not search_request.query.strip():
                    await websocket.send_json([])
                    continue

                results = await semantic_search(
                    conn,
                    search_request.query,
                    search_request.bible_version,
                    search_request.threshold,
                )

                await websocket.send_json(results)

            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                await websocket.send_json({"error": "Internal server error"})

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    finally:
        conn.close()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/semantic-search")
async def http_semantic_search(search_request: SearchRequest):
    conn = get_conn()
    try:
        if search_request.bible_version not in ["asv", "kjv", "net", "web"]:
            return {"error": "Invalid bible version"}

        if not search_request.query.strip():
            return []

        results = await semantic_search(
            conn,
            search_request.query,
            search_request.bible_version,
            search_request.threshold,
        )

        return results
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {"error": "Internal server error"}
    finally:
        conn.close()


@app.post("/credentials", response_model=CredentialsResponse)
async def get_temporary_credentials(api_key: str = Depends(verify_api_key)):
    try:
        # Initialize STS client
        sts_client = boto3.client("sts")

        # Generate temporary credentials
        response = sts_client.get_session_token(DurationSeconds=int(SESSION_DURATION))

        credentials = response["Credentials"]

        return CredentialsResponse(
            access_key_id=credentials["AccessKeyId"],
            secret_access_key=credentials["SecretAccessKey"],
            session_token=credentials["SessionToken"],
            expiration=credentials["Expiration"],
        )

    except Exception as e:
        logger.error(f"Error generating credentials: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to generate temporary credentials"
        )
