from app.main import app
from app.modules.rag.service import truncate_answer


def test_rag_ask_is_not_public() -> None:
    paths = {path for route in app.routes if isinstance(path := getattr(route, "path", None), str)}

    assert "/api/rag/ask" not in paths


def test_klaris_ask_is_not_public() -> None:
    paths = {path for route in app.routes if isinstance(path := getattr(route, "path", None), str)}

    assert "/api/klaris/ask" not in paths


def test_truncate_answer_keeps_response_under_limit() -> None:
    answer = truncate_answer("x" * 2500, max_chars=100)

    assert len(answer) <= 100
    assert answer.endswith("[resposta truncada]")
