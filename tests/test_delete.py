import pytest
from io import BytesIO

from sqlalchemy import select

from app.database import async_session
from app.models import AccessLog, FileRecord
from tests.conftest import s3_keys


async def upload(client, api_headers, name="doc.txt"):
    response = await client.post(
        "/files/upload",
        headers=api_headers,
        files={"file": (name, BytesIO(b"content"), "text/plain")},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_delete_removes_the_object_and_the_row(client, api_headers, s3):
    uploaded = await upload(client, api_headers)
    assert len(s3_keys(s3)) == 1

    response = await client.delete(f"/files/{uploaded['id']}", headers=api_headers)

    assert response.status_code == 200
    assert s3_keys(s3) == []

    async with async_session() as session:
        remaining = (await session.execute(select(FileRecord))).scalars().all()
    assert remaining == []

    # The file is no longer addressable through the API either.
    follow_up = await client.get(
        f"/files/{uploaded['id']}/download", headers=api_headers
    )
    assert follow_up.status_code == 404


@pytest.mark.asyncio
async def test_delete_unknown_id_returns_404(client, api_headers, s3):
    response = await client.delete("/files/does-not-exist", headers=api_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_leaves_other_files_untouched(client, api_headers, s3):
    keep = await upload(client, api_headers, "keep.txt")
    remove = await upload(client, api_headers, "remove.txt")

    await client.delete(f"/files/{remove['id']}", headers=api_headers)

    assert len(s3_keys(s3)) == 1
    listed = (await client.get("/files/", headers=api_headers)).json()
    assert [item["id"] for item in listed] == [keep["id"]]


@pytest.mark.asyncio
async def test_each_operation_writes_an_access_log_entry(client, api_headers, s3):
    uploaded = await upload(client, api_headers)
    await client.get(f"/files/{uploaded['id']}/download", headers=api_headers)
    await client.delete(f"/files/{uploaded['id']}", headers=api_headers)

    async with async_session() as session:
        actions = (await session.execute(select(AccessLog.action))).scalars().all()

    assert sorted(actions) == ["DELETE", "DOWNLOAD_LINK", "UPLOAD"]

    logs = (await client.get("/logs/?action=UPLOAD", headers=api_headers)).json()
    assert len(logs) == 1
    assert logs[0]["file_id"] == uploaded["id"]
