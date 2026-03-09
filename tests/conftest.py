import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import get_settings

settings = get_settings()


@pytest.fixture
def api_headers():
    return {"X-API-Key": settings.API_KEY}


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
