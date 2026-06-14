# Banco de Dados

## Extensão

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

## Tabelas

- `wiki_pages`: páginas coletadas, HTML bruto, texto limpo e hash.
- `wiki_categories`: categorias da wiki.
- `wiki_page_categories`: relação N:N entre páginas e categorias.
- `wiki_chunks`: chunks por página, token count e embedding `vector(1536)`.
- `ingestion_runs`: auditoria das execuções de ingestão.
- `rag_answer_logs`: auditoria de respostas geradas, prompt/modelo e chunks recuperados.
- `rag_answer_feedback`: feedback humano vinculado a uma resposta registrada.

## Índices

- `idx_wiki_pages_title`
- `idx_wiki_pages_title_trgm` usando `gin_trgm_ops` para busca aproximada de títulos
- `idx_wiki_chunks_page_id`
- `idx_wiki_chunks_embedding` usando `ivfflat` e `vector_cosine_ops`
- `idx_rag_answer_feedback_answer_id`
- `idx_rag_answer_feedback_rating`

## Migrations

Alembic é a fonte de verdade do schema:

```bash
alembic upgrade head
alembic downgrade -1
```

Não altere models sem criar ou atualizar migration correspondente.
