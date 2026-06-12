import structlog
from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger()


class Embedder:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def embed_text(self, text: str, input_type: str = "passage") -> list[float]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self.dimensions,
            extra_body={"input_type": input_type},
        )
        return response.data[0].embedding

    async def embed_query(self, text: str) -> list[float]:
        return await self.embed_text(text, input_type="query")

    async def embed_texts(
        self,
        texts: list[str],
        input_type: str = "passage",
    ) -> list[list[float]]:
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
            extra_body={"input_type": input_type},
        )
        embeddings = [item.embedding for item in response.data]
        return embeddings
