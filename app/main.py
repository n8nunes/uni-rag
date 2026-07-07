from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logger import audit_logger
from app.api.documents import router as doc_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Enforce explicit CORS boundaries to mitigate Cross-Origin exploitation risks
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Infrastructure"])
async def health_check():
    audit_logger.info("Health check endpoint evaluated successfully.")
    return {"status": "healthy", "architecture": "hybrid-cloud-ready"}

app.include_router(doc_router, prefix=settings.API_V1_STR)