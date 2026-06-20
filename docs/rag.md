# RAG

## Busca

O retriever usa busca híbrida. Primeiro ele analisa a pergunta para separar:

- assunto principal, como `Chainwarden`;
- qualificadores de domínio, como `Oath`, `requirements`, `drops`, `NPC` ou `location`;
- consulta limpa para comparação textual.

Depois ele cria variações de busca preservando entidade + qualificador. Exemplo:

```text
Chainwarden oath -> Chainwarden oath, Chainwarden Oath, Chainwarden
```

A busca lexical prioriza chunks que contenham o assunto e o qualificador no
heading ou no conteúdo. Isso evita tratar uma página genérica de entidade como
evidência forte quando a pergunta pede uma faceta específica, como Oath,
requisitos ou drops.

Em paralelo, o retriever gera embedding da pergunta e consulta `wiki_chunks`
com distância cosseno usando pgvector:

```sql
ORDER BY c.embedding <=> :embedding::vector
```

`/api/rag/search` retorna os trechos recuperados para depuração sem chamar o
modelo de linguagem. Essa rota é administrativa e exige `X-Admin-Api-Key`.

Usuários finais não chamam RAG diretamente. Eles usam `POST /api/klaris/chat`;
quando a mensagem exige conhecimento de Deepwoken, Klaris executa a busca
internamente.

O agente da Klaris também tenta a pergunta original e expansões qualificadas
quando a reescrita inicial do modelo fica fraca ou genérica demais.

## Prompt

O prompt fixa regras anti-alucinação:

- responder apenas com base no contexto;
- dizer `I could not find that information in the current archive.` quando faltar contexto;
- citar páginas usadas;
- não inventar builds, números, talentos, requisitos ou mecânicas;
- não usar conhecimento externo.

## Resposta

`/api/klaris/chat` retorna:

```json
{
  "response": "...",
  "sources": [
    {
      "title": "Shadowcast",
      "url": "https://deepwoken.fandom.com/wiki/Shadowcast",
      "chunk_id": "..."
    }
  ]
}
```

Se nenhum chunk forte for recuperado, a API retorna a frase padrão sem fontes.
Chunks fracos ou ambíguos não são enviados como base factual para a resposta.

## Autoaperfeiçoamento supervisionado

O sistema não treina modelo próprio e não permite que a IA altere código, prompt ou conteúdo da wiki sozinha.

O ciclo de melhoria é:

```text
pergunta -> resposta com answer_id -> feedback humano -> métricas -> ajuste revisado de ingestão/retrieval/prompt
```

`POST /api/rag/feedback` é administrativo e recebe:

```json
{
  "answer_id": "0b04602b-5dd1-4895-a321-5b831b9d60f8",
  "rating": "negative",
  "correction": "A fonte recuperada não sustenta esse requisito."
}
```

`rating` aceita apenas `positive` ou `negative`. `correction` é opcional e serve para auditoria humana.

`GET /api/rag/improvement/stats` retorna estatísticas agregadas de feedback e é rota administrativa protegida por `X-Admin-Api-Key`.

Cada resposta registrada salva:

- pergunta;
- resposta;
- `top_k`;
- versão do prompt;
- modelo usado;
- chunks usados como fonte;
- scores dos chunks recuperados.
