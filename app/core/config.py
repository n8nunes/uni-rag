from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Document Search Engine"
    API_V1_STR: str = "/api/v1"
    
    # Security Configuration
    JWT_SECRET_KEY: str = "SUPER_SECRET_DEVELOPMENT_KEY_CHANGE_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Local service routing. In Docker/Kubernetes, Ollama normally runs on the host.
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    VECTOR_DB_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "university_documents"
    VECTOR_SIZE: int = 768
    
    # Allowed CORS Origins for frontend integration
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
