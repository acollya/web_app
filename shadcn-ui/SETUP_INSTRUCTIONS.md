# 🚀 Instruções de Configuração Final - Acollya

Este documento contém as instruções para finalizar a configuração da aplicação Acollya após as correções implementadas.

---

## 📋 PROBLEMAS CORRIGIDOS

### ✅ Problema 1: Usuário não aparece no Supabase Dashboard
**Solução:** Trigger SQL automático + fallback manual no AuthCallback

### ✅ Problema 2: Botão "Assinar Mensal" não funciona
**Solução:** Integração real com Stripe via Edge Function

---

## 🔧 CONFIGURAÇÃO NECESSÁRIA

### 1️⃣ Aplicar Migration do Trigger de Usuário

O trigger SQL criará automaticamente um registro na tabela `public.users` sempre que um usuário fizer signup via OAuth (Google).

#### **Opção A: Via Supabase CLI (Recomendado)**

Execute no terminal do seu MacBook:

```bash
cd ~/Downloads/shadcn-ui  # ou o caminho do seu projeto
supabase db push
```

Se aparecer erro de "not linked", execute antes:

```bash
supabase link --project-ref plujzteuqcmctndvymtv
```

#### **Opção B: Via Supabase Dashboard (Manual)**

1. Acesse: https://supabase.com/dashboard/project/plujzteuqcmctndvymtv/sql
2. Clique em "New query"
3. Copie TODO o conteúdo do arquivo `supabase/migrations/20240121_create_user_trigger.sql`
4. Cole no editor SQL
5. Clique em "Run" (ou pressione Cmd+Enter)
6. Verifique se apareceu "Success" sem erros

**Conteúdo do SQL:**

```sql
-- Migration: Create trigger to auto-create user in public.users after auth signup
-- This ensures users who sign up via Google OAuth are automatically added to public.users table

-- Function to create user in public.users after auth.users insertion
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (
    id,
    email,
    name,
    trial_ends_at,
    subscription_status,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(
      NEW.raw_user_meta_data->>'full_name',
      NEW.raw_user_meta_data->>'name',
      split_part(NEW.email, '@', 1)
    ),
    NOW() + INTERVAL '7 days',
    'trialing',
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO NOTHING; -- Avoid errors if user already exists
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop trigger if exists (for re-running migration)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger that fires after INSERT on auth.users
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres, anon, authenticated, service_role;

-- Comment
COMMENT ON FUNCTION public.handle_new_user() IS 'Automatically creates a user record in public.users when a new user signs up via auth.users (including OAuth)';
```

---

### 2️⃣ Configurar Produtos no Stripe

Você precisa criar os produtos de assinatura no Stripe Dashboard e obter os **Price IDs**.

#### **Passo 1: Acessar Stripe Dashboard**

1. Acesse: https://dashboard.stripe.com/test/products
2. Certifique-se de estar em **Test Mode** (toggle no canto superior direito)

#### **Passo 2: Criar Produto Mensal**

1. Clique em **"+ Add product"**
2. Preencha:
   - **Name:** `Acollya Premium - Mensal`
   - **Description:** `Acesso completo à plataforma Acollya com chat ilimitado, programas de autocuidado e análises detalhadas`
   - **Pricing model:** Standard pricing
   - **Price:** `17.90`
   - **Currency:** `BRL` (Real Brasileiro)
   - **Billing period:** `Monthly`
3. Clique em **"Save product"**
4. **COPIE O PRICE ID** (formato: `price_1ABC123xyz...`)

#### **Passo 3: Criar Produto Anual**

1. Clique em **"+ Add product"** novamente
2. Preencha:
   - **Name:** `Acollya Premium - Anual`
   - **Description:** `Acesso completo à plataforma Acollya com 16% de economia (equivalente a R$ 14,99/mês)`
   - **Pricing model:** Standard pricing
   - **Price:** `179.90`
   - **Currency:** `BRL` (Real Brasileiro)
   - **Billing period:** `Yearly`
3. Clique em **"Save product"**
4. **COPIE O PRICE ID** (formato: `price_2DEF456abc...`)

---

### 3️⃣ Atualizar Price IDs no Código

Agora você precisa substituir os Price IDs no arquivo `Subscription.tsx`.

#### **Arquivo a editar:**
`/workspace/shadcn-ui/src/pages/Subscription.tsx`

#### **Localizar (por volta da linha 34-57):**

```typescript
{
  name: 'Premium Mensal',
  price: 'R$ 17,90/mês',
  priceId: import.meta.env.VITE_STRIPE_PRICE_ID_MONTHLY,  // ← Esta linha
  popular: true,
  features: [
    // ...
  ],
},
{
  name: 'Premium Anual',
  price: 'R$ 179,90/ano',
  priceId: import.meta.env.VITE_STRIPE_PRICE_ID_YEARLY,  // ← Esta linha
  badge: 'Economia de 17%',
  features: [
    // ...
  ],
},
```

#### **Atualizar arquivo `.env.local`:**

Edite o arquivo `/workspace/shadcn-ui/.env.local` e substitua os valores:

```env
# STRIPE CONFIGURATION
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_51Sce8zDnxT4DNHL7SDYtBYK8eSfXUtSBGhHNxK95xwx9HXf5uXSoqE86IT2eavUk4nZqBMJ4p5j0sXCPoU4LLjRr00nMVmVelO
VITE_STRIPE_PRICE_ID_MONTHLY=price_SEU_ID_MENSAL_AQUI     # ← Substituir pelo Price ID do produto mensal
VITE_STRIPE_PRICE_ID_YEARLY=price_SEU_ID_ANUAL_AQUI       # ← Substituir pelo Price ID do produto anual
```

**Exemplo:**
```env
VITE_STRIPE_PRICE_ID_MONTHLY=price_1QYZ123abc456def
VITE_STRIPE_PRICE_ID_YEARLY=price_2ABC789xyz123ghi
```

---

### 4️⃣ Configurar Stripe Secrets no Supabase

As Edge Functions precisam das chaves secretas do Stripe.

#### **Passo 1: Obter Secret Key do Stripe**

1. Acesse: https://dashboard.stripe.com/test/apikeys
2. Copie a **Secret key** (começa com `sk_test_...`)

#### **Passo 2: Obter Webhook Secret (Opcional para Produção)**

1. Acesse: https://dashboard.stripe.com/test/webhooks
2. Clique em **"Add endpoint"**
3. Preencha:
   - **Endpoint URL:** `https://plujzteuqcmctndvymtv.supabase.co/functions/v1/stripe-webhook`
   - **Events to send:** Selecione:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
4. Clique em **"Add endpoint"**
5. Copie o **Signing secret** (começa com `whsec_...`)

#### **Passo 3: Configurar no Supabase**

Execute no terminal:

```bash
cd ~/Downloads/shadcn-ui

# Configurar Secret Key
supabase secrets set STRIPE_API_KEY="sk_test_SEU_SECRET_KEY_AQUI"

# Configurar Webhook Secret (opcional)
supabase secrets set STRIPE_WEBHOOK_SIGNING_SECRET="whsec_SEU_WEBHOOK_SECRET_AQUI"
```

**Exemplo:**
```bash
supabase secrets set STRIPE_API_KEY="sk_test_51Sce8zDnxT4DNHL7abcdefghijklmnopqrstuvwxyz"
supabase secrets set STRIPE_WEBHOOK_SIGNING_SECRET="whsec_1234567890abcdefghijklmnopqrstuvwxyz"
```

---

## 🧪 TESTES

### Teste 1: Criação de Usuário via Google OAuth

#### **Objetivo:** Verificar se o usuário é criado automaticamente na tabela `public.users`

1. **Fazer logout** da aplicação (se estiver logado)
2. **Acessar:** http://localhost:5173/login
3. **Clicar** em "Continuar com Google"
4. **Fazer login** com sua conta Google
5. **Verificar no Supabase Dashboard:**
   - Ir em: https://supabase.com/dashboard/project/plujzteuqcmctndvymtv/editor
   - Abrir tabela `users` (não `auth.users`)
   - Verificar se seu usuário aparece com:
     - ✅ `id` (UUID)
     - ✅ `email` (seu email do Google)
     - ✅ `name` (seu nome do Google)
     - ✅ `trial_ends_at` (data atual + 7 dias)
     - ✅ `subscription_status` = `trialing`

**Resultado esperado:** ✅ Usuário aparece na tabela `public.users`

---

### Teste 2: Botão de Assinatura

#### **Objetivo:** Verificar se o botão redireciona para o Stripe Checkout

1. **Estar logado** na aplicação
2. **Acessar:** http://localhost:5173/subscription
3. **Clicar** em "Assinar Mensal"
4. **Verificar:**
   - ✅ Toast aparece: "Processando... Redirecionando para o checkout seguro do Stripe"
   - ✅ Página redireciona para `checkout.stripe.com`
   - ✅ Formulário de pagamento do Stripe aparece

**Resultado esperado:** ✅ Redirecionamento para Stripe Checkout

---

### Teste 3: Pagamento de Teste

#### **Objetivo:** Completar um pagamento de teste e verificar webhook

1. **No Stripe Checkout**, preencha:
   - **Email:** qualquer email
   - **Card number:** `4242 4242 4242 4242` (cartão de teste)
   - **Expiry:** qualquer data futura (ex: `12/25`)
   - **CVC:** qualquer 3 dígitos (ex: `123`)
   - **Name:** qualquer nome
2. **Clicar** em "Subscribe"
3. **Aguardar** processamento
4. **Verificar:**
   - ✅ Redirecionamento para `/subscription?success=true`
   - ✅ No Supabase Dashboard, tabela `subscriptions`, deve aparecer novo registro
   - ✅ Na tabela `users`, campo `subscription_status` deve mudar para `active`

**Resultado esperado:** ✅ Assinatura criada e usuário atualizado

---

## 🐛 TROUBLESHOOTING

### Erro: "Usuário não autenticado" ao clicar em Assinar

**Causa:** Sessão expirada ou usuário não logado

**Solução:**
1. Fazer logout
2. Fazer login novamente
3. Tentar assinar novamente

---

### Erro: "priceId é obrigatório"

**Causa:** Price IDs não configurados no `.env.local`

**Solução:**
1. Verificar se `.env.local` tem `VITE_STRIPE_PRICE_ID_MONTHLY` e `VITE_STRIPE_PRICE_ID_YEARLY`
2. Reiniciar o servidor de desenvolvimento: `npm run dev`

---

### Erro: "Stripe API key not found"

**Causa:** Secret Key não configurado no Supabase

**Solução:**
```bash
supabase secrets set STRIPE_API_KEY="sk_test_..."
```

---

### Usuário não aparece na tabela `public.users`

**Causa:** Migration não foi aplicada

**Solução:**
1. Verificar se executou `supabase db push` OU aplicou SQL manualmente
2. Verificar no SQL Editor se a função `handle_new_user()` existe:
   ```sql
   SELECT proname FROM pg_proc WHERE proname = 'handle_new_user';
   ```
3. Se não existir, aplicar a migration novamente

---

### Botão "Assinar" não faz nada

**Causa:** Edge Function não deployada ou erro no código

**Solução:**
1. Verificar se Edge Function está deployada:
   ```bash
   supabase functions list
   ```
2. Se não estiver, fazer deploy:
   ```bash
   supabase functions deploy create-checkout --no-verify-jwt
   ```
3. Verificar logs da função:
   ```bash
   supabase functions logs create-checkout
   ```

---

## 📚 REFERÊNCIAS

- **Supabase Auth:** https://supabase.com/docs/guides/auth
- **Supabase Edge Functions:** https://supabase.com/docs/guides/functions
- **Stripe Checkout:** https://stripe.com/docs/payments/checkout
- **Stripe Webhooks:** https://stripe.com/docs/webhooks

---

## ✅ CHECKLIST FINAL

Antes de considerar a configuração completa, verifique:

- [ ] Migration aplicada (trigger criado)
- [ ] Produtos criados no Stripe (Mensal e Anual)
- [ ] Price IDs atualizados no `.env.local`
- [ ] Stripe Secret Key configurado no Supabase
- [ ] Webhook configurado (opcional para produção)
- [ ] Teste 1: Usuário aparece no dashboard após login Google
- [ ] Teste 2: Botão redireciona para Stripe Checkout
- [ ] Teste 3: Pagamento de teste funciona e atualiza banco

---

## 🎉 CONCLUSÃO

Após seguir todas as instruções acima, sua aplicação Acollya estará totalmente funcional com:

✅ Autenticação via Google OAuth
✅ Criação automática de usuários no banco de dados
✅ Sistema de assinaturas via Stripe
✅ Webhooks para atualização de status de assinatura

Se tiver dúvidas ou problemas, consulte a seção de Troubleshooting ou entre em contato com o suporte.

**Boa sorte! 🚀**