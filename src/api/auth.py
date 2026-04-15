"""HTTP Basic authentication for the ECS API."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.api.settings import get_settings

security = HTTPBasic()


def require_auth(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """Validate HTTP Basic credentials against env-configured username/password."""
    settings = get_settings()
    valid_user = secrets.compare_digest(
        credentials.username.encode(), settings.api_username.encode()
    )
    valid_pass = secrets.compare_digest(
        credentials.password.encode(), settings.api_password.encode()
    )
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
