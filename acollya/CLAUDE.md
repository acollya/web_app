# Acollya — Instruções para Claude Code

## Visão Geral do Projeto

Acollya é um aplicativo de saúde mental que combina chat terapêutico com IA, RAG (Retrieval-Augmented Generation), análise de humor, diário e insights personalizados. Lida com dados sensíveis de saúde mental e está sujeito à LGPD.

**Stack principal:**
- Backend: FastAPI + Python + PostgreSQL (pgvector) + Redis + AWS Lambda
- Mobile: React Native + TypeScript + Expo
- AI/LLM: Anthropic Claude Haiku (chat/insights), OpenAI (embeddings, Whisper, GPT-4o-mini)
- Infra: AWS (Lambda, RDS, ElastiCache, Secrets Manager) + CDK

---

## Regras de Acionamento Automático de Subagentes

Os subagentes abaixo estão instalados em `.claude/agents/` e devem ser acionados **automaticamente** conforme o contexto do trabalho, sem necessidade de solicitação explícita do usuário.

### Backend — FastAPI / Python

**Acionar `fastapi-developer` quando:**
- Modificar qualquer arquivo em `acollya-backend/app/api/`, `acollya-backend/app/schemas/`, ou `acollya-backend/app/core/dependencies.py`
- Criar novos endpoints, routers, middlewares ou schemas Pydantic
- Trabalhar com injeção de dependência, lifespan, exception handlers

**Acionar `claude-api` quando:**
- Tocar em `acollya-backend/app/core/llm_provider.py`
- Modificar `acollya-backend/app/services/chat_service.py`
- Alterar qualquer system prompt, prompt template, ou configuração de modelo
- Ajustar parâmetros de streaming SSE, prompt caching, ou extended thinking
- Qualquer arquivo que importe `anthropic` ou `openai`

**Acionar `prompt-engineer` quando:**
- Editar `_SYSTEM_PROMPT`, `_EXTRACTION_SYSTEM_PROMPT`, `_REFLECTION_SYSTEM_PROMPT` ou qualquer string de instrução para LLM
- Avaliar qualidade de respostas do modelo ou ajustar temperatura/max_tokens
- Criar novos prompts para features de AI (novos insights, novas análises)

### RAG & Embeddings

**Acionar `llm-architect` quando:**
- Modificar `acollya-backend/app/services/rag_service.py` estruturalmente
- Propor novas fontes de dados para o RAG (além de chat_messages, journal_entries, mood_checkins)
- Mudar modelo de embedding, dimensionalidade ou estratégia de chunking
- Avaliar tradeoffs de arquitetura entre abordagens de retrieval

**Acionar `nlp-engineer` quando:**
- Ajustar threshold de similaridade coseno (atualmente 0.45)
- Modificar top-K de retrieval, estratégia de merge ou formatação do contexto RAG
- Avaliar qualidade de retrieval ou implementar reranking
- Trabalhar com lógica de `_generate_embedding()` ou `retrieve_context()`

**Acionar `database-optimizer` quando:**
- Escrever ou revisar queries que usam `<=>` (cosine distance) com pgvector
- Modificar índices IVFFlat (lists, probes) nas tabelas de embeddings
- Analisar planos de execução de queries de RAG
- Trabalhar em `acollya-backend/migrations/` relacionado a Vector columns

**Acionar `data-engineer` quando:**
- Modificar `embed_and_store()`, `extract_and_upsert_facts()` ou background tasks
- Alterar pipelines assíncronos de ingestão de dados (asyncio.create_task)
- Criar novos pipelines de embeddings ou refatorar o existente

### Banco de Dados

**Acionar `postgres-pro` quando:**
- Criar ou modificar arquivos em `acollya-backend/migrations/`
- Trabalhar com modelos ORM que têm colunas `Vector(1536)`
- Otimizar queries SQL complexas no backend
- Avaliar configurações de índice IVFFlat (lists, probes) para escala

### Mobile — React Native / Expo

**Acionar `expo-react-native-expert` quando:**
- Modificar qualquer arquivo em `acollya-mobile/src/`
- Trabalhar com `app.json`, `eas.json`, configurações de build Expo
- Implementar hooks nativos (`useAudioRecorder`, permissões de microfone)
- Lidar com navegação (`@react-navigation`), animações (`react-native-reanimated`)
- Configurar OTA updates, push notifications, ou App Store/Play Store

**Acionar `ui-ux-pro-max` quando:**
- Criar ou modificar telas em `acollya-mobile/src/screens/`
- Trabalhar com componentes visuais em `acollya-mobile/src/components/`
- Definir estilos, layouts, paleta de cores, tipografia ou fluxos de navegação
- Implementar animações, transições ou estados de UI (loading, empty, error)

**Acionar `accessibility-tester` quando:**
- Criar ou modificar telas que contenham inputs, modais, banners ou alertas
- Modificar o `CrisisBanner` ou qualquer componente relacionado a crises
- Implementar novos fluxos de onboarding ou formulários
- Revisar qualquer tela antes de considerar completa

### Qualidade & Testes

**Acionar `qa-expert` quando:**
- Finalizar qualquer nova feature ou fluxo completo
- Avaliar cobertura de testes do projeto
- Identificar riscos de qualidade em mudanças significativas
- Planejar estratégia de testes para uma área nova

**Acionar `test-automator` quando:**
- Criar ou modificar services, endpoints ou components sem teste correspondente
- Implementar novos endpoints FastAPI (gerar testes pytest + httpx)
- Criar novos componentes mobile (gerar testes Jest + Testing Library)
- Integrar testes em pipelines CI/CD

**Acionar `code-reviewer` quando:**
- Antes de qualquer merge em `main` com mudanças significativas
- Após implementar features que tocam em múltiplos arquivos
- Ao refatorar código existente de serviços críticos (chat, RAG, auth)

**Acionar `debugger` quando:**
- Reproduzir qualquer bug reportado ou comportamento inesperado
- Investigar falhas em pipeline assíncrono (asyncio, SSE, background tasks)
- Analisar erros de integração entre Lambda, RDS, Redis e APIs externas

**Acionar `error-detective` quando:**
- Analisar logs de produção ou stack traces com erros correlacionados
- Investigar falhas intermitentes em streaming SSE ou chamadas ao LLM
- Diagnosticar erros entre múltiplos serviços (Lambda → RDS → Redis → Anthropic)

**Acionar `performance-engineer` quando:**
- Modificar endpoints de streaming SSE ou lógica de streaming do LLM
- Avaliar latência de cold start Lambda ou configurações de concorrência
- Otimizar uso de cache Redis (TTL, invalidação, estratégia de chave)
- Identificar gargalos no pipeline de chat (RAG + persona + LLM)

### Segurança & Compliance

**Acionar `security-review` quando:**
- Modificar `acollya-backend/app/core/auth.py`, JWT, OAuth (Google, Apple)
- Alterar qualquer endpoint de autenticação ou autorização
- Modificar como dados de usuário são coletados, armazenados ou deletados
- Implementar novos endpoints que expõem dados sensíveis

**Acionar `compliance-auditor` quando:**
- Modificar coleta, armazenamento ou processamento de dados de saúde mental
- Alterar fluxo de deleção de conta ou exportação de dados do usuário
- Implementar novas features que envolvam dados pessoais sensíveis (LGPD)
- Antes de qualquer release que mude o modelo de dados de usuário

### Infraestrutura & Arquitetura

**Acionar `cloud-architect` quando:**
- Modificar qualquer arquivo em `acollya-infra/` (CDK stacks)
- Avaliar configurações de Lambda (memória, timeout, concorrência)
- Propor mudanças na topologia AWS (novos serviços, regiões, networking)
- Revisar configurações de RDS, ElastiCache ou Secrets Manager

**Acionar `architect-reviewer` quando:**
- Propor mudanças estruturais significativas (nova fonte RAG, novo modelo LLM, nova tabela de embeddings)
- Avaliar tradeoffs entre abordagens antes de implementar
- Revisar decisões de design que afetam múltiplas camadas do sistema
- Antes de iniciar qualquer refatoração de serviço core (chat_service, rag_service)

**Acionar `ai-engineer` quando:**
- Propor novas capacidades de AI para o produto (ex: análise de padrões, novos tipos de insight)
- Avaliar migração de modelo ou troca de provedor LLM
- Desenhar novos pipelines de AI end-to-end
- Integrar novas fontes de dados ao sistema de personalização

### Documentação

**Acionar `api-documenter` quando:**
- Adicionar novos endpoints à API
- Modificar contratos de request/response existentes
- Antes de qualquer integração com parceiros externos
- Ao atualizar schemas Pydantic que fazem parte da API pública

### Visão de Negócio & Produto

**Acionar `ux-researcher` quando:**
- Antes de criar ou redesenhar qualquer tela ou fluxo que afete experiência do usuário
- Ao definir ou revisar o fluxo de onboarding (qualquer tela em `acollya-mobile/src/screens/auth/`)
- Ao discutir personas, segmentos de usuário ou proposta de valor para um público específico
- Antes de qualquer decisão de UX que impacte fluxos core (chat, check-in de humor, diário)
- Ao planejar pesquisa para validar hipóteses sobre comportamento ou preferências dos usuários

**Acionar `legal-advisor` quando:**
- Modificar Termos de Uso, Política de Privacidade ou qualquer documento legal do app
- Adicionar novos campos de coleta de dados no modelo de usuário (`acollya-backend/app/models/`)
- Implementar ou alterar fluxos de consentimento LGPD ou deleção de conta
- Integrar novos serviços terceiros que processem dados pessoais dos usuários
- Qualquer mudança na lógica de retenção, exportação ou exclusão de dados

**Acionar `product-manager` quando:**
- Definir novas features ou avaliar requests de funcionalidade para o roadmap
- Priorizar itens no backlog ou decidir o que entra em um sprint
- Avaliar estratégia de lançamento, go-to-market ou posicionamento competitivo
- Definir métricas de sucesso (KPIs, OKRs) para novas funcionalidades ou releases
- Fazer tradeoffs entre valor para o usuário e complexidade técnica de implementação

**Acionar `customer-success-manager` quando:**
- Projetar ou revisar o fluxo de onboarding in-app e estratégia de ativação de usuários
- Trabalhar em estratégias de push notifications, re-engajamento ou win-back
- Definir ou revisar o modelo de assinatura/freemium e fluxos de upgrade para premium
- Implementar coleta de NPS, feedback in-app ou pesquisas de satisfação
- Analisar métricas de retenção, churn ou adoção de features no produto

**Acionar `content-marketer` quando:**
- Escrever ou revisar a descrição do app na App Store / Google Play e screenshots
- Criar conteúdo para landing page, redes sociais ou e-mail marketing do Acollya
- Escrever copy para push notifications, e-mails transacionais ou sequências de onboarding
- Definir ou revisar o tom de voz e brand voice em comunicações externas
- Criar conteúdo educativo sobre saúde mental para aquisição orgânica ou blog

**Acionar `technical-writer` quando:**
- Adicionar novos endpoints à API que exijam documentação para parceiros ou integradores
- Criar ou atualizar guias de integração para parceiros (clínicas, planos de saúde)
- Documentar novas features para usuários finais ou equipe interna
- Criar changelog, release notes ou documentação de SDK
- Revisar documentação existente para clareza, completude ou precisão técnica

---

## Regras Gerais

1. **Sempre usar `simplify`** após finalizar qualquer implementação — revisar código para reuso, qualidade e eficiência.
2. **Sempre usar `code-reviewer`** antes de sugerir commit em `main` com mudanças em serviços críticos.
3. **Nunca fazer diagnóstico, prescrever medicação** — verificar que o sistema prompt do Acollya mantém esse limite em qualquer alteração de prompt.
4. **LGPD first** — qualquer feature nova que envolva dado pessoal deve passar por `compliance-auditor` antes de ser considerada completa.
5. **Crisis detection** — ao modificar `crisis_detector.py` ou o fluxo SSE, sempre acionar `qa-expert` para validar os padrões regex e o fluxo de CVV.
6. **Embeddings são críticos** — mudanças em threshold, modelo ou dimensão de embedding exigem `llm-architect` + `database-optimizer` antes de aplicar.

---

## Estrutura do Projeto

```
acollya/
├── acollya-backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # FastAPI routers
│   │   ├── core/                # llm_provider, crisis_detector, auth, rate_limiter
│   │   ├── models/              # SQLAlchemy ORM (Vector columns)
│   │   ├── schemas/             # Pydantic schemas
│   │   └── services/            # chat, rag, persona, journal, mood
│   └── migrations/              # Alembic (pgvector, IVFFlat indexes)
├── acollya-mobile/
│   └── src/
│       ├── screens/             # ChatScreen, JournalScreen, MoodCheckinScreen
│       ├── components/          # VoiceInputButton, CrisisBanner
│       ├── services/            # chatService (SSE), API clients
│       └── hooks/               # useAudioRecorder, useAuth
├── acollya-infra/               # AWS CDK stacks
└── .claude/
    └── agents/                  # Subagentes instalados
```

---

## Contexto Técnico Importante

- **Streaming SSE:** protocolo `delta/done/error` — qualquer mudança deve manter compatibilidade com o frontend
- **Prompt caching:** system prompt precisa ter >1024 tokens para qualificar — não reduzir abaixo disso
- **IVFFlat lists=50:** adequado até ~500k registros; escalar para lists=100+ com >100k usuários
- **Crisis detection:** regex síncrono, roda ANTES do LLM — não introduzir I/O nesse path
- **Background tasks:** `embed_and_store()` e `extract_and_upsert_facts()` são fire-and-forget — erros devem ser silenciosos (não quebrar o fluxo de chat)
- **LGPD:** dados de saúde mental são dados sensíveis categoria especial — requerem consentimento explícito e direito de deleção garantido
