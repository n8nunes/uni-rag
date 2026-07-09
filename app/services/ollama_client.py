import httpx
from app.core.config import settings
from app.core.logger import audit_logger

class OllamaClient:
    def __init__(self):
        self.client_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        self.embedding_url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"

    async def generate_response(self, prompt: str, context: str) -> str:
        """
        Sends the isolated context along with the user prompt to the local LLM.
        """
        system_instructions = (
            "You are an enterprise AI assistant. Answer the user's question using ONLY "
            "the provided authorized document context. If the context doesn't contain the answer, "
            "state clearly that you do not have permission or context to answer.\n\n"
            f"Context:\n{context}"
        )

        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": f"{system_instructions}\n\nUser Question: {prompt}",
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.client_url, json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "No response generated.")
                return f"Error from AI Engine: Status code {response.status_code}"
        except httpx.ConnectError:
            audit_logger.error("Failed to connect to Ollama. Verify the service is running locally.")
            return "AI Engine is currently unreachable. Please verify local environment status."

    async def embed_text(self, text: str) -> list[float]:
        payload = {
            "model": settings.OLLAMA_EMBEDDING_MODEL,
            "prompt": text,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.embedding_url, json=payload)
            response.raise_for_status()
            embedding = response.json().get("embedding")
            if not embedding:
                raise RuntimeError("Ollama returned an empty embedding.")
            return embedding

ollama_client = OllamaClient()
