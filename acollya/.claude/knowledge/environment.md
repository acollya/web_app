# Environment Reference

_Referência de configuração local e de produção. Nunca commitar valores reais de secrets._

---

## Backend — Local

### Como iniciar

```bash
# 1. Subir serviços de infra
cd acollya-backend
docker-compose up -d
# Postgres disponível em localhost:5433 (NÃO 5432 — conflito com outro container)
# Redis disponível em localhost:6379

# 2. Ativar venv Python 3.12
source venv/bin/activate
# Se venv não existe: /opt/homebrew/bin/python3.12 -m venv venv

# 3. Instalar dependências (se necessário)
pip install -r requirements.txt

# 4. Rodar migrations
alembic upgrade head
# HEAD atual: 019_plan_code_completo

# 5. Iniciar servidor
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
# --host 0.0.0.0 obrigatório para o iPhone alcançar o backend pela LAN
```

### Variáveis de ambiente (.env)

```env
# Database
DB_HOST=localhost
DB_PORT=5433          # ATENÇÃO: 5433, não 5432
DB_NAME=acollya
DB_USER=acollya_admin
DB_PASSWORD=localdev

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_TLS=false

# Auth
JWT_ALGORITHM=RS256
JWT_PRIVATE_KEY=...   # RSA private key (PEM)
JWT_PUBLIC_KEY=...    # RSA public key (PEM)
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
GOOGLE_CLIENT_IDS=...  # comma-separated

# AI Providers
ANTHROPIC_API_KEY=...
ANTHROPIC_CHAT_MODEL=claude-haiku-4-5-20251001
OPENAI_API_KEY=...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# RevenueCat
REVENUE_CAT_WEBHOOK_SECRET=...

# App
STAGE=dev
TRIAL_DAYS=7
FREE_CHAT_MESSAGES_PER_DAY=10
ESSENCIAL_CHAT_MESSAGES_PER_DAY=20
PREMIUM_CHAT_MESSAGES_PER_DAY=9999
```

### Portas locais

| Serviço | Porta | Observação |
|---------|-------|-----------|
| FastAPI | 8000 | `uvicorn app.main:app --reload` |
| PostgreSQL | 5433 | host port (container interno: 5432) |
| Redis | 6379 | padrão |

---

## Mobile — Local

### API URL (`.env` + eas.json profile development)

```
EXPO_PUBLIC_API_URL=http://MacBook-Pro-de-Kadu.local:8000/api/v1
```

**mDNS `.local`** — resolve o IP da Mac na LAN automaticamente; imune a mudanças
de IP do DHCP (que já quebraram o app 2×). Não voltar a usar IP fixo.
**Porta:** `8000` (FastAPI). Mudança no `.env` exige restart do Metro (`--clear`).

⚠️ **`.env` é NÃO-VERSIONADO e é ponto único de falha (incidente 2026-08-30)**:
sem ele, `app.config.ts` cai no fallback `http://localhost:8000` — que no APARELHO
aponta para o próprio iPhone → **TODAS as telas falham** ("Não foi possível
carregar", "Nenhum programa disponível", recomendações sumidas), com backend e
código 100% saudáveis. Essa assinatura de sintomas (todas as telas com erro de
carregamento ao mesmo tempo) → **verificar PRIMEIRO se `.env` existe** antes de
qualquer diagnóstico de código/API/banco:
`ls acollya-mobile/.env` → se ausente, recriar de `.env.example` trocando a URL
para a de mDNS acima e reiniciar o Metro com `--clear`.
Verificação fim-a-fim sem aparelho:
`curl -s -H "expo-platform: ios" localhost:8081/ | jq '..|.apiUrl? // empty'`
(a URL viaja no MANIFEST do Expo, não dentro do bundle JS).

### Build type

```bash
# Dev client (NÃO Expo Go — requer para Google OAuth e RevenueCat)
eas build --profile development --platform ios

# Depois de instalar no dispositivo via TestFlight/link:
npx expo start --dev-client
```

**Por quê não Expo Go:**
- Google OAuth requer custom URL scheme registrado no `Info.plist`
- RevenueCat requer módulo nativo compilado

---

## Produção (AWS)

| Recurso | Serviço AWS | Região |
|---------|------------|--------|
| API | Lambda (FastAPI via Mangum) | `sa-east-1` |
| Banco de dados | RDS PostgreSQL (pgvector) | `sa-east-1` |
| Cache | ElastiCache Redis | `sa-east-1` |
| Secrets | Secrets Manager | `sa-east-1` |
| Storage | S3 | `sa-east-1` |

**Todos em `sa-east-1` (São Paulo)** — requisito LGPD para dados de saúde em território nacional.

Secrets Manager ARNs (dev):
- `acollya/dev/jwt` → private_key, public_key, google_client_ids
- `acollya/dev/openai` → api_key
- `acollya/dev/anthropic` → api_key

---

## Estrutura de branches

| Branch | Ambiente | Deploy |
|--------|----------|--------|
| `main` | dev/staging | manual via CDK |
| `release/*` | produção | CDK pipeline |

---

## ⚠️ Estrutura de repositórios (dual-tracking do backend)

| Diretório | Repo GitHub | Rastreamento |
|-----------|-------------|--------------|
| `web_app/` (raiz) | `acollya/web_app` | monorepo — rastreia acollya-backend como ARQUIVOS diretos |
| `acollya/acollya-mobile/` | `acollya/acollya-mobile` | submódulo registrado no .gitmodules |
| `acollya/acollya-backend/` | `acollya/acollya-backend` | **repo aninhado NÃO-submódulo** — tem .git próprio E os arquivos são rastreados no web_app |

**Consequência:** todo trabalho de backend commitado no web_app NÃO chega sozinho ao
repo standalone `acollya-backend`. Fluxo de sync obrigatório ao fechar uma frente:
`cd acollya/acollya-backend` → branch → commit de sync → PR → merge (padrão
"sync from web_app" no histórico). Esquecer isso deixa o repo standalone meses
defasado (aconteceu: maio→agosto/2026).

### ⚠️ iCloud Drive × node_modules (incidente 2026-08-30)

O projeto vive em `~/Documents` → **iCloud "Desktop & Documents" sincroniza tudo**
e, durante churn pesado (npm ci/install), cria cópias de conflito `nome 2` /
`nome 2.ext`. Foram removidos **972 itens** duplicados de
`acollya-mobile/node_modules` + 5 cópias no `src/` + `.git/index 2`.

**Assinatura**: erro `TS2688: Cannot find type definition file for 'node 2'`
pendurado no tsconfig.json, ou qualquer arquivo `* 2.*` aparecendo sozinho.

**Limpeza**:
`find node_modules \( -name "* 2.*" -o -name "* 2" \) -exec rm -rf {} +`

**Prevenção (ação do Kadu, recomendada)**: tirar a pasta de dev do alcance do
iCloud — mover `~/Documents/VsCode` para `~/dev` (exige recriar o venv do
backend, que tem paths absolutos) OU desativar "Desktop & Documents" no iCloud.
Enquanto isso não acontecer, o problema PODE VOLTAR a cada npm install grande.
