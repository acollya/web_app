# Architecture Decision Records

_Registra decisões técnicas e de produto significativas: o QUÊ e principalmente o POR QUÊ. Impede que agentes revertam escolhas que já foram ponderadas._

---

## ADR-001: 3 tiers de plano via `plan_code` inteiro (não boolean `is_premium`)

**Data:** 2026-07  
**Status:** Ativo

**Decisão:** Usar `plan_code: int` (0/1/2) na tabela `users` para representar o plano.

**Contexto:** O sistema original usava `is_premium: bool`. A introdução de um tier intermediário ("Essencial") tornaria o boolean insuficiente.

**Por quê inteiro e não enum/string:**
- Permite range queries (`plan_code >= 1` para "qualquer plano pago")
- Migration simples para adicionar tiers futuros
- Compatível com índice B-tree

**Consequências:**
- `is_premium` property abrange plan_code 1 E 2 — não usar como proxy para "é Completo"
- Webhook RevenueCat mapeia `product_id → plan_code` via dict; fallback = 2
- Migration 019 fez upgrade de plan_code=1 existentes → 2 (nenhum pagante foi rebaixado)

---

## ADR-002: Docker host port 5433 (não 5432) para Postgres local

**Data:** 2026-07  
**Status:** Ativo

**Decisão:** `acollya-postgres` mapeado como `5433:5432` no docker-compose.yml.

**Por quê:** Conflito com `product_search-postgres-1` que já ocupava a porta 5432 do host no ambiente de desenvolvimento do Kadu.

**Consequências:**
- `.env` local usa `DB_PORT=5433`
- Lambda em produção acessa RDS diretamente na porta 5432 (sem conflito)
- Ao iniciar o backend localmente, sempre verificar que o container está na 5433

---

## ADR-003: Python 3.12 para venv local

**Data:** 2026-07  
**Status:** Ativo

**Decisão:** Criar venv com `/opt/homebrew/bin/python3.12`.

**Por quê:** `psycopg2-binary` não tem wheel compilado para Python 3.14 (versão padrão no homebrew na época). Python 3.12 tem wheel estável.

**Consequências:** Qualquer novo dev setup precisa usar Python 3.12 explicitamente.

---

## ADR-004: Trial de 7 dias, limite Free de 10 msgs/dia

**Data:** 2026-07  
**Status:** Ativo

**Decisão:** `trial_days=7` (reduzido de 14), `free_chat_messages_per_day=10` (reduzido de 20).

**Por quê:** Maior rigor no plano gratuito para aumentar pressão de conversão sem eliminar o valor percebido. 10 mensagens é suficiente para demonstrar o valor do produto em um dia de uso leve.

---

## ADR-005: Single entitlement RevenueCat ("premium") com mapeamento por product_id

**Data:** 2026-07  
**Status:** Ativo

**Decisão:** Usar um único entitlement "premium" no RevenueCat; diferenciar tier pelo `product_id` no webhook.

**Por quê:** Criar dois entitlements separados exigiria reconfigurar todo o dashboard RevenueCat e o código mobile. O mapeamento server-side via webhook é mais flexível.

**Consequências:** Qualquer novo produto de assinatura deve ser adicionado ao dict `_PRODUCT_PLAN_CODE` em `subscription_service.py`.

---

## ADR-006: Lazy require() para react-native-purchases

**Data:** 2026-07  
**Status:** Ativo

**Decisão:** `iapService.ts` usa `require()` dinâmico em vez de import estático para `react-native-purchases`.

**Por quê:** Import estático causa crash no Expo Go (módulo nativo não disponível). Lazy require permite o app funcionar no Expo Go sem RevenueCat, e carrega o módulo apenas quando necessário em dev client.

**Não reverter para import estático.**

---

## ADR-007: LGPD — Anonymization on delete (sem hard delete)

**Data:** anterior a 2026-07  
**Status:** Ativo

**Decisão:** Deleção de conta anonimiza dados em vez de deletar registros.

**Por quê:** Compliance LGPD + integridade referencial (registros de chat, mood, etc. são mantidos anonimizados para análise agregada). O usuário perde acesso; os dados não identificáveis permanecem.

**Consequências:** `user_service.py` nunca faz `DELETE FROM users`. Qualquer novo serviço que lide com deleção deve seguir o mesmo padrão.

---

## ADR-008: Nomes dos planos — "Essencial" e "Completo"

**Data:** 2026-07  
**Status:** Ativo

**Decisão:** Planos pagos chamados "Essencial" (R$39,90) e "Completo" (R$79,90).

**Rejeitados:**
- "Suporte Emocional" — conotação de intervenção em crise, pode confundir com suporte psicológico real
- "Acompanhante Pessoal" — genérico, não comunica diferença entre tiers
- "Premium" / "Pro" — genérico, não comunica valor específico

**Por quê "Essencial" e "Completo":** Comunicam claramente o que o usuário tem acesso sem fazer promessas clínicas.

---

## ADR-009: Política de IDs — UUID como PK, semântica em coluna `slug`

**Data:** 2026-08-01
**Status:** Ativo (decisão do Kadu)

**Decisão:** PKs de tabelas devem ser identificadores únicos puros (UUID). Valores legíveis/semânticos (ex: `ansiedade-2-1`, `mindfulness-iniciantes`) vivem em coluna `slug` própria com UNIQUE index.

**Aplicado em:** migration 021 — `programs` e `chapters` convertidos in-place (dados preservados); `program_progress.program_id/chapter_id` remapeados.

**Consequências:**
- Novas tabelas nascem com id UUID; conteúdo seedado ganha `slug`
- API expõe ambos (`id` para navegação, `slug` para debug/SEO)
- Mobile é agnóstico — trata IDs como strings opacas vindas da API

---

## ADR-010: Trial e acesso — gate por colunas do User, não por tabela subscriptions

**Data:** 2026-07-27
**Status:** Ativo

**Decisão:** `require_premium` checa `user.is_premium` (plan_code + subscription_status + trial) como fast path; a tabela `subscriptions` é registro do RevenueCat, não fonte primária do gate.

**Por quê:** (1) webhook atualiza as colunas do User; (2) permite concessão manual de acesso (suporte/testes) via UPDATE simples; (3) evitou o bug em que chat/mood retornavam 402 para usuário com plan_code=2.

**Consequências:** Chat e mood check-in/histórico exigem apenas autenticação (modelo 3-tier — rate limiter controla 10/20/ilimitado). Somente insights de IA permanecem atrás de `require_premium`.

---

## ADR-011: Deleção LGPD — hard-delete de conteúdo sensível (revoga parte do ADR-007)

**Data:** 2026-08-29
**Status:** Ativo (auditoria compliance-auditor)

**Decisão:** `DELETE /users/me` apaga DEFINITIVAMENTE chat (mensagens+sessões), diário,
humor, persona facts e user_sessions — conteúdo + embeddings. Preserva apenas registros
pseudônimos SEM conteúdo sensível: crisis_events (probatório, Art. 16 I + Art. 7 §3),
program_progress, appointments, subscriptions.

**Por quê:** o texto livre do usuário contém dado sensível de saúde (Art. 11) — a
pseudonimização da tabela users NÃO anonimiza esse conteúdo. Retenção para ML sem
consentimento explícito era o risco legal #1 do projeto.

**Consequências:** nenhuma retenção p/ ML (se um dia existir, exige opt-in específico +
DPIA); MyDataScreen promete exatamente o que o código faz; ADR-007 permanece válido só
para os registros não-sensíveis.

---

## ADR-012: Idade mínima 18 anos

**Data:** 2026-08-29
**Status:** Ativo — REVISITÁVEL com parecer jurídico

**Decisão:** `minimum_age_years = 18` (config). Validado no cliente (modal) e no servidor.

**Por quê:** 13 (COPPA) não tem base na LGPD. Adolescente 12-17 com dado sensível de
saúde exigiria consentimento parental verificável (Art. 14) — fluxo não implementado.
18 é a única posição defensável sem ele.

**Consequências:** público adolescente fora do produto por ora; para incluí-lo:
parecer jurídico + fluxo de consentimento parental (roadmap distante).

---

## ADR-013: Consentimento SSO — gate server-side (get_consented_user)

**Data:** 2026-08-29
**Status:** Ativo

**Decisão:** No SSO a conta nasce com terms_accepted=false; TODAS as rotas que tratam
dado sensível (chat, mood, journal, media) usam `get_consented_user` → 403 até o
usuário concluir POST /users/me/consents (termos versionados + consentimento saúde +
nascimento). require_premium herda o gate.

**Por quê:** o modal client-side era teatro — a conta existia com token válido antes
do aceite (browsewrap ≠ consentimento específico Art. 11 §1). Enforcement no servidor
fecha a janela mesmo se o app morrer no meio do fluxo.
