# Bot Discord

## Arquitetura

O bot é uma camada fina que traduz comandos Discord em chamadas HTTP para a API FastAPI:

```
Discord /ask -> bot/cogs/ask.py -> bot/klaris_client.py -> POST /api/klaris/chat -> resposta
Discord /chat -> bot/cogs/chat.py -> bot/klaris_client.py -> POST /api/klaris/chat -> resposta
Discord /stats -> bot/cogs/stats.py -> bot/klaris_client.py -> GET /api/klaris/stats -> resposta
Discord /feedback -> bot/cogs/feedback_cog.py -> bot/klaris_client.py -> POST /api/rag/feedback -> resposta
```

**Regra fundamental:** O bot nunca acessa banco, MediaWiki API ou OpenAI diretamente. Toda operação passa pela API FastAPI.

## Estrutura do pacote

```
bot/
├── __init__.py          # Re-exports públicos
├── main.py              # Inicialização do bot, carga de cogs, sync, activity
├── config.py            # BotSettings (pydantic-settings, lê de .env)
├── klaris_client.py     # HTTP client com connection pooling (httpx.AsyncClient)
├── embeds.py            # Construtores de discord.Embed (answer, error, help, stats)
├── formatting.py        # Formatação texto legado (fallback para testes)
├── i18n.py              # Strings PT-BR e EN
├── errors.py            # Hierarquia de exceções e mapeamento HTTP -> mensagem
├── pagination.py        # PaginatedResponseView (botões anterior/próxima)
├── feedback_view.py     # FeedbackView (botões 👍/👎)
├── rate_limit.py        # UserRateLimiter (in-memory, por usuário)
├── cogs/
│   ├── ask.py           # /ask - pergunta sobre Deepwoken
│   ├── chat.py          # /chat - conversa com Klaris (com memória curta)
│   ├── help.py          # /help - lista comandos
│   ├── stats.py         # /stats - estatísticas do arquivo
│   ├── invite.py        # /invite - link de convite
│   └── feedback_cog.py  # /feedback - feedback manual sobre resposta
```

## Comandos

| Comando | Descrição |
|---------|-----------|
| `/ask <pergunta>` | Pergunta sobre Deepwoken. Responde com embed + fontes + botões 👍/👎 |
| `/chat <mensagem>` | Conversa com Klaris. Mantém contexto por sessão. |
| `/help` | Lista todos os comandos disponíveis. |
| `/stats` | Mostra estatísticas do arquivo (total de respostas, feedbacks, etc.). |
| `/invite` | Retorna link para adicionar o bot a outros servidores. |
| `/feedback <answer_id> <rating> [correction]` | Envia feedback manual sobre uma resposta anterior. |

## Configuração

### Variáveis de ambiente (no `.env`)

```env
# Obrigatórias
DISCORD_BOT_TOKEN=<token-do-bot>
BOT_API_KEY=<mesmo valor de BOT_API_KEY no backend>

# Opcionais
DISCORD_GUILD_ID=<id-do-servidor>          # Sincronização instantânea de comandos
DISCORD_INVITE_URL=<url-de-convite>        # Link para /invite
DISCORD_CLIENT_ID=<client-id>              # Alternativa para montar URL de invite
BOT_DEFAULT_LANGUAGE=pt-BR
BOT_ACTIVITY_TYPE=listening
BOT_ACTIVITY_TEXT=/ask
BOT_CACHE_TTL_SECONDS=300
BOT_CONTEXT_TTL_SECONDS=900
BOT_CONTEXT_MAX_TURNS=10
BOT_CHANNEL_RATE_LIMIT_COUNT=20
BOT_CHANNEL_RATE_LIMIT_WINDOW_SECONDS=60
BOT_GLOBAL_RATE_LIMIT_COUNT=50
BOT_GLOBAL_RATE_LIMIT_WINDOW_SECONDS=60
BOT_BLACKLISTED_USERS=
BOT_BLACKLISTED_GUILDS=
BOT_LOG_CHANNEL_ID=
```

### No backend

```env
BOT_API_KEY=<mesmo valor usado no bot>
```

Essa chave permite que o bot envie feedback (`POST /api/rag/feedback`) e consulte estatísticas (`GET /api/klaris/stats`) sem precisar da chave de admin total.

## Deploy

### Local (desenvolvimento)

```bash
docker compose up --build
```

Sobe `db`, `app` e `bot`. O bot usa `RAG_API_URL=http://app:8000` (rede Docker).

### Produção (DigitalOcean)

```bash
docker compose -f docker-compose.digitalocean.yml up -d --build
```

### Verificar logs

```bash
docker compose logs -f bot
```

## Proteções

### No bot

- Timeout HTTP configurável (`BOT_REQUEST_TIMEOUT_SECONDS`, default 30s)
- Rate limit por usuário (5 requisições / 60s, configurável)
- Rate limit por canal (20 / 60s, configurável)
- Rate limit global (50 / 60s, configurável)
- Limite de mensagem: 2000 caracteres
- Blacklist de usuários e guildas
- Cache de respostas (TTL configurável)
- Logs estruturados (structlog) sem tokens ou dados sensíveis
- Erros mapeados por código HTTP (401, 429, 503, etc.)

### No backend

- `message`/`query` limitados a 2000 caracteres
- `top_k` limitado entre 1 e 20
- Timeout nas etapas de recuperação e chamada do modelo
- Resposta truncada por `RAG_MAX_ANSWER_CHARS`
- Erros do provedor retornam HTTP 503
- Ingestão separada da consulta

## Feedback de respostas

Após cada `/ask` ou `/chat`, o bot adiciona botões 👍 e 👎 na mensagem. O clique envia `POST /api/rag/feedback` com `X-Bot-Api-Key` e registra o rating no banco (`rag_answer_feedback`).

O `answer_id` necessário para o feedback é retornado pelo backend no campo `answer_id` da resposta de `/api/klaris/chat`.

## Memória de conversa

O cog `chat.py` mantém memória curta em processo (TTL 15 min, max 10 turnos). A chave é `guild_id + channel_id + user_id`. A memória é perdida ao reiniciar o bot.
