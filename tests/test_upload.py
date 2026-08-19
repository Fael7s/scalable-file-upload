import pytest
from io import BytesIO

from sqlalchemy import select

from app.config import get_settings
from app.database import async_session
from app.models import FileRecord
from tests.conftest import s3_keys

settings = get_settings()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_upload_stores_object_and_metadata(client, api_headers, s3):
    content = b"invoice contents"

    response = await client.post(
        "/files/upload",
        headers=api_headers,
        files={"file": ("invoice.pdf", BytesIO(content), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "invoice.pdf"
    assert body["size"] == len(content)
    assert body["content_type"] == "application/pdf"

    # The object exists in S3 under a server-generated key that keeps only the
    # extension of the name the client sent.
    keys = s3_keys(s3)
    assert len(keys) == 1
    assert keys[0].startswith("uploads/")
    assert keys[0].endswith(".pdf")
    assert "invoice" not in keys[0]

    stored = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=keys[0])
    assert stored["Body"].read() == content

    # The metadata row is committed with the same key.
    async with async_session() as session:
        record = (await session.execute(select(FileRecord))).scalar_one()
    assert record.id == body["id"]
    assert record.original_filename == "invoice.pdf"
    assert record.s3_key == keys[0]
    assert record.file_size == len(content)


@pytest.mark.asyncio
async def test_upload_of_two_files_with_the_same_name_does_not_collide(
    client, api_headers, s3
):
    for _ in range(2):
        response = await client.post(
            "/files/upload",
            headers=api_headers,
            files={"file": ("report.pdf", BytesIO(b"x"), "application/pdf")},
        )
        assert response.status_code == 201

    assert len(set(s3_keys(s3))) == 2


@pytest.mark.asyncio
async def test_upload_rejects_disallowed_extension(client, api_headers, s3):
    response = await client.post(
        "/files/upload",
        headers=api_headers,
        files={"file": ("payload.exe", BytesIO(b"MZ"), "application/octet-stream")},
    )

    assert response.status_code == 400
    # Nothing was stored, and the rejection happened before any S3 call.
    assert s3_keys(s3) == []


@pytest.mark.asyncio
async def test_upload_rejects_file_over_the_size_limit(
    client, api_headers, s3, monkeypatch
):
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)
    oversized = b"a" * (settings.max_file_size_bytes + 1)

    response = await client.post(
        "/files/upload",
        headers=api_headers,
        files={"file": ("big.txt", BytesIO(oversized), "text/plain")},
    )

    assert response.status_code == 413
    assert s3_keys(s3) == []
