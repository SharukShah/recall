"""
Authentication module for ReCall API.
Simple API key-based authentication for single-user MVP.
"""
from fastapi import HTTPException, Header
from config import settings


async def get_current_user(authorization: str = Header(None)):
    """
    Simple API key authentication.
    Expects header: Authorization: Bearer <API_KEY>
    
    If no API_KEY is configured in settings, allows all requests (development mode).
    """
    if not settings.API_KEY:
        # If no API key is configured, allow access (development mode)
        return {"id": 1, "username": "default"}
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    if token != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return {"id": 1, "username": "user"}
