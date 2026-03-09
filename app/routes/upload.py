from fastapi import APIRouter, UploadFile, File, Depends, Request
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
    result = await s3.upload_file(file)

    file_record = FileRecord(
        original_filename=file.filename,
        s3_key=result["s3_key"],
        content_type=result["content_type"],
        file_size=result["file_size"],
    )
    db.add(file_record)
    await db.flush()

    log_svc = LogService(db)
    await log_svc.create_log(
        action="UPLOAD",
        file_id=file_record.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"Arquivo '{file.filename}' ({result['file_size']} bytes)",
    )

    return {
        "id": file_record.id,
        "filename": file_record.original_filename,
        "size": file_record.file_size,
        "content_type": file_record.content_type,
        "uploaded_at": file_record.uploaded_at.isoformat(),
    }


@router.delete("/{file_id}", status_code=200)
async def delete_file(
    file_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    s3: S3Service = Depends(get_s3_service),
    _api_key: str = Depends(verify_api_key),
):
    from sqlalchemy import select
    result = await db.execute(
        select(FileRecord).where(FileRecord.id == file_id)
    )
    file_record = result.scalar_one_or_none()
    if not file_record:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    s3.delete_file(file_record.s3_key)
    await db.delete(file_record)

    log_svc = LogService(db)
    await log_svc.create_log(
        action="DELETE",
        file_id=file_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        details=f"Arquivo '{file_record.original_filename}' deletado",
    )

    return {"message": "Arquivo deletado com sucesso."}
