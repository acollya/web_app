# Implementation Status

_Atualizado em: 2026-08-01. Agentes: sempre atualizar este arquivo ao concluir uma feature._

---

## Backend — Alembic HEAD: `021_programs_chapters_uuid`

| Feature | Status | Arquivo | Notas |
|---------|--------|---------|-------|
| Auth JWT RS256 (15min/30d refresh) | ✅ Completo | `core/auth.py` | |
| Google OAuth (verify ID token) | ✅ Completo | `core/auth.py` | |
| Apple Sign-in | ✅ Completo | `core/auth.py` | |
| Rate limiter sliding-window Redis | ✅ Completo | `core/rate_limiter.py` | |
| 3-tier rate limit (10/20/9999 msgs/dia) | ✅ Completo | `api/v1/endpoints/chat.py` | plan_code 0/1/2 |
| Plano Free: 10 msgs/dia, 7 dias trial | ✅ Completo | `config.py` | era 20 msgs antes |
| Plano Essencial: 20 msgs/dia | ✅ Completo | `config.py` | plan_code=1 |
| Plano Completo: ilimitado + voz | ✅ Completo | `config.py` | plan_code=2 |
| RevenueCat webhook (GRANT/REVOKE) | ✅ Completo | `services/subscription_service.py` | product_id → plan_code |
| Migration 019: plan_code upgrade | ✅ Completo | `migrations/versions/019_*.py` | plan_code=1 → 2 para pagantes |
| SubscriptionStatusResponse.plan_name | ✅ Completo | `schemas/subscription.py` | "Gratuito"/"Essencial"/"Completo" |
| get_plans() 3-tier catalog | ✅ Completo | `services/subscription_service.py` | |
| Exceptions messages PT-BR | ✅ Completo | `core/exceptions.py` | todas traduzidas |
| LGPD: anonymization on delete | ✅ Completo | `services/user_service.py` | sem hard delete |
| Crisis audit log | ✅ Completo | — | ver legal-checklist |
| SSE streaming (delta/done/error) | ✅ Completo | `api/v1/endpoints/chat.py` | ver contracts.md |
| RAG retrieval (pgvector, threshold 0.45) | ✅ Completo | `services/rag_service.py` | |
| Journal endpoints | ✅ Completo | `api/v1/endpoints/journal.py` | |
| Mood check-in endpoints | ✅ Completo | `api/v1/endpoints/mood.py` | |
| Password change endpoint | ✅ Completo | — | |
| LGPD sessions endpoint | ✅ Completo | — | |
| RevenueCat webhook handler | ✅ Completo | `services/subscription_service.py` | |
| Diário guiado | ✅ Completo | — | |
| user_sessions audit (login/logout) | ✅ Completo | `auth_service.py` | best-effort, nunca falha o login |
| Migration 020: DROP ai_response_cache | ✅ Completo | `migrations/020_*.py` | tabela morta removida |
| Migration 021: programs/chapters UUID + slug | ✅ Completo | `migrations/021_*.py` | ADR-009 |
| Gate 3-tier: chat/mood sem require_premium | ✅ Completo | `mood.py`, `chat.py`, `dependencies.py` | ADR-010; insights continuam premium |
| Planos "Cuidado Essencial"/"Cuidado Completo" | ✅ Completo | `subscription_service.py` | get_plans() |
| GET /programs/recommended (ranking semântico) | ✅ Completo | `program_service.py`, `endpoints/programs.py` | avg embeddings user (chat/journal/mood) × cosine chapters; fallback sort_order; exclui 100% completos |

---

## Mobile — Expo SDK 55, React Native 0.83.4

| Feature | Status | Arquivo | Notas |
|---------|--------|---------|-------|
| HomeScreen subtitle condicional | ✅ Completo | `screens/home/HomeScreen.tsx` | mostra só se `hasCheckedInToday` |
| MoodHistory nav guard (sem duplicata) | ✅ Completo | `screens/mood/MoodHistoryScreen.tsx` | verifica state.routes |
| Heart icon alignment | ✅ Completo | `screens/home/HomeScreen.tsx` | `alignItems: 'flex-start'` |
| SubscriptionScreen exibe plan_name | ✅ Completo | `screens/profile/SubscriptionScreen.tsx` | "Assinante Essencial/Completo" |
| isPremiumOrTrial() cobre plan_code 1+2 | ✅ Completo | `store/authStore.ts` | |
| isCompleto() seletor | ✅ Completo | `store/authStore.ts` | plan_code===2 |
| plan_name no SubscriptionStatus type | ✅ Completo | `services/subscriptionService.ts` | |
| react-native-purchases lazy require() | ✅ Completo | `services/iapService.ts` | evita crash Expo Go |
| Google OAuth (dev client, não Expo Go) | ✅ Completo | `hooks/useGoogleAuth.ts` | PKCE implementado |
| Voice input (VoiceInputButton) | ✅ Completo | `components/VoiceInputButton.tsx` | |
| Crisis Banner | ✅ Completo | `components/CrisisBanner.tsx` | |
| OnboardingChecklist hook | ✅ Completo | `hooks/useOnboardingChecklist.ts` | hooks rule fix: antes do early return |
| Form reset on submit (MoodCheckin) | ✅ Completo | `MoodCheckinScreen.tsx` | resetForm() no dismiss da celebração + offline; padrão: todo input reseta após envio (exceto chat) |
| Tempo relativo com minutos (Último registro) | ✅ Completo | `HomeScreen.tsx` | "Agora mesmo" / "Há X min" / "Há Xh" |
| Histórico humor: total geral vs semana | ✅ Completo | `MoodHistoryScreen.tsx` | "registros no total" usa hist.total; "intensidade na semana" |
| Carrossel programas recomendados no Home | ✅ Completo | `HomeScreen.tsx` | estilo streaming: poster gradiente por categoria + resumo 3 linhas + meta |
| MoodHistory remodelada (relatório ux-researcher) | ✅ Completo | `MoodHistoryScreen.tsx` | título único "Humor"; + no header (padrão Diário); FAB removido (colidia com pill: ambos a 88px); 3 métricas: streak, humor predominante (emoji+label), intensidade+tendência (intensity_change_pct); dots de intensidade; agrupamento por dia Hoje/Ontem/data |
| Alinhamento cards "Esta semana" no Home | ✅ Completo | `HomeScreen.tsx` | insightTopSlot altura fixa 24 |

---

## UX Roadmap — Tier 1 (Quick Wins) — ✅ COMPLETO

| # | Item | Status | Onde |
|---|------|--------|------|
| 1 | expo-haptics install + todas as ações | ✅ Completo | ver detalhes abaixo |
| 2 | TypingIndicator animation (staggered dots) | ✅ Completo | `components/base/TypingIndicator.tsx` |
| 3 | Breathing curve (OnboardingWhyScreen) | ✅ Completo | valores corretos já presentes |
| 4 | VoiceInputButton pulse ring + haptics | ✅ Completo | start=Heavy, stop=Medium |
| 5 | Avatar AcollyaIcon (sem emoji) | ✅ Completo | ChatScreen usa AcollyaIcon |
| 6 | Send button Ionicons + scale animation | ✅ Completo | ChatScreen send button |
| 7 | Journal prompt chip "✨ Precisa de uma ideia?" | ✅ Completo | JournalNewScreen.tsx |
| 8 | Emoji removal ChatSessionList | ✅ Completo | usa AcollyaIcon |
| 9 | keyboardDismissMode="none" (JournalNew) | ✅ Completo | JournalNewScreen.tsx ScrollView |
| 10 | accessibilityRole="alert" nos containers de erro | ✅ Completo | MoodCheckin + JournalNew (no View, não ThemedText) |
| 11 | PT-BR accessibilityLabels (send, TTS, mic) | ✅ Completo | ChatScreen, TTSButton, VoiceInputButton |
| 12 | Error banner contrast | ✅ OK (sem fix) | Colors.error #C0392B = 5.37:1 em surface |
| 13 | Reduced-motion check | ✅ Completo | TypingIndicator + VoiceInputButton + CrisisBanner |
| 14 | Chat tab label "Conversar" | ✅ Completo | `navigation/index.tsx` |
| 15 | Suppress mood CTA se já registrou hoje | ✅ Completo | HomeScreen subtitle condicional |

### Haptics implementados por arquivo
| Arquivo | Ações com haptics |
|---------|-------------------|
| `ThemedButton.tsx` | Qualquer toque → Light (inclui todos os botões Onboarding) |
| `ChatScreen.tsx` | Send → Medium |
| `MoodCheckinScreen.tsx` | Cluster tap → Selection; Sub-emoção tap → Selection; Slider → Selection; Save → Success; Erro → Warning |
| `JournalNewScreen.tsx` | Save → Success; Erro → Warning |
| `CrisisBanner.tsx` | Aparição → Error; "Ligar 188" → Warning |
| `VoiceInputButton.tsx` | Iniciar gravação → Heavy; Parar gravação → Medium |

---

## UX Roadmap — Tier 2 (10 itens) — ✅ COMPLETO

| Item | Status | Onde |
|------|--------|------|
| Post-checkin celebration modal | ✅ Completo | `components/mood/StreakCelebrationModal.tsx` |
| EmpathyCard component | ✅ Completo | `components/home/EmpathyCard.tsx` — rotação diária |
| **Dark mode** | ✅ **Completo** | 50 arquivos migrados para `useThemeColors()` |
| Empty states redesign | ✅ Completo | `InvitationState` em Chat, Journal, MoodHistory |
| Conversation starters | ✅ Completo | `components/chat/StarterChips.tsx` |
| RAG awareness indicator | ✅ Completo | `components/chat/MemoryIndicator.tsx` |
| Frosted glass tab bar | ✅ Completo | BlurView intensity=40 iOS |
| CrisisBanner slide animation | ✅ Completo | SlideInDown 400ms + reduced-motion fallback |
| HomeScreen checklist widget | ✅ Completo | `OnboardingChecklist.tsx` — auto-dismiss 7 dias |
| Scroll-to-bottom FAB | ✅ Completo | `ScrollToBottomFAB.tsx` — spring animation |

### Dark mode — notas técnicas
- `ThemeProvider` no `App.tsx` wrapping toda a árvore; `ThemedRoot` component interno usa `C.background` no View raiz
- 50 arquivos: `import { Colors }` → `const C = useThemeColors()` + `function makeStyles(C)`
- `ErrorBoundary.tsx` mantém `Colors` estático (class component — hooks não permitidos)
- Ativação: automática ao mudar tema do sistema iOS/Android

---

## UX Roadmap — Tier 2.5 (Polimento Pós-Testes) — ⏳ PENDENTE

Identificado em 2026-07-25 após primeiros testes no dispositivo físico.

| # | Item | Esforço | Status | Arquivo(s) |
|---|------|---------|--------|------------|
| 1 | **Floating tab bar pill** — 4 tabs visíveis, position:absolute, borderRadius:32, bottom:24, sombra/blur | Alto | ✅ Completo | `navigation/index.tsx`, `theme/index.ts` |
| 2 | JournalTab e CrescimentoTab ocultas do tab bar (tabs continuam montadas — deep links/push intactos) | Baixo | ✅ Completo | `navigation/index.tsx` |
| 3 | "Assinatura" → "Planos de Cuidado" (ProfileScreen label + SubscriptionScreen header) | Baixo | ✅ Completo | `ProfileScreen.tsx`, `SubscriptionScreen.tsx` |
| 4 | Skeleton screens / loading states consistentes | Médio | ❌ Pendente | todas as telas com `loading` state |
| 5 | Migrar fetches críticos para TanStack Query (cache + staleTime) | Alto | ❌ Pendente | Home, Chat, Journal, Mood — elimina re-fetch no foco |

### Floating tab bar — notas técnicas (2026-07-25)
- Pill só aparece nas telas RAIZ de cada stack (`TAB_ROOT_SCREENS` + `getFocusedRouteNameFromRoute`); em telas de detalhe (Chat, JournalNew, Settings…) a barra some — libera inputs/botões inferiores
- Tabs ocultas via `tabBarButton: () => null` (`HIDDEN_TAB_OPTIONS`) — NÃO remover do navigator: HomeScreen, ProfileScreen, linking.ts e usePushNotifications navegam para elas
- Tokens novos em `theme/index.ts`: `TabBar.floatingBottom` (24), `floatingMargin` (16), `radius` (32), `clearance` (104)
- 6 telas raiz usam `paddingBottom: TabBar.clearance` no contentContainer — conteúdo escorre por baixo do pill
- `HelpAffordance` (FAB SOS) **removido do render** em 2026-07-25 por decisão do Kadu — componente preservado em `components/base/HelpAffordance.tsx` para futura reformulação do acesso a ajuda em crise; CrisisBanner automático continua ativo
- `floatingMargin: 40` — pill NÃO vai de ponta a ponta (decisão de design do Kadu)
- iOS: BlurView com `borderRadius + overflow:hidden`; Android: surface sólido + elevation 12

### Notas de prioridade
- Item 4: bloqueia percepção de lentidão em produção — implementar antes do lançamento
- Item 5: performance real — telas nunca refazem fetch se dado ainda é válido; TanStack Query já está no App.tsx, só falta usá-lo nas telas

### Reestruturação de telas: Agendamentos, Programas e Diário (registrado 2026-08-03) — ⏳ PENDENTE

Pedido do Kadu: aplicar às 3 telas o mesmo processo usado na remodelação da MoodHistory
(relatório de agente UX + implementação). Referência de qualidade: MoodHistory 2026-08-02.

| Tela | Escopo esperado | Arquivos |
|------|-----------------|----------|
| **Diário** (`JournalListScreen` + `JournalDetailScreen`) | Hierarquia/título, agrupamento por dia (paridade com Humor), indicadores no topo (streak de escrita? total?), estados vazios, cards | `screens/journal/*` |
| **Programas** (`ProgramsScreen` + `ProgramDetailScreen` + `ChapterViewScreen`) | Aplicar linguagem visual dos posters/gradientes do carrossel do Home; categoria com cores; progresso visual; CATEGORY_EMOJI usa chaves pt-BR mas backend manda categorias em EN (bug latente — emojis nunca aparecem); revisar hierarquia do detalhe | `screens/programs/*` |
| **Agendamentos** (`AppointmentsScreen` + `TherapistsScreen` + `TherapistDetailScreen` + `AppointmentBookScreen`) | Fluxo completo nunca passou por revisão de UX; acessível só via Perfil — revisar descoberta, cards de terapeuta, fluxo de booking, estados vazios | `screens/appointments/*` |

**Processo:** para cada tela, rodar agente ux-researcher com o arquivo + contexto (como feito
na MoodHistory), decidir com o Kadu, implementar. Uma tela por sessão.

### Migração de Trial: backend → RevenueCat/loja (decidido 2026-07-26) — ⏳ PENDENTE

Decisão do Kadu: mover o trial de 7 dias do modelo backend (concedido no cadastro) para
Introductory Offer da loja gerenciado via RevenueCat. Motivo: conversão por inércia
(30–50% vs 2–5%), elegibilidade gerenciada pela Apple/Google, menos lógica custom.

| # | Mudança | Onde |
|---|---------|------|
| 1 | Parar de conceder `trialing` no cadastro — usuário novo nasce no Gratuito | backend `user_service.py` / fluxo de registro |
| 2 | Webhook: `INITIAL_PURCHASE` com `period_type: TRIAL` → status `trialing` (não `active`) | `services/subscription_service.py` |
| 3 | Paywall: exibir "7 dias grátis, depois R$X/mês" via `introPrice` do produto | `SubscriptionScreen.tsx` |
| 4 | Configurar Introductory Offer (7 dias grátis) nos produtos | App Store Connect + Play Console (manual Kadu) |

⚠️ NÃO manter os dois modelos — seria trial duplo (14 dias grátis).
⚠️ Item 1 remove o "todo usuário experimenta premium" — Gratuito (10 msgs/dia) vira a porta de entrada.

### Backlog de estudo — Insight Staleness (registrado 2026-08-02, pedido do Kadu)

**Problema:** usuário que fica tempo sem usar o app (ex: Voeo) pode receber insights
baseados em contexto desatualizado — "estresse no trabalho e problemas de sono"
relatados semanas atrás podem já ter passado, gerando insights irrelevantes.

**Direções a estudar juntos (não implementar ainda):**
- Time decay nos pesos do RAG já existe para retrieval — avaliar decay também na
  geração de insights e no persona (facts com timestamp de validade?)
- "Re-onboarding suave" após X dias de ausência: "Como você está desde a última vez?"
  antes de gerar insights novos
- Marcar persona facts como `stale` após N dias sem reforço; prompt do insight
  poderia sinalizar incerteza temporal ("da última vez que conversamos...")
- Sinal de recência no prompt: idade dos dados usados no contexto

**Quando:** análise conjunta Kadu + Claude mais próximo do final do roadmap.

### RevenueCat Sandbox Testing (setup de dev — não é código)
- Criar Sandbox Tester no App Store Connect → Usuários → Testadores Sandbox
- No iPhone: Ajustes → App Store → sair do Apple ID real durante a compra
- Usar o Sandbox Apple ID quando o iOS pedir login na compra
- Compras sandbox são gratuitas e disparam o webhook do RevenueCat normalmente
- Após compra: verificar no painel RevenueCat se o evento PURCHASE apareceu

---

## Build / Infra

| Item | Status | Notas |
|------|--------|-------|
| EAS dev client build (iOS) | ⏳ Pendente rebuild | mudanças mobile requerem novo build |
| RevenueCat produtos criados | ⏳ Manual (usuário) | App Store Connect + Play Console |
| Docker postgres porta 5433 | ✅ Configurado | docker-compose.yml |
| Python 3.12 venv local | ✅ Configurado | ver environment.md |
