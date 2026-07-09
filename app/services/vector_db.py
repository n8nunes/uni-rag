import hashlib
import uuid
import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.models.schemas import ClassificationEnum
from app.services.ollama_client import ollama_client

class VectorDBService:
    def __init__(self):
        self.base_url = settings.VECTOR_DB_URL
        self.collection = settings.QDRANT_COLLECTION

    async def ensure_collection(self, vector_size: int | None = None) -> None:
        size = vector_size or settings.VECTOR_SIZE
        async with httpx.AsyncClient(timeout=30.0) as client:
            existing = await client.get(f"{self.base_url}/collections/{self.collection}")
            if existing.status_code == 200:
                return

            response = await client.put(
                f"{self.base_url}/collections/{self.collection}",
                json={
                    "vectors": {
                        "size": size,
                        "distance": "Cosine",
                    }
                },
            )
            response.raise_for_status()

    async def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Converts chunks to Ollama embeddings and persists them to Qdrant.
        """
        if not chunks:
            return True

        points = []
        first_vector: list[float] | None = None

        for index, chunk in enumerate(chunks):
            vector = await ollama_client.embed_text(chunk["text"])
            first_vector = first_vector or vector
            stable_key = f"{chunk['metadata']['source_file']}:{chunk['metadata']['timestamp']}:{index}"
            point_id = str(uuid.UUID(hashlib.md5(stable_key.encode("utf-8")).hexdigest()))
            points.append(
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": {
                        "text": chunk["text"],
                        **chunk["metadata"],
                    },
                }
            )

        await self.ensure_collection(vector_size=len(first_vector or []))
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.put(
                f"{self.base_url}/collections/{self.collection}/points",
                json={"points": points},
            )
            response.raise_for_status()
        return True

    async def secure_similarity_search(
        self, 
        query: str, 
        user_clearance: ClassificationEnum,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Executes a vector search heavily restricted by a server-enforced metadata filter.
        """
        # Define strict scope based on security classification clearance
        # Public users see Public. Student-Only sees Public + Student-Only, etc.
        allowed_classifications = [ClassificationEnum.PUBLIC]
        
        if user_clearance == ClassificationEnum.STUDENT_ONLY:
            allowed_classifications.append(ClassificationEnum.STUDENT_ONLY)
        elif user_clearance == ClassificationEnum.RESTRICTED:
            allowed_classifications.extend([ClassificationEnum.STUDENT_ONLY, ClassificationEnum.RESTRICTED])

        query_vector = await ollama_client.embed_text(query)

        db_metadata_filter = {
            "must": [
                {
                    "key": "classification",
                    "match": {"any": [c.value for c in allowed_classifications]},
                }
            ]
        }

        await self.ensure_collection(vector_size=len(query_vector))
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/search",
                json={
                    "vector": query_vector,
                    "limit": top_k,
                    "with_payload": True,
                    "filter": db_metadata_filter,
                },
            )
            response.raise_for_status()

        results = []
        for item in response.json().get("result", []):
            payload = item.get("payload", {})
            results.append(
                {
                    "text": payload.get("text", ""),
                    "score": item.get("score"),
                    "metadata": {
                        "source_file": payload.get("source_file", "unknown"),
                        "classification": payload.get("classification", ClassificationEnum.PUBLIC.value),
                        "uploaded_by": payload.get("uploaded_by", "unknown"),
                        "timestamp": payload.get("timestamp"),
                    },
                }
            )

        return results

vector_db = VectorDBService()
