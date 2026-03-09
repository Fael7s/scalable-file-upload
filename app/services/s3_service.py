import uuid
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from app.config import get_settings

settings = get_settings()


class S3Service:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.S3_BUCKET_NAME

    def _generate_s3_key(self, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        unique_name = f"{uuid.uuid4().hex}"
        return f"uploads/{unique_name}.{ext}" if ext else f"uploads/{unique_name}"

    def _validate_extension(self, filename: str) -> None:
        if "." not in filename:
            raise HTTPException(status_code=400, detail="Arquivo sem extensão.")
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=400,
                detail=f"Extensão '.{ext}' não permitida. "
                       f"Permitidas: {settings.ALLOWED_EXTENSIONS}",
            )

    async def upload_file(self, file: UploadFile) -> dict:
        self._validate_extension(file.filename)

        contents = await file.read()
        file_size = len(contents)

        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo excede o limite de {settings.MAX_FILE_SIZE_MB}MB.",
            )

        s3_key = self._generate_s3_key(file.filename)

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=contents,
                ContentType=file.content_type or "application/octet-stream",
            )
        except ClientError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao enviar para S3: {e.response['Error']['Message']}",
            )

        return {
            "s3_key": s3_key,
            "file_size": file_size,
            "content_type": file.content_type,
        }

    def generate_presigned_url(self, s3_key: str, expiration: int = None) -> str:
        if expiration is None:
            expiration = settings.PRESIGNED_URL_EXPIRATION
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao gerar link: {e.response['Error']['Message']}",
            )

    def delete_file(self, s3_key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
        except ClientError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Erro ao deletar: {e.response['Error']['Message']}",
            )


def get_s3_service() -> S3Service:
    return S3Service()
