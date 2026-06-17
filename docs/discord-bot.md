# Bot Discord

## Arquitetura

O bot é uma camada fina que traduz comandos Discord em chamadas HTTP para a API FastAPI:

```
Discord /ask -> bot/cogs/ask.py -> bot/klaris_client.py -> POST /api/klaris/chat -> resposta
Discord /chat -> bot/cogs/chat.py -> bot/klaris_client.py -> POST /api/klaris/chat -> resposta
Discord /stats -> bot/cogs/stats.py -> bot/klaris_client.py -> GET /api/klaris/stats -> resposta
Discord /feedback -> bot/cogs/feedback_cog.py -> bot/klaris_client.py -> POST /api/rag/feedback -> resposta
Discord /ping -> bot/cogs/utility.py -> bot/klaris_client.py -> GET /health -> resposta
```

**Regra fundamental:** O bot nunca acessa banco, MediaWiki API ou OpenAI diretamente. Toda operação passa pela API FastAPI.

## Estrutura do pacote

```
bot/
├── __init__.py           # Re-exports públicos
├── main.py               # Inicialização do bot, carga de cogs, sync, activity
├── config.py             # BotSettings (pydantic-settings, lê de .env)
├── klaris_client.py      # HTTP client com connection pooling + cache LRU
├── guards.py             # WindowRateLimiter, BotGuard, GuardResult
├── notifications.py      # BotNotifier — logs operacionais no Discord
├── embeds.py             # Construtores de discord.Embed (answer, error, help, stats)
├── formatting.py         # Formatação texto legado (fallback para testes)
├── i18n.py               # Strings PT-BR e EN
├── errors.py             # Hierarquia de exceções e mapeamento HTTP -> mensagem
├── pagination.py         # PaginatedResponseView (botões anterior/próxima + página)
├── feedback_view.py      # FeedbackView (botões 👍/👎 + modal de correção)
├── rate_limit.py         # Re-export de WindowRateLimiter como UserRateLimiter
├── cache.py              # LRUCache com TTL
├── cogs/
│   ├── ask.py            # /ask - pergunta sobre Deepwoken (com autocomplete)
│   ├── chat.py           # /chat - conversa com Klaris (com memória curta)
│   ├── utility.py        # /ping, /clear, /context
│   ├── admin.py          # /admin user-blacklist, guild-blacklist, stats, broadcast
│   ├── help.py           # /help - lista comandos
│   ├── stats.py          # /stats - estatísticas do arquivo
│   ├── invite.py         # /invite - link de convite
│   └── feedback_cog.py   # /feedback - feedback manual sobre resposta
```

## Comandos

| Comando | Descrição |
|---------|-----------|
| `/ask <pergunta>` | Pergunta sobre Deepwoken. Responde com embed + fontes + botões 👍/👎/✏️ |
| `/chat <mensagem>` | Conversa com Klaris. Mantém contexto por sessão. |
| `/ping` | Mede latência Discord + backend |
| `/clear` | Limpa o contexto de conversa do usuário |
| `/context` | Mostra quantos turnos estão salvos para o usuário |
| `/help` | Lista todos os comandos disponíveis. |
| `/stats` | Mostra estatísticas do arquivo (total de respostas, feedbacks, etc.). |
| `/invite` | Retorna link para adicionar o bot a outros servidores. |
| `/feedback <answer_id> <rating> [correction]` | Envia feedback manual sobre uma resposta anterior. |
| `/admin user-blacklist <add\|remove\|list> [user_id]` | Gerencia blacklist de usuários (admin) |
| `/admin guild-blacklist <add\|remove\|list> [guild_id]` | Gerencia blacklist de servidores (admin) |
| `/admin stats` | Estatísticas do bot (admin) |
| `/admin broadcast <message>` | Envia mensagem para todos os servidores (admin) |

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
BOT_DEFAULT_LANGUAGE=en
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
BOT_RESPONSE_CACHE_ENABLED=true
BOT_RESPONSE_CACHE_MAX_SIZE=128
BOT_RESPONSE_CACHE_TTL_SECONDS=600
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

### Sistema de Guards (bot/guards.py)

Todas as interações passam pelo `BotGuard.check_interaction()` que verifica:

1. **Blacklist de usuários** — usuários na lista são bloqueados
2. **Blacklist de guilds** — servidores na lista são bloqueados
3. **Rate limit global** — todas as requisições compartilham um limite
4. **Rate limit por canal** — cada canal tem seu próprio limite
5. **Rate limit por usuário** — cada usuário tem seu próprio limite

Configurações:

- `BOT_RATE_LIMIT_COUNT` / `BOT_RATE_LIMIT_WINDOW_SECONDS` (usuário)
- `BOT_CHANNEL_RATE_LIMIT_COUNT` / `BOT_CHANNEL_RATE_LIMIT_WINDOW_SECONDS` (canal)
- `BOT_GLOBAL_RATE_LIMIT_COUNT` / `BOT_GLOBAL_RATE_LIMIT_WINDOW_SECONDS` (global)
- `BOT_BLACKLISTED_USERS` / `BOT_BLACKLISTED_GUILDS` (blacklist, CSV)

### Cache de respostas (bot/cache.py)

Respostas de `/ask` são cacheadas em memória com chave normalizada (pergunta em lowercase + top_k). O cache não é usado para `/chat` (que tem histórico). Configurável via:

- `BOT_RESPONSE_CACHE_ENABLED` (bool, default true)
- `BOT_RESPONSE_CACHE_MAX_SIZE` (int, default 128)
- `BOT_RESPONSE_CACHE_TTL_SECONDS` (int, default 600)

### No bot

- Timeout HTTP configurável (`BOT_REQUEST_TIMEOUT_SECONDS`, default 30s)
- Limite de mensagem: 2000 caracteres
- Logs estruturados (structlog) sem tokens ou dados sensíveis
- Erros mapeados por código HTTP (401, 429, 503, etc.)
- Circuit breaker: falhas do backend são logadas no canal de log

### No backend

- `message`/`query` limitados a 2000 caracteres
- `top_k` limitado entre 1 e 20
- Timeout nas etapas de recuperação e chamada do modelo
- Resposta truncada por `RAG_MAX_ANSWER_CHARS`
- Erros do provedor retornam HTTP 503
- Ingestão separada da consulta

## Notificações (bot/notifications.py)

O `BotNotifier` envia eventos para o canal configurado em `BOT_LOG_CHANNEL_ID`. Eventos monitorados:

- Bot iniciado
- Erro em chamada ao backend
- Rate limit acionado
- Usuário/servidor bloqueado
- Feedback recebido
- `/clear` executado
- `/ping` com backend indisponível

Falhas no envio de log não interrompem comandos.

## Feedback de respostas

Após cada `/ask` ou `/chat`, o bot adiciona botões:

- **👍** — feedback positivo (envia direto)
- **👎** — abre modal para correção opcional
- **✏️ Corrigir** — abre o mesmo modal independentemente do rating

O clique envia `POST /api/rag/feedback` com `X-Bot-Api-Key`.

## Memória de conversa

### Volatilidade

O `ConversationStore` é **em memória** (`bot_context_backend=in_memory`). Isso significa:

- Contexto é perdido ao reiniciar o bot
- Contexto não é compartilhado entre réplicas do bot
- Cada usuário tem seu próprio contexto, chaveado por `user_id`

### Configurações

- `BOT_CONTEXT_TTL_SECONDS`: tempo de vida do contexto (default 900s / 15min)
- `BOT_CONTEXT_MAX_TURNS`: máximo de turnos armazenados (default 10)

### Plano futuro

A interface `ConversationStore` pode ser estendida para suportar Redis:

```python
class BaseConversationStore(ABC):
    @abstractmethod
    def get_history(self, user_id: str) -> list[dict[str, str]]: ...
    @abstractmethod
    def add_message(self, user_id: str, role: str, content: str) -> None: ...
    @abstractmethod
    def clear(self, user_id: str) -> None: ...
```

Com `BOT_CONTEXT_BACKEND=redis`, o `RedisConversationStore` usaria `REDIS_URL` para persistência.

## Autocomplete

O comando `/ask` possui autocomplete que busca títulos de páginas via `GET /api/wiki/suggest?query=`. As sugestões são cacheadas pelo próprio Discord (não há cache adicional no bot para isso).

## Comandos Admin

Comandos restritos a usuários com permissão `Administrator` no servidor:

- `/admin user-blacklist add/remove/list` — gerencia blacklist de usuários (runtime)
- `/admin guild-blacklist add/remove/list` — gerencia blacklist de servidores (runtime)
- `/admin stats` — mostra estatísticas do bot
- `/admin broadcast <mensagem>` — envia mensagem para todos os servidores

**Nota:** Blacklists adicionadas via comando admin são **runtime apenas**. Para blacklist persistente entre reinícios, use as variáveis de ambiente `BOT_BLACKLISTED_USERS` e `BOT_BLACKLISTED_GUILDS`.

## Endpoint de Sugestão (Backend)

`GET /api/wiki/suggest?query=&limit=10`

Criado para suportar autocomplete do Discord. Retorna lista de `{title, url}` baseada em busca ILIKE no título.

## Docker

### Serviços

```yaml
services:
  db:     # pgvector/pgvector:pg17
  app:    # FastAPI (src)
  bot:    # Bot Discord (src)
```

O bot depende do `app` (que depende do `db`). O bot acessa o app via `RAG_API_URL=http://app:8000`.

### Comandos úteis

```bash
# Build e start
docker compose up --build -d

# Logs do bot
docker compose logs -f bot

# Restart apenas do bot
docker compose restart bot
```
