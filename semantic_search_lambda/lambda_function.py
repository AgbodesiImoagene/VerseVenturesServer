import os
import json

from pgvector.psycopg2 import register_vector
import psycopg2
from sentence_transformers import SentenceTransformer


def get_verse_list(verses):
    results = []
    for x in verses:
        verse_dict = {}
        verse_dict["book"] = x[1]
        verse_dict["chapter"] = x[2]
        verse_dict["verse"] = x[3]
        verse_dict["text"] = x[4]
        results.append(verse_dict)
    return results


def semantic_search(model, conn, query, bible_version, threshold):
    register_vector(conn)
    query_embedding = model.encode(query)
    cursor = conn.cursor()
    cursor.execute(f"SET search_path TO {bible_version}, public;")
    conn.commit()
    cursor.execute("""
        WITH distances AS (
            SELECT verse_id, encoding <=> %s AS distance
            FROM embeddings
        )
        SELECT verse_id, 1 - distance
        FROM distances
        ORDER BY distance
        LIMIT 10;
    """, (query_embedding,))
    similar_verses = cursor.fetchall()
    print("similar_verses:", similar_verses)
    similar_verses = list(filter(lambda x: x[1] >= threshold, similar_verses))
    print("filtered similar_verses:", similar_verses)
    if similar_verses:
        ids = [x[0] for x in  similar_verses]
        placeholders = ','.join(['%s'] * len(ids))
        cursor.execute(f"SELECT * FROM verses WHERE id IN ({placeholders})", ids)
        verses = cursor.fetchall()
        return get_verse_list(verses)
    return []


def get_conn(host = None, port = None, user = None, password = None, db = None):
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
        keepalives_count=5
    )


def get_error(status_code = 400, message = "Bad Request"):
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message})
    }


def get_response(response_object = []):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_object)
    }


def handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))  # Parse JSON body
        query = body.get("query", "")
        threshold = float(body.get("threshold", 0.6))
        bible_version = body.get("bible_version", "kjv")

        print("event:", event)
        print("body:", body)
        print("query:", query)
        print("threshold:", threshold)
        print("bible_version:", bible_version)

        if bible_version not in ["asv", "kjv", "net", "web"]:
            return get_error()

        if not query.strip():
            return get_response()

        model = SentenceTransformer("all-mpnet-base-v2")
        return get_response(semantic_search(model, conn, query, bible_version, threshold))
    except Exception as e:
        print(e)
        return get_error(500, "Internal Server Error")


conn = get_conn()
