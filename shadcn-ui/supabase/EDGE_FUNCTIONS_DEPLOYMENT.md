# Guia de Deploy - Edge Functions do Supabase

Este guia explica como fazer deploy das Edge Functions do projeto Acollya PWA.

## Pré-requisitos

1. **Instalar Supabase CLI**
```bash
# macOS/Linux
brew install supabase/tap/supabase

# Windows (via Scoop)
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase

# Ou via npm
npm install -g supabase
```

2. **Login no Supabase**
```bash
supabase login
```

3. **Link do projeto**
```bash
supabase link --project-ref seu-project-ref
```

## Edge Functions Disponíveis

### Pagamento e Assinaturas
1. **stripe-webhook** (TypeScript) - Processa webhooks do Stripe
2. **create-checkout** (TypeScript) - Cria sessões de checkout
3. **create-portal** (TypeScript) - Portal do cliente Stripe

### IA e Análise
4. **chat-ai** (Python) - Chat com IA usando OpenAI
5. **journal-reflection** (TypeScript) - Reflexões sobre diário
6. **mood-insights** (TypeScript) - Análise de padrões de humor
7. **mood-checkin** (TypeScript) - Check-ins de humor com insights IA

### Matching e Progresso
8. **therapist-matching** (TypeScript) - Matching de terapeutas
9. **program-progress** (TypeScript) - Progresso em programas
10. **appointment-booking** (TypeScript) - Agendamento de consultas

## Configurar Secrets

```bash
# Stripe
supabase secrets set STRIPE_API_KEY=sk_test_...
supabase secrets set STRIPE_WEBHOOK_SIGNING_SECRET=whsec_...

# OpenAI (para chat-ai, journal-reflection, mood-checkin)
supabase secrets set OPENAI_API_KEY=sk-...
```

## Deploy Individual

### Pagamento
```bash
supabase functions deploy stripe-webhook --no-verify-jwt
supabase functions deploy create-checkout
supabase functions deploy create-portal
```

### IA e Análise
```bash
supabase functions deploy chat-ai
supabase functions deploy journal-reflection
supabase functions deploy mood-insights
supabase functions deploy mood-checkin
```

### Matching e Progresso
```bash
supabase functions deploy therapist-matching
supabase functions deploy program-progress
supabase functions deploy appointment-booking
```

## Deploy Todas as Funções

```bash
# Script para deploy de todas as funções
supabase functions deploy stripe-webhook --no-verify-jwt
supabase functions deploy create-checkout
supabase functions deploy create-portal
supabase functions deploy chat-ai
supabase functions deploy journal-reflection
supabase functions deploy mood-insights
supabase functions deploy mood-checkin
supabase functions deploy therapist-matching
supabase functions deploy program-progress
supabase functions deploy appointment-booking
```

## URLs das Edge Functions

Após o deploy:

```
# Pagamento
https://seu-project-ref.supabase.co/functions/v1/stripe-webhook
https://seu-project-ref.supabase.co/functions/v1/create-checkout
https://seu-project-ref.supabase.co/functions/v1/create-portal

# IA e Análise
https://seu-project-ref.supabase.co/functions/v1/chat-ai
https://seu-project-ref.supabase.co/functions/v1/journal-reflection
https://seu-project-ref.supabase.co/functions/v1/mood-insights
https://seu-project-ref.supabase.co/functions/v1/mood-checkin

# Matching e Progresso
https://seu-project-ref.supabase.co/functions/v1/therapist-matching
https://seu-project-ref.supabase.co/functions/v1/program-progress
https://seu-project-ref.supabase.co/functions/v1/appointment-booking
```

## Monitoramento

### Ver logs em tempo real
```bash
# Função específica
supabase functions logs chat-ai --tail
supabase functions logs mood-insights --tail

# Todas as funções
supabase functions logs --tail
```

### Listar funções deployadas
```bash
supabase functions list
```

## Testar Localmente

```bash
# TypeScript
supabase functions serve journal-reflection --env-file .env.local

# Python
supabase functions serve chat-ai --env-file .env.local
```

## Resumo de Funcionalidades

| Função | Linguagem | Requer OpenAI | Descrição |
|--------|-----------|---------------|-----------|
| stripe-webhook | TypeScript | ❌ | Sincroniza assinaturas |
| create-checkout | TypeScript | ❌ | Cria checkout Stripe |
| create-portal | TypeScript | ❌ | Portal do cliente |
| chat-ai | Python | ✅ | Chat com IA |
| journal-reflection | TypeScript | ✅ | Reflexões de diário |
| mood-insights | TypeScript | ❌ | Análise de humor |
| mood-checkin | TypeScript | ⚠️ | Check-in (IA opcional) |
| therapist-matching | TypeScript | ❌ | Matching de terapeutas |
| program-progress | TypeScript | ❌ | Progresso em programas |
| appointment-booking | TypeScript | ❌ | Agendamentos |

⚠️ = Funciona sem, mas com funcionalidade reduzida

## Troubleshooting

### Erro: "Missing environment variable"
```bash
supabase secrets list
```

### Erro: "Function not found"
```bash
supabase functions list
```

### Erro de autenticação
- Verifique se o token JWT está sendo enviado
- Confirme que o usuário existe na tabela `users`

### Erro do OpenAI API
- Verifique a chave da API
- Confirme créditos disponíveis
- Veja os logs: `supabase functions logs <function-name> --tail`

## Próximos Passos

1. ✅ Deploy das funções
2. ✅ Configurar secrets
3. ✅ Configurar webhook do Stripe
4. ✅ Testar cada função
5. ✅ Integrar no frontend
6. ✅ Monitorar logs

## Suporte

- [Documentação Supabase](https://supabase.com/docs/guides/functions)
- [Supabase Discord](https://discord.supabase.com)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/supabase)