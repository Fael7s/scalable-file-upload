# Scalable File Upload System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)

API REST de alta performance desenvolvida para gerenciar o ciclo de vida de arquivos (upload, listagem, download seguro e deleção) utilizando infraestrutura de nuvem. O projeto demonstra o uso de tecnologias modernas de backend e integração com serviços de storage escaláveis.

## Stack Tecnológica

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

### 1. Configuração Inicial

```bash
git clone https://github.com/Fael7s/scalable-file-upload.git
cd scalable-file-upload
cp .env.example .env
# Edite o arquivo .env com as credenciais AWS necessárias
```

### 2. Execução via Docker

```bash
docker-compose up --build
```

### 3. Execução Local

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A documentação interativa da API está disponível em: **http://localhost:8000/docs**

## Endpoints

| Método   | Rota                        | Descrição                    |
|----------|-----------------------------|------------------------------|
| `POST`   | `/files/upload`             | Upload de arquivo            |
| `GET`    | `/files/`                   | Listar arquivos              |
| `GET`    | `/files/{id}/download`      | Gerar link temporário        |
| `DELETE` | `/files/{id}`               | Deletar arquivo              |
| `GET`    | `/logs/`                    | Listar logs de acesso        |
| `GET`    | `/logs/file/{id}`           | Logs de um arquivo específico|
| `GET`    | `/health`                   | Health check do serviço      |

## Exemplo de Utilização (cURL)

```bash
# Upload de arquivo
curl -X POST http://localhost:8000/files/upload \
  -H "X-API-Key: your-secret-api-key-here" \
  -F "file=@documento.pdf"

# Geração de link de download (validade de 3600 segundos)
curl http://localhost:8000/files/{file_id}/download?expiration=3600 \
  -H "X-API-Key: your-secret-api-key-here"

# Consulta de logs de acesso
curl http://localhost:8000/logs/ \
  -H "X-API-Key: your-secret-api-key-here"
```

## Implantação em EC2

1. Provisionar instância EC2 (Amazon Linux 2 / Ubuntu)
2. Instalar Docker e Docker Compose
3. Clonar o repositório e configurar o arquivo `.env`
4. Executar o script de configuração: `bash scripts/setup_aws.sh <bucket-name> <region>`
5. Iniciar os serviços: `docker-compose up -d`
6. Configurar o Security Group para permitir tráfego na porta 8000

## Arquitetura do Sistema

```
Cliente -> Instância EC2 (FastAPI) -> Amazon S3
                    |
                    -> SQLite/PostgreSQL (Metadados e Logs)
```

## Testes Automatizados

```bash
pytest tests/ -v
```

## Licença

MIT
