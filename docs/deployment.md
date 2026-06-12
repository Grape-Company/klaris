# Deploy

## Recomendação

Use:

- Render Free para a API FastAPI.
- Supabase Free para PostgreSQL + pgvector.
- NVIDIA API para embeddings e chat.

## Variáveis obrigatórias no Render

Configure como secrets no painel do Render:

```text
ADMIN_API_KEY=<token longo aleatório>
OPENAI_API_KEY=<nova chave NVIDIA>
DATABASE_URL=postgresql+asyncpg://postgres.cvtqxsgimilehbqnoxqd:<senha>@aws-1-us-west-2.pooler.supabase.com:5432/postgres
DATABASE_SYNC_URL=postgresql://postgres.cvtqxsgimilehbqnoxqd:<senha>@aws-1-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require
```

Não coloque essas variáveis em arquivos commitados.

## Variáveis não secretas

O arquivo `render.yaml` já define:

```text
ENVIRONMENT=production
ENABLE_DOCS=false
DATABASE_SSL=true
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
EMBEDDING_MODEL=nvidia/llama-nemotron-embed-1b-v2
EMBEDDING_DIMENSIONS=1536
LLM_MODEL=openai/gpt-oss-20b
```

## Supabase

1. Crie o projeto.
2. Copie a connection string do pooler.
3. Configure `DATABASE_URL` e `DATABASE_SYNC_URL` no Render.
4. O deploy executa `alembic upgrade head` automaticamente.

Supabase suporta a extensão `vector`, usada pelo pgvector.

## Ingestão em produção

As rotas `/api/ingestion/*` exigem header:

```text
X-Admin-Api-Key: <ADMIN_API_KEY>
```

Exemplo:

```bash
curl -X POST https://<render-url>/api/ingestion/run \
  -H "Content-Type: application/json" \
  -H "X-Admin-Api-Key: <ADMIN_API_KEY>" \
  -d '{"namespace":0,"limit":100}'
```

Comece com `limit=20` ou `limit=100` para não estourar o Supabase Free.

## Endpoint público para o bot

Use apenas:

```text
POST /api/rag/ask
POST /api/rag/search
GET /health
```

Não exponha o `ADMIN_API_KEY` no bot se o bot rodar em ambiente cliente. Se o bot roda como servidor, pode guardar o token em variável secreta.
