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
- `rag`: busca vetorial, prompt anti-alucinação, geração da resposta e feedback supervisionado.
- `core`: configuração, banco, logging e exceções.

## Fluxo de ingestão

```text
MediaWiki API -> HTML bruto -> texto limpo -> hash -> chunks -> embeddings -> PostgreSQL
```

A ingestão é idempotente por `title UNIQUE`, `content_hash` e recriação dos chunks quando o conteúdo muda.

## Fluxo RAG

`/api/klaris/chat` é a única superfície conversacional pública. Quando a mensagem
é factual sobre Deepwoken, o agente aciona internamente o fluxo RAG:

```text
chat -> classificação factual -> reescrita de consulta -> expansão qualificada -> retrieval híbrido -> seleção de fontes fortes -> LLM -> resposta com sources
```

`/api/rag/search` existe apenas para debug administrativo protegido por
`X-Admin-Api-Key`. Não há `/api/rag/ask` público.

O retrieval combina:

- busca lexical por título, heading e conteúdo;
- análise de assunto e qualificadores de domínio, como `Oath`, `requirements` e `drops`;
- expansão de consultas quando a reescrita do modelo remove uma faceta importante;
- busca vetorial por pgvector como complemento semântico.

## Fluxo de melhoria

```text
answer_id -> feedback humano -> rag_answer_feedback -> estatísticas -> revisão de prompt/retrieval/ingestão
```

O autoaperfeiçoamento é deliberadamente supervisionado. Feedback e métricas indicam onde melhorar, mas nenhuma rotina altera prompt, código, embeddings ou conteúdo da wiki sem revisão explícita.

## Decisões técnicas

- Monólito modular para reduzir complexidade operacional.
- PostgreSQL + pgvector para manter dados relacionais e busca semântica no mesmo banco.
- Alembic como fonte de verdade para schema.
- Docker Compose com host interno `db`, mantendo compatibilidade com rede Docker.
- Feedback de RAG em tabelas próprias para não contaminar a base factual da wiki.
