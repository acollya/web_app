# Acollya PWA - Plano de Implementação MVP

## Arquitetura e Estrutura de Arquivos

### 1. Configuração Base (Prioridade: Alta)
- [x] Template shadcn-ui inicializado
- [ ] Atualizar index.html com título, meta tags e manifest
- [ ] Criar manifest.json para PWA
- [ ] Configurar service worker básico
- [ ] Atualizar tailwind.config.ts com paleta de cores Acollya

### 2. Tipos e Interfaces TypeScript (src/types/)
- [ ] types/user.ts - User, AuthResponse
- [ ] types/mood.ts - MoodCheckin, Emotion, MoodSummary
- [ ] types/journal.ts - JournalEntry
- [ ] types/chat.ts - ChatMessage, ChatSession
- [ ] types/program.ts - Program, ProgramProgress, ProgramDay
- [ ] types/therapist.ts - Therapist, Appointment, Availability
- [ ] types/subscription.ts - Subscription, Plan

### 3. Configuração de API e Serviços (src/services/)
- [ ] services/apiClient.ts - Cliente HTTP centralizado com BASE_URL
- [ ] services/authService.ts - login, register, googleAuth (mock)
- [ ] services/moodService.ts - createCheckin, getCheckins, getSummary (mock)
- [ ] services/journalService.ts - createEntry, getEntries (mock)
- [ ] services/chatService.ts - sendMessage, getSessions (mock)
- [ ] services/programService.ts - getPrograms, updateProgress (mock)
- [ ] services/analyticsService.ts - getMoodAnalytics (mock)
- [ ] services/therapistService.ts - getTherapists, bookAppointment (mock)

### 4. Estado Global (src/store/)
- [ ] store/authStore.ts - Zustand store para autenticação
- [ ] store/moodStore.ts - Estado de humor atual
- [ ] store/chatStore.ts - Sessão de chat ativa
- [ ] store/programStore.ts - Progresso em programas

### 5. Componentes Reutilizáveis (src/components/)
- [ ] components/Layout.tsx - Layout principal com navegação
- [ ] components/BottomNav.tsx - Navegação inferior mobile
- [ ] components/PrimaryButton.tsx - Botão primário com estilo Acollya
- [ ] components/SecondaryButton.tsx - Botão secundário
- [ ] components/TertiaryButton.tsx - Botão terciário
- [ ] components/ChatBubble.tsx - Bolha de chat (AI e usuário)
- [ ] components/EmotionIcon.tsx - Ícone de emoção
- [ ] components/MoodCard.tsx - Card de humor
- [ ] components/ProgramCard.tsx - Card de programa
- [ ] components/TherapistCard.tsx - Card de terapeuta
- [ ] components/LoadingSpinner.tsx - Indicador de carregamento
- [ ] components/OfflineIndicator.tsx - Indicador de modo offline
- [ ] components/TypingIndicator.tsx - Indicador de digitação (3 pontos)
- [ ] components/MoodGraph.tsx - Gráfico de humor (7 dias)

### 6. Páginas - Onboarding e Autenticação (src/pages/)
- [ ] pages/Onboarding1.tsx - Introdução à Acollya
- [ ] pages/Onboarding2.tsx - Benefícios
- [ ] pages/Onboarding3.tsx - Privacidade e LGPD
- [ ] pages/Login.tsx - Login com email/senha e Google
- [ ] pages/Register.tsx - Cadastro
- [ ] pages/ForgotPassword.tsx - Recuperação de senha

### 7. Páginas - Dashboard e Funcionalidades Principais
- [ ] pages/Home.tsx - Dashboard emocional
- [ ] pages/MoodCheckin.tsx - Check-in de humor
- [ ] pages/Journal.tsx - Lista de entradas do diário
- [ ] pages/JournalNew.tsx - Nova entrada de diário
- [ ] pages/Chat.tsx - Chat com IA terapêutica
- [ ] pages/Programs.tsx - Lista de programas
- [ ] pages/ProgramDetail.tsx - Detalhes do programa
- [ ] pages/Analytics.tsx - Painel de emoções

### 8. Páginas - Profissionais e Conta
- [ ] pages/Therapists.tsx - Lista de psicólogos
- [ ] pages/TherapistDetail.tsx - Detalhes do terapeuta
- [ ] pages/Booking.tsx - Agendamento
- [ ] pages/Profile.tsx - Perfil do usuário
- [ ] pages/Settings.tsx - Configurações
- [ ] pages/Privacy.tsx - Privacidade e segurança
- [ ] pages/About.tsx - Sobre a Acollya
- [ ] pages/Subscription.tsx - Planos e assinaturas
- [ ] pages/Terms.tsx - Termos de uso
- [ ] pages/PrivacyPolicy.tsx - Política de privacidade

### 9. Hooks Customizados (src/hooks/)
- [ ] hooks/useAuth.ts - Hook de autenticação
- [ ] hooks/useOffline.ts - Detectar estado offline
- [ ] hooks/useLocalStorage.ts - Persistência local

### 10. Utilidades e Helpers (src/lib/)
- [ ] lib/constants.ts - Constantes (cores, endpoints, etc)
- [ ] lib/mockData.ts - Dados mock para desenvolvimento
- [ ] lib/offlineStorage.ts - IndexedDB para offline-first
- [ ] lib/crisisDetection.ts - Detecção de palavras de risco

### 11. PWA e Configurações Finais
- [ ] public/manifest.json - Manifest PWA
- [ ] public/service-worker.js - Service worker
- [ ] Atualizar App.tsx com rotas completas
- [ ] Testar navegação entre todas as páginas
- [ ] Testar responsividade mobile
- [ ] Verificar animações e microinterações

## Ordem de Implementação

### Fase 1: Fundação (Arquivos 1-4)
1. Configuração base e cores
2. Tipos TypeScript
3. API client e serviços mock
4. Estado global

### Fase 2: Componentes Base (Arquivo 5)
5. Componentes reutilizáveis

### Fase 3: Fluxo de Autenticação (Arquivo 6)
6. Onboarding e páginas de auth

### Fase 4: Funcionalidades Principais (Arquivo 7)
7. Dashboard, mood, journal, chat, programs

### Fase 5: Funcionalidades Secundárias (Arquivo 8)
8. Therapists, profile, settings

### Fase 6: PWA e Finalização (Arquivos 9-11)
9. Hooks customizados
10. Utilidades
11. PWA configuration

## Notas Importantes
- Todos os textos em português brasileiro
- Tom acolhedor, empático e direto
- Mobile-first design
- Paleta de cores Acollya estritamente seguida
- Microinterações suaves (breathe, fade, slide, pulse)
- Avisos de segurança no chat (CVV 188)
- Detecção de crise com modal especial
- Offline-first com localStorage/IndexedDB
- Todas as APIs são mock, preparadas para backend FastAPI futuro