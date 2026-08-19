import pytest
from io import BytesIO


async def upload(client, api_headers, name="doc.txt"):
    response = await client.post(
        "/files/upload",
        headers=api_headers,
        files={"file": (name, BytesIO(b"content"), "text/plain")},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_file_history_returns_only_that_files_entries(client, api_headers, s3):
    tracked = await upload(client, api_headers, "tracked.txt")
    other = await upload(client, api_headers, "other.txt")
    await client.get(f"/files/{tracked['id']}/download", headers=api_headers)
    await client.delete(f"/files/{tracked['id']}", headers=api_headers)

    response = await client.get(f"/logs/file/{tracked['id']}", headers=api_headers)

    assert response.status_code == 200
    entries = response.json()
    assert sorted(entry["action"] for entry in entries) == [
        "DELETE",
        "DOWNLOAD_LINK",
        "UPLOAD",
    ]
    # The second file shares the table, so a history that ignored the file id
    # would return four entries here and both entries below.
    other_history = await client.get(
        f"/logs/file/{other['id']}", headers=api_headers
    )
    assert [entry["action"] for entry in other_history.json()] == ["UPLOAD"]


@pytest.mark.asyncio
async def test_logs_filter_returns_only_the_requested_action(client, api_headers, s3):
    first = await upload(client, api_headers, "one.txt")
    await upload(client, api_headers, "two.txt")
    await client.delete(f"/files/{first['id']}", headers=api_headers)

    unfiltered = (await client.get("/logs/", headers=api_headers)).json()
    assert len(unfiltered) == 3

    filtered = (await client.get("/logs/?action=DELETE", headers=api_headers)).json()
    assert [entry["action"] for entry in filtered] == ["DELETE"]
    assert filtered[0]["file_id"] == first["id"]


@pytest.mark.asyncio
async def test_logs_filter_on_an_unused_action_returns_nothing(
    client, api_headers, s3
):
    await upload(client, api_headers)

    response = await client.get("/logs/?action=DELETE", headers=api_headers)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_logs_respect_skip_and_limit(client, api_headers, s3):
    for name in ["a.txt", "b.txt", "c.txt"]:
        await upload(client, api_headers, name)

    first_page = (await client.get("/logs/?skip=0&limit=2", headers=api_headers)).json()
    second_page = (
        await client.get("/logs/?skip=2&limit=2", headers=api_headers)
    ).json()

    assert len(first_page) == 2
    assert len(second_page) == 1
    assert len({entry["id"] for entry in first_page + second_page}) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["limit=0", "limit=201", "skip=-1"])
async def test_logs_reject_pagination_outside_the_bounds(client, api_headers, query):
    response = await client.get(f"/logs/?{query}", headers=api_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_logs_accept_the_maximum_limit(client, api_headers):
    response = await client.get("/logs/?limit=200", headers=api_headers)
    assert response.status_code == 200
