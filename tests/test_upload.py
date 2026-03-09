import pytest
from io import BytesIO


@pytest.mark.asyncio
async def test_upload_without_api_key(client):
    response = await client.post(
        "/files/upload",
        files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
