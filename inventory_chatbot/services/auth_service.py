# inventory_chatbot/services/auth_service.py

import logging
from datetime import datetime, timedelta

import bcrypt
from jose import jwt

from inventory_chatbot.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ------------------------------------------------------------------
# Pre-hashed passwords (generated with bcrypt).
# To add a new user, run:
#   python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
# ------------------------------------------------------------------
USERS_DB = {
    "admin": {
        "password_hash": "$2b$12$gMbd.vTjUpfmHc8XU.xvSulaGGBRaVGSB9T4DinW53aW7tNvOAfCi",  # admin123
        "role": "admin",
    },
    "manager": {
        "password_hash": "$2b$12$MJ8zYB5eJ8fHALFVXwZ3hOCqW9B6YuEDKZHx8zZwQhChH6x8dPfOe",  # manager123
        "role": "manager",
    },
    "viewer": {
        "password_hash": "$2b$12$rZjN8f3fXkDqH7XZNqT6uOBH8Z9YkW6QqX7qZQyH8zT6fQpX9fXBu",  # viewer123
        "role": "viewer",
    },
}


class AuthService:
    """Handles user authentication and JWT token management."""

    def authenticate(self, username: str, password: str):
        """
        Verify credentials using bcrypt hash comparison.
        Returns (username, role) on success, None on failure.
        """
        user = USERS_DB.get(username)
        if not user:
            return None

        # Compare supplied password against stored bcrypt hash
        if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            return None

        return username, user["role"]

    def create_token(self, username: str, role: str) -> str:
        """Create a signed JWT access token."""
        payload = {
            "sub": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> dict:
        """Decode and verify a JWT access token."""
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
