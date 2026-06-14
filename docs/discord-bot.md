# Bot Discord

## Arquitetura recomendada

Mantenha o bot como camada separada:

```text
Discord slash command -> bot -> POST /api/klaris/chat -> Discord response
```

O bot não deve acessar banco, MediaWiki API ou OpenAI diretamente. Ele deve chamar a API FastAPI.

## Proteções obrigatórias no bot

- Timeout HTTP entre 20 e 35 segundos.
- Rate limit por usuário e por canal.
- Limite de tamanho da mensagem para 2000 caracteres.
- Tratamento de `sources=[]` com resposta neutra.
- Não logar tokens, headers de autenticação ou conteúdo sensível.
- Responder de forma efêmera quando houver erro operacional.

## Proteções já existentes na API

- `message`/`query` limitados a 2000 caracteres.
- `top_k` limitado entre 1 e 20.
- Timeout nas etapas de recuperação e chamada do modelo.
- Resposta truncada por `RAG_MAX_ANSWER_CHARS`.
- Erros do provedor retornam HTTP 503.
- Ingestão separada da consulta.

## Provedor de IA

Se usar uma chave `nvapi-...`, configure `OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1`. Sem essa URL, a SDK tenta autenticar no endpoint padrão da OpenAI e retorna 401.

## Exemplo de chamada do bot

```python
import httpx


async def ask_deepwoken(api_url: str, question: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{api_url}/api/klaris/chat",
            json={"message": question, "top_k": 8},
        )
        response.raise_for_status()
        return response.json()
```

## Formatação recomendada

Monte a resposta do Discord com:

```text
<answer>

Fontes:
- <title>: <url>
```

Se a mensagem passar de 2000 caracteres, divida em múltiplas mensagens ou reduza fontes exibidas.

## Deploy com Docker Compose

Configure no `.env`:

```env
DISCORD_BOT_TOKEN=<token-do-bot>
RAG_API_URL=http://app:8000
BOT_DEFAULT_TOP_K=8
```

Se quiser registrar slash commands instantaneamente em um servidor específico, configure também:

```env
DISCORD_GUILD_ID=<id-do-servidor>
```

Suba API, banco e bot:

```bash
docker compose -f docker-compose.digitalocean.yml up -d --build
```

Ver logs:

```bash
docker compose -f docker-compose.digitalocean.yml logs -f bot
```
