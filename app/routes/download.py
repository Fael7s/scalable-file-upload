from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.services.s3_service import S3Service, get_s3_service
from app.services.log_service import LogService
from app.models import FileRecord
from app.middleware.access_logger import verify_api_key, get_client_ip
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/files", tags=["Download"])

@router.get("/{file_id}/download")
async def get_download_link(
    file_id: str,
    request: Request,
    expiration: int = Query(
        default=settings.PRESIGNED_URL_EXPIRATION,
        ge=60,
        le=43200,
        description="Validade do link em segundos",
    ),
    db: AsyncSession = Depends(get_db),
    s3: S3Service = Depends(get_s3_service),
    _api_key: str = Depends(verify_api_key),
):
    # Localiza o arquivo no banco para recuperar a chave do S3
    query = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = query.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Gera o link assinado temporário
    url = s3.get_signed_url(record.s3_key, expiration)

    # Cria log da solicitação de download
    log_svc = LogService(db)
    await log_svc.create_log(
        action="DOWNLOAD_LINK",
        file_id=file_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"Link gerado com expiração de {expiration}s",
    )

    return {
        "file_id": record.id,
        "filename": record.original_filename,
        "download_url": url,
        "expires_in": expiration,
    }

@router.get("/", summary="Listar arquivos cadastrados")
async def list_files(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    from sqlalchemy import desc
    
    # Busca arquivos ordenados pela data de upload
    query = await db.execute(
        select(FileRecord)
        .order_by(desc(FileRecord.uploaded_at))
        .offset(skip)
        .limit(limit)
    )
    files = query.scalars().all()
    
    return [
        {
            "id": f.id,
            "filename": f.original_filename,
            "size": f.file_size,
            "content_type": f.content_type,
            "uploaded_at": f.uploaded_at.isoformat(),
        }
        for f in files
    ]
