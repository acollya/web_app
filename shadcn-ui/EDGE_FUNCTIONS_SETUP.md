# 🚀 Configuração das Edge Functions - Guia Completo

Este guia detalha como configurar as variáveis de ambiente para as Edge Functions do Supabase.

---

## 📋 Variáveis Necessárias

As Edge Functions precisam de **4 variáveis de ambiente**:

| Variável | Onde Obter | Usado Por |
|----------|-----------|-----------|
| `STRIPE_API_KEY` | Stripe Dashboard → Developers → API keys (Secret key) | Todas as 3 functions |
| `STRIPE_WEBHOOK_SIGNING_SECRET` | Stripe Dashboard → Webhooks → Endpoint → Signing secret | Apenas `stripe-webhook` |
| `SUPABASE_URL` | Auto-injetado pelo Supabase | Todas as 3 functions |
| `SUPABASE_SERVICE_ROLE_KEY` | Auto-injetado pelo Supabase | Todas as 3 functions |

---

## 🔧 Método 1: Configurar via Supabase CLI (Recomendado)

### Pré-requisitos
```bash
# Instalar Supabase CLI
npm install -g supabase

# Login
supabase login

# Link ao projeto
cd /workspace/shadcn-ui
supabase link --project-ref SEU_PROJECT_REF
```

### Configurar Secrets
```bash
# 1. STRIPE_API_KEY (Secret Key do Stripe)
# Obter em: https://dashboard.stripe.com/apikeys
supabase secrets set STRIPE_API_KEY=sk_test_51...

# 2. STRIPE_WEBHOOK_SIGNING_SECRET (Webhook Signing Secret)
# Obter DEPOIS de criar o webhook (passo explicado abaixo)
supabase secrets set STRIPE_WEBHOOK_SIGNING_SECRET=whsec_...

# Verificar secrets configurados
supabase secrets list
```

---

## 🔧 Método 2: Configurar via Supabase Dashboard

1. Acesse https://supabase.com/dashboard
2. Selecione seu projeto
3. Vá em **Edge Functions** (menu lateral)
4. Clique em uma das suas functions (`stripe-webhook`, `create-checkout`, ou `create-portal`)
5. Vá na aba **Secrets**
6. Clique em **"Add new secret"**
7. Adicione:
   - Name: `STRIPE_API_KEY`
   - Value: `sk_test_51...` (sua Secret Key do Stripe)
8. Repita para `STRIPE_WEBHOOK_SIGNING_SECRET` (após criar o webhook)

---

## 📦 Deploy das Edge Functions

### Via CLI
```bash
cd /workspace/shadcn-ui

# Deploy de todas as functions
supabase functions deploy

# Ou deploy individual
supabase functions deploy stripe-webhook
supabase functions deploy create-checkout
supabase functions deploy create-portal
```

### Obter URLs das Functions
Após o deploy, você receberá as URLs:
```
https://[PROJECT_REF].supabase.co/functions/v1/stripe-webhook
https://[PROJECT_REF].supabase.co/functions/v1/create-checkout
https://[PROJECT_REF].supabase.co/functions/v1/create-portal
```

---

## 🔗 Configurar Webhook no Stripe

### Passo 1: Criar Endpoint
1. Acesse https://dashboard.stripe.com/webhooks
2. Clique em **"+ Add endpoint"**
3. **Endpoint URL**: `https://[PROJECT_REF].supabase.co/functions/v1/stripe-webhook`
4. **Description**: `Acollya PWA - Supabase Edge Function`

### Passo 2: Selecionar Eventos
Marque os seguintes eventos:
- ✅ `checkout.session.completed`
- ✅ `checkout.session.async_payment_succeeded`
- ✅ `checkout.session.async_payment_failed`
- ✅ `customer.subscription.created`
- ✅ `customer.subscription.updated`
- ✅ `customer.subscription.deleted`
- ✅ `invoice.payment_succeeded`
- ✅ `invoice.payment_failed`

### Passo 3: Obter Signing Secret
1. Após criar o endpoint, clique nele
2. Copie o **"Signing secret"** (começa com `whsec_...`)
3. Configure como variável de ambiente:
   ```bash
   supabase secrets set STRIPE_WEBHOOK_SIGNING_SECRET=whsec_...
   ```

### Passo 4: Testar Webhook
```bash
# Via Stripe CLI
stripe trigger checkout.session.completed

# Ou via Dashboard
# Stripe Dashboard → Webhooks → Seu endpoint → "Send test webhook"
```

---

## ✅ Checklist Final

Antes de ir para produção, verifique:

- [ ] `STRIPE_API_KEY` configurado no Supabase
- [ ] `STRIPE_WEBHOOK_SIGNING_SECRET` configurado no Supabase
- [ ] Edge Functions deployadas com sucesso
- [ ] Webhook criado no Stripe Dashboard
- [ ] Eventos corretos selecionados no webhook
- [ ] Teste de webhook realizado (status 200)
- [ ] Produtos/Preços criados no Stripe
- [ ] Price IDs adicionados no `.env.local` do frontend
- [ ] Logs das Edge Functions verificados (sem erros)

---

## 🐛 Troubleshooting

### Erro: "STRIPE_API_KEY não definido"
**Solução:**
```bash
supabase secrets set STRIPE_API_KEY=sk_test_...
supabase functions deploy stripe-webhook
```

### Erro: "Webhook signature verification failed"
**Causa:** `STRIPE_WEBHOOK_SIGNING_SECRET` incorreto ou não configurado

**Solução:**
1. Verifique o signing secret no Stripe Dashboard
2. Reconfigure:
   ```bash
   supabase secrets set STRIPE_WEBHOOK_SIGNING_SECRET=whsec_...
   supabase functions deploy stripe-webhook
   ```

### Webhook retorna 500
**Solução:**
1. Verifique os logs no Supabase Dashboard:
   - Edge Functions → `stripe-webhook` → Logs
2. Verifique se todas as variáveis estão configuradas
3. Teste localmente:
   ```bash
   supabase functions serve stripe-webhook
   ```

### Erro: "Missing stripe_price_id"
**Causa:** Produto/Preço não configurado corretamente no Stripe

**Solução:**
1. Verifique se o produto tem um Price ID
2. Confirme que o Price ID está correto na requisição

---

## 📚 Recursos Adicionais

- **Documentação Stripe Webhooks:** https://stripe.com/docs/webhooks
- **Documentação Supabase Edge Functions:** https://supabase.com/docs/guides/functions
- **Stripe CLI:** https://stripe.com/docs/stripe-cli
- **Testar Webhooks:** https://stripe.com/docs/webhooks/test

---

## 🔐 Segurança

### ⚠️ NUNCA exponha no frontend:
- `STRIPE_API_KEY` (Secret Key)
- `SUPABASE_SERVICE_ROLE_KEY`
- `STRIPE_WEBHOOK_SIGNING_SECRET`

### ✅ Pode ser exposto no frontend:
- `VITE_STRIPE_PUBLISHABLE_KEY` (Publishable Key)
- `VITE_SUPABASE_ANON_KEY` (Anon Key)
- `VITE_SUPABASE_URL`

---

**Precisa de ajuda?** Consulte os logs das Edge Functions no Supabase Dashboard ou execute localmente com `supabase functions serve`.