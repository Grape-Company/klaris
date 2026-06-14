# Deploy na DigitalOcean

Este projeto deve ser publicado na DigitalOcean com Droplet + Docker Compose quando a prioridade for compatibilidade total com rede Docker. Nesse modelo, a API conversa com o PostgreSQL pelo hostname interno `db`, sem expor o banco publicamente.

## Arquivos usados

- `Dockerfile`
- `docker-compose.digitalocean.yml`
- `.env`, criado a partir de `.env.digitalocean.example`

## 1. Criar a Droplet

Crie uma Droplet Ubuntu LTS na DigitalOcean.

Recomendação inicial:

- 1 vCPU / 1 GB RAM para teste pequeno
- 1 vCPU / 2 GB RAM ou mais para ingestão real
- região próxima dos usuários
- autenticação por SSH key

## 2. Acessar o servidor

```bash
ssh root@IP_DA_DROPLET
```

Atualize o sistema:

```bash
apt update
apt upgrade -y
```

## 3. Instalar Docker

```bash
apt install -y ca-certificates curl gnupg git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Confirme:

```bash
docker --version
docker compose version
```

## 4. Enviar o projeto para o servidor

Opção simples usando Git:

```bash
git clone <URL_DO_REPOSITORIO> /opt/deepwoken-rag
cd /opt/deepwoken-rag
```

## 5. Configurar variáveis de ambiente

```bash
cp .env.digitalocean.example .env
nano .env
```

Troque obrigatoriamente:

- `POSTGRES_PASSWORD`
- `ADMIN_API_KEY`
- `OPENAI_API_KEY`

Não commite `.env`.

## 6. Subir a aplicação

```bash
docker compose -f docker-compose.digitalocean.yml up -d --build
```

O container `app` executa `alembic upgrade head` antes de iniciar a API.

Verifique:

```bash
docker compose -f docker-compose.digitalocean.yml ps
docker compose -f docker-compose.digitalocean.yml logs -f app
```

Teste localmente no servidor:

```bash
curl http://localhost:8000/health
```

Teste de fora:

```bash
curl http://IP_DA_DROPLET:8000/health
```

Se aparecer `password authentication failed for user "deepwoken"`, o volume `pgdata` provavelmente foi criado com outra senha. O Postgres só usa `POSTGRES_PASSWORD` na primeira inicialização do volume.

Para preservar dados, volte o `.env` para a senha usada na primeira criação do banco e suba novamente:

```bash
docker compose -f docker-compose.digitalocean.yml up -d --build
```

Para ambiente novo sem dados importantes, recrie o volume:

```bash
docker compose -f docker-compose.digitalocean.yml down -v
docker compose -f docker-compose.digitalocean.yml up -d --build
```

No servidor da DigitalOcean, prefira sempre informar o arquivo de produção com `-f docker-compose.digitalocean.yml`. O comando sem `-f` usa o `docker-compose.yml` local.

## 7. Ingestão inicial

Comece pequeno:

```bash
curl -X POST http://IP_DA_DROPLET:8000/api/ingestion/run \
  -H "Content-Type: application/json" \
  -H "X-Admin-Api-Key: ADMIN_API_KEY_AQUI" \
  -d '{"namespace":0,"limit":20}'
```

Depois aumente para `100`, `500` ou mais conforme estabilidade, custo do provedor de IA e uso de CPU/RAM.

## 8. Conversar com Klaris

```bash
curl -X POST http://IP_DA_DROPLET:8000/api/klaris/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"what is Shrine of Order?","top_k":8}'
```

## 9. Firewall básico

Libere SSH e API:

```bash
ufw allow OpenSSH
ufw allow 8000/tcp
ufw enable
ufw status
```

Para produção com domínio e HTTPS, coloque Nginx/Caddy na frente e exponha apenas portas `80` e `443`.

## 10. Atualizar deploy

```bash
cd /opt/deepwoken-rag
git pull
docker compose -f docker-compose.digitalocean.yml up -d --build
```

## 11. Backup mínimo do banco

```bash
docker compose -f docker-compose.digitalocean.yml exec db pg_dump -U deepwoken deepwoken > backup.sql
```

Guarde backups fora da Droplet.
