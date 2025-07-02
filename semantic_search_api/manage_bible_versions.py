#!/usr/bin/env python3
"""
Bible Version Management Script

This script allows you to dynamically add new bible versions to the database
without requiring code changes or service restarts.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse
from dotenv import load_dotenv

load_dotenv(".env")


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        cursor_factory=RealDictCursor,
    )


def list_bible_versions():
    """List all available bible versions in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('asv', 'kjv', 'net', 'web', 'esv', 'niv', 'nlt', 'nasb', 'nkjv')
            AND schema_name != 'information_schema'
            AND schema_name != 'pg_catalog'
            ORDER BY schema_name
        """
        )

        versions = [row["schema_name"] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        print("Available Bible Versions:")
        for version in versions:
            print(f"  - {version.upper()}")

        return versions
    except Exception as e:
        print(f"Error listing bible versions: {e}")
        return []


def add_bible_version(version_name):
    """Add a new bible version schema to the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if schema already exists
        cursor.execute(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = %s
        """,
            (version_name.lower(),),
        )

        if cursor.fetchone():
            print(f"Bible version '{version_name}' already exists.")
            return False

        # Create the schema
        cursor.execute(f"CREATE SCHEMA {version_name.lower()}")

        # Create the verses table
        cursor.execute(
            f"""
            CREATE TABLE {version_name.lower()}.verses (
                id SERIAL PRIMARY KEY,
                book VARCHAR(50) NOT NULL,
                chapter INTEGER NOT NULL,
                verse INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create the embeddings table
        cursor.execute(
            f"""
            CREATE TABLE {version_name.lower()}.embeddings (
                verse_id INTEGER REFERENCES {version_name.lower()}.verses(id),
                encoding vector(768),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (verse_id)
            )
        """
        )

        # Create indexes
        cursor.execute(
            f"""
            CREATE INDEX idx_{version_name.lower()}_verses_book_chapter_verse 
            ON {version_name.lower()}.verses(book, chapter, verse)
        """
        )

        cursor.execute(
            f"""
            CREATE INDEX idx_{version_name.lower()}_embeddings_encoding 
            ON {version_name.lower()}.embeddings USING ivfflat (encoding vector_cosine_ops)
        """
        )

        conn.commit()
        cursor.close()
        conn.close()

        print(f"Successfully added bible version '{version_name.upper()}'")
        print(
            f"Schema '{version_name.lower()}' created with tables: verses, embeddings"
        )
        return True

    except Exception as e:
        print(f"Error adding bible version: {e}")
        return False


def remove_bible_version(version_name):
    """Remove a bible version schema from the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if schema exists
        cursor.execute(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name = %s
        """,
            (version_name.lower(),),
        )

        if not cursor.fetchone():
            print(f"Bible version '{version_name}' does not exist.")
            return False

        # Drop the schema (this will drop all tables in the schema)
        cursor.execute(f"DROP SCHEMA {version_name.lower()} CASCADE")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"Successfully removed bible version '{version_name.upper()}'")
        return True

    except Exception as e:
        print(f"Error removing bible version: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Manage Bible Versions")
    parser.add_argument(
        "action", choices=["list", "add", "remove"], help="Action to perform"
    )
    parser.add_argument("--version", "-v", help="Bible version name (for add/remove)")

    args = parser.parse_args()

    if args.action == "list":
        list_bible_versions()
    elif args.action == "add":
        if not args.version:
            print("Error: --version is required for 'add' action")
            sys.exit(1)
        add_bible_version(args.version)
    elif args.action == "remove":
        if not args.version:
            print("Error: --version is required for 'remove' action")
            sys.exit(1)
        remove_bible_version(args.version)


if __name__ == "__main__":
    main()
