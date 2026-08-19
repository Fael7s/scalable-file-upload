import time
import pytest
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from app.config import get_settings

settings = get_settings()


def presigned_ttl_seconds(url: str) -> int:
    """Seconds of validity encoded in a presigned URL.

    botocore picks the signature version from the client configuration, and the
    two styles express the deadline differently: SigV4 carries a duration in
    X-Amz-Expires, the legacy S3 signer carries an absolute epoch in Expires.
    Normalising here keeps the assertions about the application's behaviour
    rather than about which signer botocore selected.
    """
    query = parse_qs(urlparse(url).query)
    if "X-Amz-Expires" in query:
        return int(query["X-Amz-Expires"][0])
    return int(query["Expires"][0]) - int(time.time())


async def upload(client, api_headers, name="file.txt", content=b"data"):
    response = await client.post(
        "/files/upload",
        headers=api_headers,
        files={"file": (name, BytesIO(content), "text/plain")},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_download_not_found(client, api_headers):
    response = await client.get("/files/fake-id/download", headers=api_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_returns_uploaded_files(client, api_headers, s3):
    names = ["first.txt", "second.txt", "third.txt"]
    for name in names:
        await upload(client, api_headers, name)

    response = await client.get("/files/", headers=api_headers)

    assert response.status_code == 200
    listed = response.json()
    assert len(listed) == 3
    assert {item["filename"] for item in listed} == set(names)


@pytest.mark.asyncio
async def test_list_respects_skip_and_limit(client, api_headers, s3):
    for name in ["a.txt", "b.txt", "c.txt"]:
        await upload(client, api_headers, name)

    first_page = await client.get("/files/?skip=0&limit=2", headers=api_headers)
    second_page = await client.get("/files/?skip=2&limit=2", headers=api_headers)

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1

    seen = [item["id"] for item in first_page.json() + second_page.json()]
    assert len(set(seen)) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["limit=0", "limit=101", "skip=-1"])
async def test_list_rejects_pagination_outside_the_bounds(client, api_headers, query):
    response = await client.get(f"/files/?{query}", headers=api_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_accepts_the_maximum_limit(client, api_headers):
    response = await client.get("/files/?limit=100", headers=api_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_download_link_is_presigned_for_the_stored_object(
    client, api_headers, s3
):
    uploaded = await upload(client, api_headers, "manual.pdf")

    response = await client.get(
        f"/files/{uploaded['id']}/download", headers=api_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == uploaded["id"]
    assert body["filename"] == "manual.pdf"
    assert body["expires_in"] == settings.PRESIGNED_URL_EXPIRATION

    url = body["download_url"]
    assert settings.S3_BUCKET_NAME in url
    assert "uploads/" in url
    # A presigned GET carries its authorisation in the query string.
    assert "Signature=" in url
    assert presigned_ttl_seconds(url) == pytest.approx(
        settings.PRESIGNED_URL_EXPIRATION, abs=5
    )


@pytest.mark.asyncio
async def test_download_link_honours_a_custom_expiration(client, api_headers, s3):
    uploaded = await upload(client, api_headers)

    response = await client.get(
        f"/files/{uploaded['id']}/download?expiration=900", headers=api_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body["expires_in"] == 900
    assert presigned_ttl_seconds(body["download_url"]) == pytest.approx(900, abs=5)


@pytest.mark.asyncio
@pytest.mark.parametrize("expiration", [59, 43201])
async def test_download_link_rejects_expiration_outside_the_bounds(
    client, api_headers, s3, expiration
):
    uploaded = await upload(client, api_headers)

    response = await client.get(
        f"/files/{uploaded['id']}/download?expiration={expiration}",
        headers=api_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("expiration", [60, 43200])
async def test_download_link_accepts_the_boundary_values(
    client, api_headers, s3, expiration
):
    uploaded = await upload(client, api_headers)

    response = await client.get(
        f"/files/{uploaded['id']}/download?expiration={expiration}",
        headers=api_headers,
    )

    assert response.status_code == 200
    assert response.json()["expires_in"] == expiration
