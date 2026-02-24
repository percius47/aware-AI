from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from app.core.config import settings
from app.core.logging_config import get_logger
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx
import json

logger = get_logger("auth")
security = HTTPBearer()

_jwks_cache: Dict[str, Any] = {}

class CurrentUser(BaseModel):
    """Authenticated user model extracted from JWT token."""
    id: str
    email: Optional[str] = None

def _get_jwks() -> Dict[str, Any]:
    """Fetch and cache JWKS from Supabase."""
    global _jwks_cache
    
    if _jwks_cache:
        return _jwks_cache
    
    if not settings.SUPABASE_URL:
        return {}
    
    try:
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        response = httpx.get(jwks_url, timeout=10)
        if response.status_code == 200:
            _jwks_cache = response.json()
            logger.info(f"Fetched JWKS from Supabase: {len(_jwks_cache.get('keys', []))} keys")
        return _jwks_cache
    except Exception as e:
        logger.warning(f"Failed to fetch JWKS: {e}")
        return {}

def _get_signing_key(token: str) -> Optional[str]:
    """Get the signing key for a token from JWKS."""
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg")
        
        logger.debug(f"Token header: alg={alg}, kid={kid}")
        
        if alg == "HS256":
            return settings.SUPABASE_JWT_SECRET
        
        jwks = _get_jwks()
        keys = jwks.get("keys", [])
        
        for key in keys:
            if key.get("kid") == kid:
                return jwk.construct(key)
        
        if keys:
            return jwk.construct(keys[0])
            
    except Exception as e:
        logger.warning(f"Error getting signing key: {e}")
    
    return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """
    Dependency to extract and verify the current user from JWT token.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        CurrentUser with id and email extracted from token
        
    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    token = credentials.credentials
    
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        
        if alg == "HS256":
            if not settings.SUPABASE_JWT_SECRET:
                logger.error("SUPABASE_JWT_SECRET not configured for HS256")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication not configured"
                )
            key = settings.SUPABASE_JWT_SECRET
        else:
            key = _get_signing_key(token)
            if not key:
                logger.error(f"Could not find signing key for algorithm: {alg}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not verify token"
                )
        
        payload = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience="authenticated"
        )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            logger.warning("Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        logger.debug(f"Authenticated user: {user_id}")
        return CurrentUser(id=user_id, email=email)
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except Exception as e:
        logger.error(f"Unexpected auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )
