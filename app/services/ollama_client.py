import httpx
from app.core.config import settings
from app.core.logger import audit_logger

class OllamaClient:
    def __init__(self):
        self.client_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        self.embedding_url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"

    async def generate_response(self, prompt: str, context: str, conversation_history: list[dict] | None = None) -> str:
        """
        Sends the isolated context along with the user prompt to the local LLM.
        """
        history_block = ""
        if conversation_history:
            history_lines = []
            for message in conversation_history:
                role = str(message.get("role", "user")).capitalize()
                content = str(message.get("content", "")).strip()
                if content:
                    history_lines.append(f"{role}: {content}")
            if history_lines:
                history_block = "Conversation history:\n" + "\n".join(history_lines) + "\n\n"

        system_instructions = (
            "You are an enterprise AI assistant. Answer the user's question using ONLY "
            "the provided authorized document context. If the context doesn't contain the answer, "
            "state clearly that you do not have permission or context to answer.\n\n"
            f"{history_block}"
            f"Context:\n{context}"
        )

        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": f"{system_instructions}\n\nUser Question: {prompt}",
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(self.client_url, json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "No response generated.")
                return f"Error from AI Engine: Status code {response.status_code}"
        except httpx.ConnectError:
            audit_logger.error("Failed to connect to Ollama. Verify the service is running locally.")
            return "AI Engine is currently unreachable. Please verify local environment status."
        except httpx.TimeoutException:
            audit_logger.error("Timed out waiting for Ollama to generate a response.")
            return (
                "AI Engine timed out while generating the answer. The documents were retrieved, "
                "but the local Ollama model did not respond before the timeout."
            )
        except httpx.RequestError as exc:
            audit_logger.error(f"Ollama request failed: {exc}")
            return "AI Engine request failed. Please verify local Ollama status."

    async def embed_text(self, text: str) -> list[float]:
        payload = {
            "model": settings.OLLAMA_EMBEDDING_MODEL,
            "prompt": text,
        }

        async with httpx.AsyncClient(timeout=settings.OLLAMA_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(self.embedding_url, json=payload)
            response.raise_for_status()
            embedding = response.json().get("embedding")
            if not embedding:
                raise RuntimeError("Ollama returned an empty embedding.")
            return embedding

ollama_client = OllamaClient()
