import pytest


@pytest.mark.asyncio
async def test_download_not_found(client, api_headers):
    response = await client.get("/files/fake-id/download", headers=api_headers)
    assert response.status_code == 404
