# Banco de Dados

## Extensão

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Tabelas

- `wiki_pages`: páginas coletadas, HTML bruto, texto limpo e hash.
- `wiki_categories`: categorias da wiki.
- `wiki_page_categories`: relação N:N entre páginas e categorias.
- `wiki_chunks`: chunks por página, token count e embedding `vector(1536)`.
- `ingestion_runs`: auditoria das execuções de ingestão.

## Índices

- `idx_wiki_pages_title`
- `idx_wiki_chunks_page_id`
- `idx_wiki_chunks_embedding` usando `ivfflat` e `vector_cosine_ops`

## Migrations

Alembic é a fonte de verdade do schema:

```bash
alembic upgrade head
alembic downgrade -1
```

Não altere models sem criar ou atualizar migration correspondente.
