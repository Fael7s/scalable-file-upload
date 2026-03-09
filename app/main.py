from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import get_settings
from app.database import init_db
from app.routes import upload, download, logs

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="API escalável para upload de arquivos com armazenamento S3",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(upload.router)
app.include_router(download.router)
app.include_router(logs.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}
