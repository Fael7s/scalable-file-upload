import uuid
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from app.config import get_settings

settings = get_settings()

class S3Service:
    def __init__(self):
        # Conecta ao S3 usando as variáveis de ambiente carregadas
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.S3_BUCKET_NAME

    def _get_unique_key(self, filename: str) -> str:
        # Gera um nome aleatório para o arquivo no S3 para evitar conflitos
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        random_id = uuid.uuid4().hex
        return f"uploads/{random_id}.{ext}" if ext else f"uploads/{random_id}"

    def _validate_file_type(self, filename: str) -> None:
        if "." not in filename:
            raise HTTPException(status_code=400, detail="O arquivo enviado não possui uma extensão.")
        
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=400,
                detail=f"O formato '.{ext}' não é permitido. Use: {settings.ALLOWED_EXTENSIONS}",
            )

    async def upload(self, file: UploadFile) -> dict:
        self._validate_file_type(file.filename)
        
        # Lê o conteúdo para calcular o tamanho real antes de subir
        body = await file.read()
        size = len(body)

        if size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo excede o limite permitido de {settings.MAX_FILE_SIZE_MB}MB.",
            )

        key = self._get_unique_key(file.filename)

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType=file.content_type or "application/octet-stream",
            )
        except ClientError as e:
            msg = e.response.get('Error', {}).get('Message', 'Erro no S3')
            raise HTTPException(status_code=502, detail=f"Falha ao salvar no storage: {msg}")

        return {
            "s3_key": key,
            "file_size": size,
            "content_type": file.content_type,
        }

    def get_signed_url(self, key: str, ttl: int = None) -> str:
        ttl = ttl or settings.PRESIGNED_URL_EXPIRATION
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=ttl,
            )
        except ClientError as e:
            msg = e.response.get('Error', {}).get('Message', 'Erro ao gerar link')
            raise HTTPException(status_code=502, detail=f"Não foi possível gerar o link: {msg}")

    def remove(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            msg = e.response.get('Error', {}).get('Message', 'Erro ao deletar')
            raise HTTPException(status_code=502, detail=f"Erro ao remover arquivo: {msg}")

def get_s3_service() -> S3Service:
    return S3Service()
