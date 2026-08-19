import os

# The settings object is built at import time and requires AWS credentials, so
# the test environment has to be in place before anything under app/ is loaded.
# Fixing the values here also keeps the suite hermetic: it never reads a
# developer's .env, never touches the development database and never reaches AWS.
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["API_KEY"] = "test-api-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_file_upload.db"

import boto3  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402
from moto import mock_aws  # noqa: E402

from app.main import app  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import Base, engine, init_db  # noqa: E402

settings = get_settings()


@pytest_asyncio.fixture(autouse=True)
async def database():
    # ASGITransport does not run the application lifespan, so the startup hook
    # that creates the tables never fires. Calling the same init_db() the
    # application uses keeps schema creation in one place, and dropping the
    # tables afterwards leaves each test with an empty database.
    await init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def api_headers():
    return {"X-API-Key": settings.API_KEY}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def s3():
    # moto intercepts botocore, so every client built while this context is
    # open talks to an in-memory S3. The application builds a fresh client per
    # request through get_s3_service, which means requests made inside a test
    # are captured without the application knowing anything about the mock.
    with mock_aws():
        client = boto3.client("s3", region_name=settings.AWS_REGION)
        client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
        yield client


def s3_keys(client) -> list[str]:
    response = client.list_objects_v2(Bucket=settings.S3_BUCKET_NAME)
    return [item["Key"] for item in response.get("Contents", [])]
