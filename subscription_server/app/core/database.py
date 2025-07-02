"""
Database connection and initialization utilities.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Optional
from .config import settings

logger = logging.getLogger(__name__)


def get_db_connection():
    """Get a database connection with RealDictCursor."""
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        cursor_factory=RealDictCursor,
    )


def init_database():
    """Initialize database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255),
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email_verified BOOLEAN DEFAULT FALSE,
                stripe_customer_id VARCHAR(255),
                oauth_provider VARCHAR(50),
                oauth_id VARCHAR(255),
                oauth_picture VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(oauth_provider, oauth_id)
            )
        """
        )

        # Create email_verification_tokens table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create subscriptions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                stripe_subscription_id VARCHAR(255) UNIQUE,
                stripe_customer_id VARCHAR(255),
                plan_name VARCHAR(100) NOT NULL,
                status VARCHAR(50) NOT NULL,
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create api_keys table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                api_key VARCHAR(255) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create usage_logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                api_endpoint VARCHAR(100),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email_verified ON users(email_verified)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user_id ON email_verification_tokens(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_token ON email_verification_tokens(token)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires_at "
            "ON email_verification_tokens(expires_at)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON usage_logs(timestamp)"
        )

        # Create function to update updated_at timestamp
        cursor.execute(
            """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """
        )

        # Create triggers to automatically update updated_at
        cursor.execute(
            """
            DROP TRIGGER IF EXISTS update_users_updated_at ON users;
            CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """
        )

        cursor.execute(
            """
            DROP TRIGGER IF EXISTS update_subscriptions_updated_at ON subscriptions;
            CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """
        )

        conn.commit()
        logger.info("Database initialized successfully")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


class DatabaseManager:
    """Database connection manager with context support."""

    def __init__(self):
        self.connection = None
        self.cursor = None

    def __enter__(self):
        self.connection = get_db_connection()
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
            self.connection.close()
