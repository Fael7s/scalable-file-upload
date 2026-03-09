#!/bin/bash
# Cria o bucket S3 e configura políticas básicas

BUCKET_NAME=${1:-"my-file-upload-bucket"}
REGION=${2:-"us-east-1"}

echo "Criando bucket: $BUCKET_NAME na região $REGION"

aws s3api create-bucket \
  --bucket "$BUCKET_NAME" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION"

# Bloqueia acesso público
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Habilita versionamento (proteção contra deleção acidental)
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled

echo "Bucket $BUCKET_NAME criado e configurado com sucesso."
