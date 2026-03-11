from fastapi import APIRouter, UploadFile, File, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.s3_service import S3Service, get_s3_service
from app.services.log_service import LogService
from app.models import FileRecord
from app.middleware.access_logger import verify_api_key, get_client_ip

router = APIRouter(prefix="/files", tags=["Upload"])

@router.post("/upload", status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    s3: S3Service = Depends(get_s3_service),
    _api_key: str = Depends(verify_api_key),
):
    # Envia o arquivo para o storage S3
    res = await s3.upload(file)

    # Cria o registro de metadados no banco
    record = FileRecord(
        original_filename=file.filename,
        s3_key=res["s3_key"],
        content_type=res["content_type"],
        file_size=res["file_size"],
    )
    db.add(record)
    await db.flush()

    # Registra a atividade nos logs de acesso
    log_svc = LogService(db)
    await log_svc.create_log(
        action="UPLOAD",
        file_id=record.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"Arquivo '{file.filename}' enviado com sucesso.",
    )

    return {
        "id": record.id,
        "filename": record.original_filename,
        "size": record.file_size,
        "content_type": record.content_type,
        "uploaded_at": record.uploaded_at.isoformat(),
    }

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    s3: S3Service = Depends(get_s3_service),
    _api_key: str = Depends(verify_api_key),
):
    from sqlalchemy import select
    
    query = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = query.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Remove do S3 e limpa do banco de dados
    s3.remove(record.s3_key)
    await db.delete(record)

    # Log da remoção
    log_svc = LogService(db)
    await log_svc.create_log(
        action="DELETE",
        file_id=file_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"Arquivo '{record.original_filename}' removido permanentemente.",
    )

    return {"message": "Arquivo deletado com sucesso."}
