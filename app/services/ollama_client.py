import httpx
from urllib.parse import quote
from app.core.config import settings
from app.core.logger import audit_logger

class OllamaClient:
    def __init__(self):
        self.client_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        self.embedding_url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"

    async def _get_web_research(self, query: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            audit_logger.warning(f"Web research lookup failed: {exc}")
            return ""

        snippets: list[str] = []
        abstract = payload.get("AbstractText")
        if abstract:
            snippets.append(f"Summary: {abstract}")

        for topic in payload.get("RelatedTopics", [])[:4]:
            if isinstance(topic, dict):
                text = topic.get("Text")
                first_url = topic.get("FirstURL")
                if text:
                    entry = text.strip()
                    if first_url:
                        entry = f"{entry} ({first_url})"
                    snippets.append(entry)

        return "\n".join(snippets[:6])

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

        web_research = await self._get_web_research(prompt)
        research_block = ""
        if web_research:
            research_block = f"Web research findings:\n{web_research}\n\n"

        system_instructions = (
            "You are an enterprise AI assistant. Answer the user's question using ONLY "
            "the provided authorized document context, but if the question requires broader or current information, "
            "use the web research findings as supplemental context. If neither the document context nor web research "
            "contains enough information, state clearly that you do not have permission or context to answer.\n\n"
            f"{history_block}"
            f"{research_block}"
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
