import pytest
from io import BytesIO

# Every route that depends on verify_api_key. The identifiers do not need to
# exist: the dependency runs before the handler body, so an authenticated call
# answers 404 while an unauthenticated one never gets that far.
PROTECTED_ENDPOINTS = [
    ("POST", "/files/upload"),
    ("GET", "/files/"),
    ("GET", "/files/some-id/download"),
    ("DELETE", "/files/some-id"),
    ("GET", "/logs/"),
    ("GET", "/logs/file/some-id"),
]

BAD_CREDENTIALS = {
    "missing": {},
    "wrong": {"X-API-Key": "not-the-configured-key"},
    "empty": {"X-API-Key": ""},
}


async def call(client, method, path, headers):
    # The upload route also declares a required body. Sending a valid one keeps
    # authentication the only thing the request can be rejected for.
    extra = {}
    if method == "POST":
        extra["files"] = {"file": ("probe.txt", BytesIO(b"probe"), "text/plain")}
    return await client.request(method, path, headers=headers, **extra)


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
@pytest.mark.parametrize(
    "headers", BAD_CREDENTIALS.values(), ids=BAD_CREDENTIALS.keys()
)
async def test_protected_endpoint_rejects_bad_credentials(
    client, s3, method, path, headers
):
    response = await call(client, method, path, headers)
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
async def test_protected_endpoint_accepts_the_configured_key(
    client, s3, api_headers, method, path
):
    # Without this the rejections above would also pass against a typo in the
    # path or a route that no longer exists, since both answer with an error
    # too. Any status other than 403 proves the route was actually reached.
    response = await call(client, method, path, api_headers)
    assert response.status_code != 403

