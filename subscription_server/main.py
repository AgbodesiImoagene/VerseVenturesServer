"""
Entry point for the VerseVentures Subscription Server.
This file imports the modular application structure.
"""

from app.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
