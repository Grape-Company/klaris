# RAG

## Busca

O retriever gera embedding da pergunta e consulta `wiki_chunks` com distância cosseno usando pgvector:

```sql
ORDER BY c.embedding <=> :embedding::vector
```

`/api/rag/search` retorna os trechos recuperados para depuração sem chamar o modelo de linguagem.

## Prompt

O prompt fixa regras anti-alucinação:

- responder apenas com base no contexto;
- dizer `não encontrei essa informação na base atual.` quando faltar contexto;
- citar páginas usadas;
- não inventar builds, números, talentos, requisitos ou mecânicas;
- não usar conhecimento externo.

## Resposta

`/api/rag/ask` retorna:

```json
{
  "answer": "...",
  "sources": [
    {
      "title": "Shadowcast",
      "url": "https://deepwoken.fandom.com/wiki/Shadowcast",
      "chunk_id": "..."
    }
  ]
}
```

Se nenhum chunk for recuperado, a API retorna a frase padrão sem fontes.
