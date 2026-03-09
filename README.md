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

