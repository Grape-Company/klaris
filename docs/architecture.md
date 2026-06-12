# Arquitetura

## Visão geral

O sistema usa RAG, não treinamento próprio:

```text
pergunta -> embedding -> pgvector -> chunks relevantes -> prompt -> LLM -> resposta com fontes
```

## Camadas

```text
router -> service -> repository -> database
```

Routers cuidam apenas de HTTP, validação via schemas e códigos de resposta. Services coordenam casos de uso. Repositories isolam SQLAlchemy e consultas. Clients externos ficam fora de services e repositories.

## Módulos

- `wiki`: leitura de páginas, categorias e busca textual simples.
- `ingestion`: MediaWiki client, limpeza, chunking, embeddings e pipeline.
- `rag`: busca vetorial, prompt anti-alucinação e geração da resposta.
- `core`: configuração, banco, logging e exceções.

## Fluxo de ingestão

```text
MediaWiki API -> HTML bruto -> texto limpo -> hash -> chunks -> embeddings -> PostgreSQL
```

A ingestão é idempotente por `title UNIQUE`, `content_hash` e recriação dos chunks quando o conteúdo muda.

## Fluxo RAG

`/api/rag/search` retorna apenas chunks. `/api/rag/ask` recupera chunks, monta contexto e chama o modelo. A resposta inclui fontes usadas.

## Decisões técnicas

- Monólito modular para reduzir complexidade operacional.
- PostgreSQL + pgvector para manter dados relacionais e busca semântica no mesmo banco.
- Alembic como fonte de verdade para schema.
- Docker Compose com host interno `db`, mantendo compatibilidade com rede Docker.
