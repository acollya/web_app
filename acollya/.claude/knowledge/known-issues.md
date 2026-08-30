# Known Issues & Gotchas

_Agentes: ao resolver um bug, mover de "Ativos" para "Resolvidos" com a data e o fix._

---

## Bugs Ativos

| # | Bug | Área | Prioridade |
|---|-----|------|-----------|
| 1 | `expo-haptics` não confirmado instalado — verificar `package.json` antes de usar | Mobile | Média |
| 2 | `expo-blur` não confirmado instalado — verificar `package.json` antes de usar | Mobile | Baixa |
| 3 | EAS dev client desatualizado — mudanças mobile desde o último build não estão no dispositivo | Mobile/Build | Alta |
| 4 | RevenueCat products `acollya_essencial_monthly` e `acollya_completo_monthly` ainda não criados no dashboard | IAP | Alta (bloqueio de produção) |

---

## Riscos de Regressão — NÃO QUEBRAR

Esses itens já quebraram o app antes ou têm invariantes críticas.

### SSE Streaming (CRÍTICO)
- Protocolo `delta/done/error` deve ser mantido — qualquer mudança em `chat.py` quebra o mobile
- Ver contratos completos em `contracts.md`
- Nunca alterar o tipo de evento ou a estrutura do payload sem atualizar o mobile simultaneamente

### Prompt Caching (CRÍTICO)
- System prompt **precisa ter >1024 tokens** para qualificar para caching
- Nunca reduzir o system prompt abaixo disso sem medir impacto de custo

### Crisis Detection (CRÍTICO)
- Regex síncrono, roda **ANTES** do LLM — não introduzir I/O, await, ou banco de dados nesse path
- Localização: `app/core/crisis_detector.py`

### Background Tasks (IMPORTANTE)
- `embed_and_store()` e `extract_and_upsert_facts()` são fire-and-forget
- Erros **devem ser silenciosos** — nunca deixar exceção vazar para o fluxo de chat

### React Rules of Hooks (IMPORTANTE)
- Hooks SEMPRE antes de qualquer early return
- Falha anterior: `useOnboardingChecklist()` estava em linha 182, após early return em linha 174

### Módulos nativos novos — require NUNCA no top-level (CRÍTICO — incidente 2026-08-29)
- **Regra**: qualquer lib nativa nova (fora do dev client atual) só pode ser
  requerida DENTRO da função que a usa, com try/catch. `require` no top-level de
  um módulo importado pela navegação executa no BOOT — a falha derruba TODAS as
  telas, não só a feature (todas as telas são importadas estaticamente, sem lazy).
- **Incidente**: `attachmentService.ts` fez `require('expo-image-picker')` no
  top-level → app crashou no boot inteiro → iterações de Fast Refresh sobre a
  árvore crashada deixaram a sessão JS do aparelho corrompida (telas nativas
  fantasma do react-native-screens): "histórico abria humor", voltar caía em
  pilhas antigas, chat/programas não abriam — com o código no disco já correto.
- **Recuperação após janela de boot-crash**: matar o Metro, `rm -rf $TMPDIR/metro-*
  node_modules/.cache`, `npx expo start --dev-client --clear`, e FORCE-QUIT do
  app no aparelho (remover do app switcher) + cold start. Reload simples NÃO
  basta — a hierarquia nativa contaminada sobrevive ao reload.
- Precedente correto: `iapService.ts` (mas só porque nada de navegação o importa
  no boot — não confiar nesse acaso; requires sempre dentro das funções).

### AppState reset (política mudada em 2026-08-29)
- `App.tsx`: reset para Home ao retomar só acontece após background REAL > 5 min.
  Blips de `inactive` (prompt de permissão, Control Center, notificação) e
  backgrounds curtos (pickers de galeria/câmera/documento do chat) NÃO resetam.
- NÃO voltar ao comportamento antigo (reset em qualquer retomada): destruía o
  fluxo de anexos do chat e qualquer navegação em andamento.

### Port 5432 (CONFIGURAÇÃO LOCAL)
- Acollya postgres usa **porta 5433** (não 5432) devido a conflito com outro container
- `.env` deve ter `DB_PORT=5433`
- Lambda em produção usa 5432 via RDS diretamente — não há conflito lá

### Python version (CONFIGURAÇÃO LOCAL)
- **Python 3.12** para o venv — psycopg2-binary não tem wheel para Python 3.14
- Usar `/opt/homebrew/bin/python3.12` ao criar venv

### Google OAuth / RevenueCat — Expo Go
- **Quebra by design** no Expo Go
- Google OAuth requer custom URL scheme em `Info.plist` (apenas dev client)
- RevenueCat requer módulo nativo (apenas dev client)
- Usar sempre `eas build --profile development`

### react-native-purchases
- Import estático quebra o Expo Go
- Solução: lazy `require()` em `iapService.ts` — **não reverter para import estático**

---

## Resolvidos (Histórico)

| Data | Bug | Fix | Arquivo |
|------|-----|-----|---------|
| 2026-07 | Rules of Hooks crash — `useOnboardingChecklist()` após early return | Movido para antes do `if (loading) return` | `HomeScreen.tsx:136` |
| 2026-07 | Port 5432 conflito com `product_search-postgres-1` | docker-compose mapeado para `5433:5432` | `docker-compose.yml` |
| 2026-07 | psycopg2-binary falha no Python 3.14 | Venv criado com Python 3.12 | `venv/` |
| 2026-07 | Google OAuth quebrado no Expo Go | Migrado para dev client build | `eas.json` |
| 2026-07 | `react-native-purchases` crash no Expo Go | Lazy `require()` no iapService | `services/iapService.ts` |
| 2026-07 | Mensagens de erro de assinatura em inglês | Traduzidas para PT-BR | `core/exceptions.py` |
| 2026-07 | MoodHistory abria segunda instância de MoodCheckin | Nav guard via `state.routes.some()` | `MoodHistoryScreen.tsx` |
| 2026-07 | Ícone de coração desalinhado no header | `alignItems: 'flex-start'` no greetingRow | `HomeScreen.tsx` |
| 2026-07 | plan_code=1 existentes seriam "downgraded" para Essencial | Migration 019 faz upgrade para plan_code=2 | `migrations/019_*.py` |
| 2026-07-27 | Telas Humor/Chat com "verifique a internet" — na verdade HTTP 402: `require_premium` (modelo binário antigo) bloqueava chat/mood inteiros pós-trial, contradizendo o 3-tier; e ignorava `plan_code`/`subscription_status` do User (simulação via DB não funcionava) | (1) `require_premium` agora honra `user.is_premium` (fast path); (2) mood create/list e chat trocados para `get_current_user` — rate limiter 3-tier controla o uso; insights de mood continuam premium; (3) `get_status` com fallback para colunas do User quando não há linha em `subscriptions` | `dependencies.py`, `mood.py`, `chat.py`, `subscription_service.py` |
| 2026-07-27 | IP do Mac mudava via DHCP e quebrava o app (`.env` com IP fixo) | `EXPO_PUBLIC_API_URL` usa mDNS `http://MacBook-Pro-de-Kadu.local:8000` — independe do IP | `.env`, `eas.json` |
| 2026-08-01 | `user_sessions` nunca era preenchida (modelo existia, gravação não conectada) | `record_session_login/logout` no auth_service — best-effort em register/login/google/apple + carimbo `logout_at` no logout | `auth_service.py`, `endpoints/auth.py` |
| 2026-08-01 | `ai_response_cache` morta desde o schema inicial (zero referências no código) | DROP na migration 020 | `migrations/020_*.py` |
| 2026-08-01 | `programs`/`chapters` com PK slug de texto (`ansiedade-2-1`) | Migration 021: id → UUID, slug preservado em coluna própria; `program_progress` remapeado; ver ADR-009 | `migrations/021_*.py`, `models/program.py`, `program_service.py` |

### REGRA DE PRODUTO — Sugestão de programas no chat (Kadu, 2026-08-27)
O RAG do chat SÓ sugere programas SEM custo para o usuário (`min_plan_code <= plano efetivo`).
Programas pagos/bloqueados NUNCA entram no contexto da conversa — upsell é papel das telas
(get_recommended do Home pode mostrar tudo). Implementado no bloco de catálogo do rag_service
com threshold próprio `_MAX_DISTANCE_CATALOG=0.60` (calibrado: on-topic 0.52–0.57, neutro 0.68+).

### Bug crítico resolvido — Decimal × float no retrieve_context (2026-08-27)
`rrf_score`/`distance` chegavam como `Decimal` do asyncpg; qualquer match no histórico pessoal
explodia o retrieve_context INTEIRO silenciosamente (RAG retornava vazio — memória "morta" sem
sintoma). Pré-existente desde o hybrid search. Fix: `float()` em todas as multiplicações de score.
⚠️ Padrão a vigiar: valores numéricos vindos de SQL bruto via asyncpg → sempre coagir com float().

### Simulação de assinante para testes (dev)
```sql
UPDATE users SET plan_code = 2, subscription_status = 'active' WHERE email = '...';
```
Funciona de ponta a ponta após o fix do `require_premium` (2026-07-27). Logout/login no app para recarregar.
