Planejamento de elite — Deepwoken Knowledge Base + IA
1. Objetivo do sistema

Criar uma base local consultável com informações da Deepwoken Wiki, capaz de responder perguntas usando IA com fonte, contexto e rastreabilidade.

O sistema não deve treinar uma IA do zero. O sistema deve usar RAG, ou seja:

pergunta do usuário
→ busca no banco
→ recupera trechos relevantes
→ envia os trechos para o modelo
→ modelo responde com base apenas nesses trechos
2. Stack recomendada
Camada	Escolha
Linguagem principal	Python
API backend	FastAPI
Banco relacional	PostgreSQL
Busca vetorial	pgvector
ORM	SQLAlchemy 2.0
Migrations	Alembic
Coleta da wiki	requests/httpx + MediaWiki API
Parsing HTML	BeautifulSoup
Jobs internos	scripts Python ou Celery depois
IA	OpenAI API ou Ollama local
Testes	Pytest
Qualidade	Ruff + Black + Mypy
Config	.env com Pydantic Settings

Minha recomendação forte: comece monolítico modular, não microsserviço. Para esse projeto, microsserviço agora é overengineering.

3. Estrutura do projeto
deepwoken-rag/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   ├── modules/
│   │   ├── wiki/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── router.py
│   │   ├── ingestion/
│   │   │   ├── mediawiki_client.py
│   │   │   ├── crawler.py
│   │   │   ├── cleaner.py
│   │   │   ├── chunker.py
│   │   │   ├── embedder.py
│   │   │   └── pipeline.py
│   │   └── rag/
│   │       ├── retriever.py
│   │       ├── prompt.py
│   │       ├── service.py
│   │       └── router.py
├── migrations/
├── scripts/
│   ├── ingest_all_pages.py
│   ├── ingest_category.py
│   ├── rebuild_embeddings.py
│   └── reset_database.py
├── tests/
├── docs/
│   ├── architecture.md
│   ├── ingestion.md
│   ├── rag.md
│   ├── database.md
│   ├── coding-standards.md
│   ├── ai-development-rules.md
│   └── production-readiness.md
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── .env.example
└── README.md
4. Banco de dados
Tabelas principais
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE wiki_pages (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  namespace INTEGER NOT NULL DEFAULT 0,
  page_id INTEGER,
  raw_html TEXT,
  clean_text TEXT,
  content_hash TEXT NOT NULL,
  last_ingested_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

CREATE TABLE wiki_categories (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL
);

CREATE TABLE wiki_page_categories (
  page_id UUID REFERENCES wiki_pages(id) ON DELETE CASCADE,
  category_id UUID REFERENCES wiki_categories(id) ON DELETE CASCADE,
  PRIMARY KEY (page_id, category_id)
);

CREATE TABLE wiki_chunks (
  id UUID PRIMARY KEY,
  page_id UUID NOT NULL REFERENCES wiki_pages(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  heading TEXT,
  content TEXT NOT NULL,
  token_count INTEGER,
  embedding VECTOR(1536),
  created_at TIMESTAMP NOT NULL,
  UNIQUE(page_id, chunk_index)
);

CREATE TABLE ingestion_runs (
  id UUID PRIMARY KEY,
  status TEXT NOT NULL,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  pages_found INTEGER DEFAULT 0,
  pages_ingested INTEGER DEFAULT 0,
  pages_failed INTEGER DEFAULT 0,
  error_message TEXT
);
Índices
CREATE INDEX idx_wiki_pages_title ON wiki_pages(title);
CREATE INDEX idx_wiki_chunks_page_id ON wiki_chunks(page_id);
CREATE INDEX idx_wiki_chunks_embedding 
ON wiki_chunks USING ivfflat (embedding vector_cosine_ops);
5. Fluxo de ingestão
Pipeline
1. listar páginas pela API MediaWiki
2. filtrar namespaces irrelevantes
3. baixar conteúdo da página
4. limpar HTML
5. gerar hash do conteúdo
6. comparar com hash salvo
7. se mudou, atualizar página
8. quebrar texto em chunks
9. gerar embeddings
10. salvar chunks no banco
Regra importante

Nunca gere embeddings antes de limpar e chunkar o texto.

Fluxo certo:

HTML bruto
→ texto limpo
→ chunks
→ embeddings
→ banco

Fluxo errado:

HTML bruto
→ embeddings
6. Cliente da MediaWiki

Arquivo:

app/modules/ingestion/mediawiki_client.py

Responsabilidades:

- listar todas as páginas
- buscar página por título
- listar categorias
- listar membros de categoria
- lidar com paginação "continue"
- aplicar rate limit
- retry com backoff

Regras:

- nunca fazer scraping agressivo
- usar User-Agent identificável
- respeitar paginação da API
- limitar concorrência
- salvar falhas para retry

Exemplo de config:

MEDIAWIKI_API_URL = "https://deepwoken.fandom.com/api.php"
CRAWLER_USER_AGENT = "DeepwokenRAGBot/0.1"
CRAWLER_DELAY_SECONDS = 0.5
CRAWLER_MAX_RETRIES = 3
7. Limpeza do conteúdo

Arquivo:

app/modules/ingestion/cleaner.py

Remover:

- scripts
- estilos
- tabelas de navegação
- ads
- menus laterais
- rodapé
- comentários
- elementos vazios

Preservar:

- título
- subtítulos
- parágrafos
- listas
- tabelas úteis quando forem conteúdo real
- links internos úteis

Regra crítica: não apagar tabelas automaticamente sem avaliar. Em wiki de jogo, muita informação importante fica em tabela.

Melhor abordagem:

fase 1: manter tabelas como texto
fase 2: extrair tabelas estruturadas
fase 3: normalizar entidades específicas
8. Estratégia de chunks

Chunk ideal:

500 a 900 tokens por chunk
overlap de 80 a 120 tokens
preservar heading
preservar título da página

Formato interno do chunk:

Page: Shrine of Order
Section: Usage

<conteúdo do trecho>

Não faça chunk cego a cada N caracteres. Use hierarquia:

H1 página
→ H2 seção
→ H3 subseção
→ parágrafos
9. RAG
Fluxo de pergunta
POST /api/rag/ask

body:
{
  "question": "what is the best oath for shadowcast?",
  "top_k": 8
}

Processo:

1. gerar embedding da pergunta
2. buscar chunks similares no pgvector
3. aplicar filtro opcional por categoria
4. montar contexto
5. enviar para IA
6. retornar resposta + fontes

Resposta esperada:

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
Regra de ouro

A IA deve responder apenas com base no contexto recuperado.

Prompt base:

Você é um assistente especializado em Deepwoken.

Responda usando apenas as informações do CONTEXTO.
Se a resposta não estiver no CONTEXTO, diga:
"não encontrei essa informação na base atual."

Sempre cite as páginas usadas.
Não invente builds, números, talentos, requisitos ou mecânicas.
Não use conhecimento externo.
10. Endpoints do backend
Wiki
GET /api/wiki/pages
GET /api/wiki/pages/{id}
GET /api/wiki/search?query=
GET /api/wiki/categories
GET /api/wiki/categories/{name}/pages
Ingestão
POST /api/ingestion/run
POST /api/ingestion/pages/{title}
POST /api/ingestion/category/{category}
GET /api/ingestion/runs
GET /api/ingestion/runs/{id}
RAG
POST /api/rag/ask
POST /api/rag/search

Separação importante:

/rag/search = só busca trechos
/rag/ask = busca + IA

Isso facilita debug.

11. Metodologia de desenvolvimento

Use entregas em fases.

Fase 0 — Fundação

Objetivo: projeto rodando limpo.

Tarefas:

- criar repo
- configurar FastAPI
- configurar PostgreSQL
- configurar pgvector
- configurar SQLAlchemy
- configurar Alembic
- criar docker-compose local
- criar .env.example
- configurar Ruff, Black, Mypy e Pytest

Critério de pronto:

- app sobe
- banco sobe
- migration roda
- teste mínimo passa
Fase 1 — Coleta

Objetivo: listar e salvar páginas.

Tarefas:

- criar MediaWikiClient
- implementar list_all_pages
- implementar get_page_html
- lidar com paginação
- salvar wiki_pages
- criar script ingest_all_pages.py

Critério de pronto:

- consegue salvar pelo menos 100 páginas
- não duplica páginas
- falhas são logadas
Fase 2 — Limpeza

Objetivo: transformar HTML em texto útil.

Tarefas:

- criar cleaner
- remover ruído
- preservar headings
- preservar listas
- preservar tabelas como markdown/texto
- salvar clean_text
- calcular content_hash

Critério de pronto:

- página salva com texto legível
- conteúdo inútil reduzido
- hash evita reprocessamento desnecessário
Fase 3 — Chunking

Objetivo: quebrar conteúdo para busca.

Tarefas:

- criar chunker
- chunk por seção
- overlap controlado
- salvar wiki_chunks
- reprocessar chunks quando página mudar

Critério de pronto:

- cada página possui chunks
- chunks mantêm referência à página
- chunks não ficam gigantes nem minúsculos
Fase 4 — Embeddings

Objetivo: habilitar busca semântica.

Tarefas:

- criar embedder
- gerar embedding por chunk
- salvar no pgvector
- criar índice vetorial
- criar busca top_k

Critério de pronto:

- pergunta retorna chunks relevantes
- busca por significado funciona melhor que LIKE
Fase 5 — RAG

Objetivo: responder com IA.

Tarefas:

- criar retriever
- criar prompt fixo
- criar RagService
- criar endpoint /api/rag/ask
- retornar fontes
- impedir resposta sem contexto

Critério de pronto:

- resposta tem fontes
- IA admite quando não sabe
- não inventa dado ausente
Fase 6 — Hardening local antes de prod

Objetivo: deixar pronto para produção, sem fazer deploy.

Tarefas:

- logs estruturados
- tratamento de erro
- rate limit interno do crawler
- testes unitários
- testes de integração
- documentação completa
- revisão de segurança
- checklist de produção

Critério de pronto:

- projeto documentado
- pipeline reproduzível
- comandos claros
- pronto para deploy/prod
12. Boas práticas de código
Regras obrigatórias
- nenhuma regra de negócio dentro do router
- router chama service
- service chama repository
- repository acessa banco
- client externo isolado em classe própria
- configs só via Pydantic Settings
- nunca hardcodar API key
- logs sem dados sensíveis
- funções pequenas
- nomes explícitos
Padrão de camadas
router → service → repository → database

Errado:

@router.post("/ask")
def ask():
    # busca no banco
    # chama OpenAI
    # monta prompt
    # salva log

Certo:

@router.post("/ask")
def ask(payload: AskRequest, service: RagService = Depends()):
    return service.ask(payload)
13. Boas práticas de arquitetura
Separar ingestão de consulta

Ingestão é pipeline pesado.

Consulta é operação rápida.

Não misture os dois.

ingestion/
rag/
wiki/
Idempotência

Rodar ingestão duas vezes não pode duplicar dados.

Use:

title UNIQUE
content_hash
ON CONFLICT UPDATE
Observabilidade

Logar:

- início da ingestão
- páginas encontradas
- páginas processadas
- páginas puladas por hash igual
- páginas com erro
- tempo total
Controle de alucinação

Toda resposta da IA deve conter:

- answer
- sources
- confidence opcional

Se não houver fontes:

não responder como certeza
14. Documentação obrigatória
README.md

Deve conter:

- objetivo do projeto
- stack
- como rodar local
- como configurar .env
- como rodar migrations
- como ingerir páginas
- como fazer pergunta
- comandos úteis
docs/architecture.md

Deve conter:

- desenho da arquitetura
- explicação das camadas
- fluxo de ingestão
- fluxo RAG
- decisões técnicas
docs/ingestion.md

Deve conter:

- como a MediaWiki API é usada
- endpoints da API externa
- paginação
- rate limit
- limpeza
- chunking
- reprocessamento
docs/rag.md

Deve conter:

- como funciona a busca
- como o prompt é montado
- regras anti-alucinação
- formato da resposta
docs/database.md

Deve conter:

- modelo das tabelas
- índices
- relacionamento
- migrations
docs/coding-standards.md

Deve conter:

- padrão de pastas
- padrão de nomes
- padrão de services
- padrão de repositories
- padrão de testes
docs/ai-development-rules.md

Esse é o arquivo mais importante para evitar desvio de rota.

Conteúdo mínimo:

# Regras para IA desenvolvedora

1. Não alterar arquitetura sem atualizar docs/architecture.md.
2. Não colocar regra de negócio em routers.
3. Não chamar banco diretamente fora de repositories.
4. Não chamar API externa fora de clients.
5. Não criar nova dependência sem justificar no README.
6. Não remover testes existentes.
7. Não criar endpoints sem schemas de entrada/saída.
8. Não responder perguntas sem fontes no RAG.
9. Não gerar embeddings de HTML bruto.
10. Não misturar ingestão com pergunta do usuário.
11. Não hardcodar secrets.
12. Não ignorar migrations.
13. Não fazer scraping agressivo.
14. Não usar conhecimento externo na resposta da IA.
15. Se faltar informação, retornar que não foi encontrado na base.
docs/production-readiness.md

A documentação termina aqui.

Deve conter checklist final:

- variáveis de ambiente revisadas
- migrations testadas
- banco com pgvector habilitado
- logs configurados
- rate limit configurado
- ingestão testada
- backup planejado
- endpoints revisados
- prompt anti-alucinação validado
- testes passando
- pronto para deploy/prod
15. Ordem exata de execução
1. criar repo
2. criar estrutura de pastas
3. configurar pyproject.toml
4. subir PostgreSQL + pgvector local
5. configurar FastAPI
6. configurar SQLAlchemy
7. configurar Alembic
8. criar migrations iniciais
9. implementar MediaWikiClient
10. implementar ingestão de páginas
11. implementar limpeza
12. implementar chunking
13. implementar embeddings
14. implementar busca vetorial
15. implementar RAG
16. implementar endpoints
17. escrever testes
18. escrever documentação
19. revisar regras para IA
20. finalizar production-readiness.md
16. Minha recomendação final

Faça primeiro um MVP com:

FastAPI
PostgreSQL
pgvector
MediaWiki API
Nvidia API, OpenAI ou alguma coisa que seja sustentavel para muitos anos de graça.

Não comece por interface, bot do Discord ou deploy. O núcleo do produto é:

wiki → banco → busca → resposta com fonte

Quando isso estiver sólido, o resto vira camada em cima.
o projeto deve ser inteiramente compativel com a rede docker
