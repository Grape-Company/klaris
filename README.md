# Deepwoken RAG

Base local consultável para conteúdo da Deepwoken Wiki usando RAG. O sistema coleta páginas da MediaWiki API, salva conteúdo limpo no PostgreSQL, gera chunks com embeddings em pgvector e responde perguntas com fontes.

## Stack

- Python 3.11
- FastAPI
- PostgreSQL com pgvector
- SQLAlchemy 2.0
- Alembic
- httpx + BeautifulSoup
- OpenAI API para embeddings e resposta
- Pytest, Ruff e Mypy
- Docker Compose

## Rodar local com Docker

Crie `.env` a partir de `.env.example` e configure `OPENAI_API_KEY`.

Para OpenAI, deixe `OPENAI_BASE_URL` vazio:

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
LLM_MODEL=gpt-4o-mini
```

Para NVIDIA ou outro provedor OpenAI-compatível, configure também a URL base e modelos compatíveis:

```env
OPENAI_API_KEY=nvapi-...
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
EMBEDDING_MODEL=<modelo-de-embedding-compativel>
EMBEDDING_DIMENSIONS=1536
LLM_MODEL=<modelo-chat-compativel>
```

O schema inicial usa `wiki_chunks.embedding vector(1536)`. Se o provedor retornar embeddings com outra dimensão, ajuste `EMBEDDING_DIMENSIONS` e a migration/schema antes da ingestão ou recrie o banco com a dimensão correta.

```bash
docker compose up --build
```

O Compose sobe PostgreSQL/pgvector, aplica `alembic upgrade head` e inicia a API em `http://localhost:8000`.

## Rodar sem Docker

```bash
cp .env.example .env
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
docker compose up -d db
./.venv/bin/alembic upgrade head
./.venv/bin/uvicorn app.main:app --reload
```

## Comandos úteis

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m ruff check .
./.venv/bin/python -m mypy app
./.venv/bin/python -m scripts.ingest_all_pages 0 100
./.venv/bin/python -m scripts.ingest_category Weapons
./.venv/bin/python -m scripts.rebuild_embeddings
```

## API principal

- `GET /health`
- `GET /api/wiki/pages`
- `GET /api/wiki/pages/{id}`
- `GET /api/wiki/search?query=...`
- `GET /api/wiki/categories`
- `GET /api/wiki/categories/{name}/pages`
- `POST /api/ingestion/run`
- `POST /api/ingestion/pages/{title}`
- `POST /api/ingestion/category/{category}`
- `GET /api/ingestion/runs`
- `GET /api/ingestion/runs/{id}`
- `POST /api/rag/search`
- `POST /api/rag/ask`

## Bot Discord

O bot deve ser uma aplicação separada que chama esta API. Veja [docs/discord-bot.md](docs/discord-bot.md).

Exemplo:

```bash
curl -X POST http://localhost:8000/api/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"what is Shrine of Order?","top_k":8}'
```

## Decisões

O projeto é um monólito modular. Routers chamam services, services chamam repositories, repositories acessam banco. A ingestão é separada da consulta para preservar latência baixa no RAG.
