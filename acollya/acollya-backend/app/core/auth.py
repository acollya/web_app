"""
Authentication helpers: JWT RS256 + bcrypt + Google OAuth.

JWT design:
  - Access tokens:  RS256, 15 min TTL, signed with private key
  - Refresh tokens: RS256, 30 day TTL, contains jti (UUID) stored in Redis
  - Refresh token rotation: on /auth/refresh the old jti is deleted and a new one
    is issued. Revocation = just delete the jti from Redis.

Token payload structure:
  {
    "sub":  "user-uuid",            # user.id
    "type": "access" | "refresh",
    "jti":  "uuid4",                # refresh tokens only — for revocation
    "iat":  unix timestamp,
    "exp":  unix timestamp,
  }

Google OAuth:
  - Client sends the ID token from Google Sign-In SDK
  - We verify it via Google's tokeninfo endpoint (no secret needed)
  - On success we upsert the user (google_id, email, name)
"""
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt as _bcrypt
import httpx
from jose import JWTError, jwt

from app.config import settings
from app.core.exceptions import AuthenticationError, InvalidTokenError, TokenExpiredError

logger = logging.getLogger(__name__)

# ── bcrypt helpers ─────────────────────────────────────────────────────────────
# Using bcrypt directly (passlib 1.7.4 is incompatible with bcrypt >= 4.0).
_BCRYPT_ROUNDS = 12


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ────────────────────────────────────────────────────────────────

def _jwt_config() -> dict:
    """Lazy-loaded JWT config from Secrets Manager (cached after first call)."""
    return settings.jwt_config


def create_access_token(user_id: str) -> str:
    """Create a short-lived RS256 access token."""
    cfg = _jwt_config()
    expire = datetime.now(UTC) + timedelta(
        minutes=cfg.get("access_token_expire_minutes", 15)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": datetime.now(UTC),
        "exp": expire,
    }
    return jwt.encode(payload, cfg["private_key"], algorithm=cfg.get("algorithm", "RS256"))


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Create a long-lived RS256 refresh token.

    Returns (token_string, jti) — caller must store jti in Redis.
    """
    cfg = _jwt_config()
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(
        days=cfg.get("refresh_token_expire_days", 30)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": datetime.now(UTC),
        "exp": expire,
    }
    token = jwt.encode(payload, cfg["private_key"], algorithm=cfg.get("algorithm", "RS256"))
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Raises:
      TokenExpiredError   - token is past its exp
      InvalidTokenError   - signature invalid or malformed
    """
    cfg = _jwt_config()
    try:
        payload = jwt.decode(
            token,
            cfg["public_key"],
            algorithms=[cfg.get("algorithm", "RS256")],
        )
        return payload
    except JWTError as exc:
        msg = str(exc).lower()
        if "expired" in msg:
            raise TokenExpiredError() from exc
        raise InvalidTokenError() from exc


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and assert the token is of type 'access'."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise InvalidTokenError("Expected an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and assert the token is of type 'refresh'."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise InvalidTokenError("Expected a refresh token")
    return payload


# ── Google OAuth ───────────────────────────────────────────────────────────────

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


async def verify_google_id_token(id_token: str) -> dict[str, Any]:
    """
    Verify a Google ID token via Google's tokeninfo endpoint.

    Returns the decoded token payload with at least:
      { "sub": "...", "email": "...", "name": "...", "picture": "..." }

    Raises:
      AuthenticationError - if the token is invalid or the audience doesn't match
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("Google tokeninfo rejected token: %s", exc.response.text)
            raise AuthenticationError("Invalid Google ID token") from exc
        except httpx.RequestError as exc:
            logger.error("Google tokeninfo request failed: %s", exc)
            raise AuthenticationError("Could not verify Google token") from exc

    # Validate audience — must match our app's client ID(s).
    # Fails closed: if no client IDs are configured, the token is rejected.
    # This prevents accepting tokens from other Google-integrated apps.
    cfg = settings.jwt_config
    google_client_ids: list[str] = cfg.get("google_client_ids", [])
    if not google_client_ids:
        logger.error(
            "google_client_ids not configured — rejecting Google token to fail closed. "
            "Add client ID(s) to the JWT secret under the 'google_client_ids' key."
        )
        raise AuthenticationError("Google OAuth not configured on this server")
    if data.get("aud") not in google_client_ids:
        raise AuthenticationError("Google token audience mismatch")

    if "sub" not in data or "email" not in data:
        raise AuthenticationError("Google token missing required fields")

    return data


APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_BUNDLE_ID = "com.acollya.app"


async def verify_apple_identity_token(identity_token: str) -> dict[str, Any]:
    """
    Verify an Apple identity token (JWT) using Apple's public keys.

    Returns payload with at least: { "sub": "...", "email": "..." }
    email may be absent on subsequent sign-ins (Apple only provides it once).

    Raises AuthenticationError on invalid token.
    """
    import json
    import base64

    # Fetch Apple's public JWKS
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(APPLE_KEYS_URL)
            resp.raise_for_status()
            jwks = resp.json()
        except Exception as exc:
            logger.error("Failed to fetch Apple public keys: %s", exc)
            raise AuthenticationError("Could not verify Apple token") from exc

    # Decode header to find the right key
    try:
        import json, base64
        header_segment = identity_token.split(".")[0]
        header_json = base64.urlsafe_b64decode(header_segment + "==")
        header = json.loads(header_json)
        kid = header.get("kid")
        alg = header.get("alg", "RS256")
    except Exception as exc:
        raise AuthenticationError("Invalid Apple token format") from exc

    # Find the matching key
    key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key_data:
        raise AuthenticationError("Apple token key not found")

    try:
        # python-jose can decode using a JWK dict directly
        payload = jwt.decode(
            identity_token,
            key_data,
            algorithms=[alg],
            audience=APPLE_BUNDLE_ID,
            issuer=APPLE_ISSUER,
        )
    except JWTError as exc:
        logger.warning("Apple token verification failed: %s", exc)
        raise AuthenticationError("Invalid Apple identity token") from exc
    except Exception as exc:
        logger.warning("Apple token verification unexpected error: %s", exc)
        raise AuthenticationError("Could not verify Apple token") from exc

    if "sub" not in payload:
        raise AuthenticationError("Apple token missing required fields")

    return payload
