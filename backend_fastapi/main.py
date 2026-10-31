from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import gps_job
from db.database import create_tables


create_tables()

app = FastAPI(
    title = "GPS Backend",
    description = "Api to generate gps route",
    version = "0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = settings.ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

app.include_router(gps_job.router, prefix=settings.API_PREFIX)

if __name__ == "__main__":
    import uvicorn
    print(settings.STATIC_URL)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)