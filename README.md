# 📁 Scalable File Upload System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)

API REST de alta performance desenvolvida para gerenciar o ciclo de vida de arquivos (upload, listagem, download seguro e deleção) utilizando infraestrutura de nuvem. O projeto demonstra o uso de tecnologias modernas de backend e integração com serviços de storage escaláveis.

## 🛠️ Stack Tecnológica

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Framework assíncrono de alta performance)
- **Storage:** [Amazon S3](https://aws.amazon.com/s3/) (Armazenamento de objetos altamente disponível)
- **Banco de Dados:** SQLite com [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (ORM Assíncrono)
- **Segurança:** Autenticação via API Key e Presigned URLs (Links temporários)
- **DevOps:** Docker & Docker Compose para padronização de ambiente
- **Testes:** Pytest com suporte a testes assíncronos (httpx)

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
