from fastapi import Request, Depends
from fastapi.security import APIKeyHeader
from fastapi import HTTPException, Security
from app.config import get_settings

settings = get_settings()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str = Security(api_key_header),
) -> str:
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="API Key inválida ou ausente.")
    return api_key


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
