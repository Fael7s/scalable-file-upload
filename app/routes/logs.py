from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.log_service import LogService
from app.middleware.access_logger import verify_api_key

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/")
async def get_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    action: str = Query(default=None, description="Filtrar por ação: UPLOAD, DOWNLOAD_LINK, DELETE"),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    log_svc = LogService(db)
    logs = await log_svc.get_logs(skip=skip, limit=limit, action=action)
    return [
        {
            "id": log.id,
            "action": log.action,
            "file_id": log.file_id,
            "ip_address": log.ip_address,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]


@router.get("/file/{file_id}")
async def get_file_logs(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    log_svc = LogService(db)
    logs = await log_svc.get_logs_by_file(file_id)
    return [
        {
            "id": log.id,
            "action": log.action,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in logs
    ]
