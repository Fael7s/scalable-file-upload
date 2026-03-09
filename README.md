# 📁 Scalable File Upload System

API REST escalável para upload de arquivos com armazenamento no Amazon S3,
geração de links temporários para download e logs de acesso.

## Stack

- **Python 3.12** + **FastAPI**
- **Amazon S3** (armazenamento)
- **Amazon EC2** (deploy)
- **SQLite** (metadata/logs — substituível por PostgreSQL)
- **Docker**

## Funcionalidades

- Upload de arquivos com validação de tipo e tamanho
- Armazenamento seguro no S3 (bucket privado)
- Geração de presigned URLs com expiração configurável
- Logs de acesso completos (upload, download, deleção)
- Autenticação via API Key
- Listagem e deleção de arquivos

## Quick Start

### 1. Clone e configure

```bash
git clone https://github.com/Fael7s/scalable-file-upload.git
cd scalable-file-upload
cp .env.example .env
# Edite o .env com suas credenciais AWS
```

### 2. Rode com Docker

```bash
docker-compose up --build
```

### 3. Ou rode localmente

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Acesse a documentação interativa: **http://localhost:8000/docs**

## Endpoints

| Método   | Rota                        | Descrição                    |
|----------|-----------------------------|------------------------------|
| `POST`   | `/files/upload`             | Upload de arquivo            |
| `GET`    | `/files/`                   | Listar arquivos              |
| `GET`    | `/files/{id}/download`      | Gerar link temporário        |
| `DELETE` | `/files/{id}`               | Deletar arquivo              |
| `GET`    | `/logs/`                    | Listar logs de acesso        |
| `GET`    | `/logs/file/{id}`           | Logs de um arquivo específico|
| `GET`    | `/health`                   | Health check                 |

## Exemplo de uso com cURL

```bash
# Upload
curl -X POST http://localhost:8000/files/upload \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "file=@documento.pdf"

# Gerar link de download (expira em 1h)
curl http://localhost:8000/files/{file_id}/download?expiration=3600 \
  -H "X-API-Key: your-secret-api-key-here"

# Ver logs
curl http://localhost:8000/logs/ \
  -H "X-API-Key: your-secret-api-key-here"
```

## Deploy no EC2

1. Lance uma instância EC2 (Amazon Linux 2 / Ubuntu)
2. Instale Docker e Docker Compose
3. Clone o repositório e configure `.env`
4. Execute `bash scripts/setup_aws.sh seu-bucket us-east-1`
5. Execute `docker-compose up -d`
6. Configure o Security Group para liberar a porta 8000

## Arquitetura

```
Cliente → EC2 (FastAPI) → Amazon S3
                ↓
           SQLite/PostgreSQL (metadata + logs)
```

## Testes

```bash
pytest tests/ -v
```

## Licença

MIT
