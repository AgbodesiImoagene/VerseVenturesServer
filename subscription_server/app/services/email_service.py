"""
Email service for sending verification emails and notifications.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import emails
from jinja2 import Template

from ..core.config import settings
from ..core.database import get_db_connection
from .auth_service import AuthService

logger = logging.getLogger(__name__)


class EmailService:
    """Service for email operations."""

    @staticmethod
    def create_verification_token(user_id: int) -> str:
        """Create and store a verification token for a user."""
        conn = get_db_connection()
        cursor = conn.cursor()

        token = AuthService.generate_verification_token()
        expires_at = datetime.now() + timedelta(hours=24)

        cursor.execute(
            """
            INSERT INTO email_verification_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
            RETURNING token
        """,
            (user_id, token, expires_at),
        )

        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        return result["token"]

    @staticmethod
    def verify_email_token(token: str) -> Optional[int]:
        """Verify an email verification token and return user ID."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id FROM email_verification_tokens
            WHERE token = %s AND expires_at > NOW()
        """,
            (token,),
        )

        result = cursor.fetchone()

        if result:
            user_id = result["user_id"]

            # Mark email as verified
            cursor.execute(
                "UPDATE users SET email_verified = TRUE WHERE id = %s",
                (user_id,),
            )

            # Delete the used token
            cursor.execute(
                "DELETE FROM email_verification_tokens WHERE token = %s",
                (token,),
            )

            conn.commit()
            cursor.close()
            conn.close()

            return user_id

        cursor.close()
        conn.close()
        return None

    @staticmethod
    def send_verification_email(email: str, token: str, first_name: str) -> bool:
        """Send email verification email."""
        try:
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

            # HTML template for verification email
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Verify Your Email - VerseVentures</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                    .content { padding: 20px; background-color: #f9f9f9; }
                    .button { display: inline-block; padding: 12px 24px; background-color: #4CAF50; 
                             color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
                    .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to VerseVentures!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {{ first_name }},</h2>
                        <p>Thank you for registering with VerseVentures. To complete your registration, 
                        please verify your email address by clicking the button below:</p>
                        
                        <a href="{{ verification_url }}" class="button">Verify Email Address</a>
                        
                        <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                        <p>{{ verification_url }}</p>
                        
                        <p>This link will expire in 24 hours.</p>
                        
                        <p>If you didn't create an account with VerseVentures, you can safely ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2024 VerseVentures. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Render template
            template = Template(html_template)
            html_content = template.render(
                first_name=first_name, verification_url=verification_url
            )

            # Send email
            message = emails.Message(
                subject="Verify Your Email - VerseVentures",
                html=html_content,
                mail_from=settings.FROM_EMAIL,
            )

            smtp_options = {
                "host": settings.SMTP_HOST,
                "port": settings.SMTP_PORT,
                "user": settings.SMTP_USERNAME,
                "password": settings.SMTP_PASSWORD,
                "tls": True,
            }

            response = message.send(to=email, smtp=smtp_options)

            if response.status_code not in [250, 200, 201, 202]:
                logger.error(
                    f"Failed to send verification email: {response.status_code}"
                )
                return False

            logger.info(f"Verification email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Error sending verification email: {str(e)}")
            return False

    @staticmethod
    def cleanup_expired_tokens():
        """Clean up expired verification tokens."""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "DELETE FROM email_verification_tokens WHERE expires_at < NOW()"
            )
            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired verification tokens")

        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
