class DeepwokenRAGError(Exception):
    pass


class WikiPageNotFoundError(DeepwokenRAGError):
    def __init__(self, title: str) -> None:
        self.title = title
        super().__init__(f"Wiki page not found: {title}")


class WikiAPIError(DeepwokenRAGError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(f"Wiki API error: {message}")


class IngestionError(DeepwokenRAGError):
    pass


class EmbeddingError(DeepwokenRAGError):
    pass


class RAGError(DeepwokenRAGError):
    pass
