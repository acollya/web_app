// supabase/functions/stripe-webhook/index.ts
// Webhook Stripe -> Supabase Edge (Deno)
// Sincroniza estado de assinaturas na tabela public.subscriptions

import Stripe from 'https://esm.sh/stripe@14?target=denonext';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ========== ENV VARS ==========
const stripeApiKey = Deno.env.get('STRIPE_API_KEY') as string;
const stripeWebhookSecret = Deno.env.get('STRIPE_WEBHOOK_SIGNING_SECRET') as string;

const supabaseUrl = Deno.env.get('SUPABASE_URL') as string;
const supabaseServiceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') as string;

if (!stripeApiKey) console.error('⚠️ STRIPE_API_KEY não definido');
if (!stripeWebhookSecret) console.error('⚠️ STRIPE_WEBHOOK_SIGNING_SECRET não definido');
if (!supabaseUrl) console.error('⚠️ SUPABASE_URL não definido');
if (!supabaseServiceRoleKey) console.error('⚠️ SUPABASE_SERVICE_ROLE_KEY não definido');

// ========== CLIENTES ==========
const stripe = new Stripe(stripeApiKey, {
  apiVersion: '2024-11-20',
});

// Obrigatório em Deno para verificar assinatura do webhook
const cryptoProvider = Stripe.createSubtleCryptoProvider();

const supabase = createClient(supabaseUrl, supabaseServiceRoleKey, {
  auth: { persistSession: false },
});

// ========== TIPOS / HELPERS ==========
type SubscriptionStatus =
  | 'trialing'
  | 'active'
  | 'past_due'
  | 'canceled'
  | 'unpaid'
  | 'incomplete'
  | 'incomplete_expired'
  | 'paused';

function unixToIso(sec: number | null | undefined): string | null {
  if (!sec) return null;
  return new Date(sec * 1000).toISOString();
}

// ========== FUNÇÕES DE SINCRONIZAÇÃO ==========

// 1) checkout.session.completed
// - Assume que você criou a Checkout Session com metadata.user_id
// - Busca a Subscription completa via Stripe para pegar price + períodos
async function upsertFromCheckoutSession(session: Stripe.Checkout.Session) {
  const userId = session.metadata?.user_id; // deve ser o UUID do usuário no Supabase

  const stripeSubscriptionId = session.subscription as string | null;

  if (!userId || !stripeSubscriptionId) {
    console.warn('💡 checkout.session.completed sem user_id ou subscription_id → ignorando', {
      userId,
      stripeSubscriptionId,
    });
    return;
  }

  // Busca a assinatura completa no Stripe
  const subscription = await stripe.subscriptions.retrieve(stripeSubscriptionId);

  const priceId = subscription.items?.data?.[0]?.price?.id ?? null;
  if (!priceId) {
    console.error('❌ Subscription sem price_id (stripe_price_id) – verifique seus produtos/preços no Stripe.', {
      stripeSubscriptionId,
    });
    throw new Error('Missing stripe_price_id');
  }

  const currentPeriodStartIso =
    unixToIso(subscription.current_period_start) ?? new Date().toISOString();
  const currentPeriodEndIso =
    unixToIso(subscription.current_period_end) ?? new Date().toISOString();

  const status = subscription.status as SubscriptionStatus;

  const nowIso = new Date().toISOString();

  const payload = {
    user_id: userId,
    stripe_subscription_id: stripeSubscriptionId,
    stripe_price_id: priceId,
    status,
    current_period_start: currentPeriodStartIso,
    current_period_end: currentPeriodEndIso,
    cancel_at_period_end: subscription.cancel_at_period_end ?? false,
    updated_at: nowIso,
  };

  const { error } = await supabase
    .from('subscriptions')
    .upsert(payload, { onConflict: 'stripe_subscription_id' });

  if (error) {
    console.error('❌ Erro ao upsert subscription (checkout.session.completed):', error);
  } else {
    console.log('✅ Subscription upserted via checkout.session.completed', {
      user_id: userId,
      stripe_subscription_id: stripeSubscriptionId,
      stripe_price_id: priceId,
      status,
    });
  }
}

// 2) customer.subscription.created / updated
async function updateFromStripeSubscription(subscription: Stripe.Subscription) {
  const stripeSubscriptionId = subscription.id;
  const priceId = subscription.items?.data?.[0]?.price?.id ?? null;

  if (!priceId) {
    console.error('❌ Subscription sem price_id (stripe_price_id) em customer.subscription.updated', {
      stripeSubscriptionId,
    });
    throw new Error('Missing stripe_price_id');
  }

  const status = subscription.status as SubscriptionStatus;

  const currentPeriodStartIso =
    unixToIso(subscription.current_period_start) ?? new Date().toISOString();
  const currentPeriodEndIso =
    unixToIso(subscription.current_period_end) ?? new Date().toISOString();

  const payload = {
    stripe_price_id: priceId,
    status,
    current_period_start: currentPeriodStartIso,
    current_period_end: currentPeriodEndIso,
    cancel_at_period_end: subscription.cancel_at_period_end ?? false,
    updated_at: new Date().toISOString(),
  };

  const { error, data } = await supabase
    .from('subscriptions')
    .update(payload)
    .eq('stripe_subscription_id', stripeSubscriptionId)
    .select('id, user_id')
    .maybeSingle();

  if (error) {
    console.error('❌ Erro ao atualizar subscription (customer.subscription.updated):', error);
    return;
  }

  console.log('✅ Subscription atualizada a partir do Stripe', {
    stripe_subscription_id: stripeSubscriptionId,
    stripe_price_id: priceId,
    status,
    subscription_row_id: data?.id,
    user_id: data?.user_id,
  });
}

// 3) customer.subscription.deleted (cancelamento)
async function markSubscriptionCanceled(subscription: Stripe.Subscription) {
  const stripeSubscriptionId = subscription.id;

  const currentPeriodStartIso =
    unixToIso(subscription.current_period_start) ?? new Date().toISOString();
  const currentPeriodEndIso =
    unixToIso(subscription.current_period_end) ?? new Date().toISOString();

  const payload = {
    status: 'canceled' as SubscriptionStatus,
    current_period_start: currentPeriodStartIso,
    current_period_end: currentPeriodEndIso,
    cancel_at_period_end: subscription.cancel_at_period_end ?? false,
    updated_at: new Date().toISOString(),
  };

  const { error, data } = await supabase
    .from('subscriptions')
    .update(payload)
    .eq('stripe_subscription_id', stripeSubscriptionId)
    .select('id, user_id')
    .maybeSingle();

  if (error) {
    console.error('❌ Erro ao marcar subscription como cancelada:', error);
    return;
  }

  console.log('✅ Subscription marcada como cancelada', {
    stripe_subscription_id: stripeSubscriptionId,
    subscription_row_id: data?.id,
    user_id: data?.user_id,
  });

  // Aqui você pode (em outra função/flow) fazer downgrade de permissões do usuário.
}

// ========== HANDLER PRINCIPAL ==========
Deno.serve(async (request: Request): Promise<Response> => {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }

  const signature = request.headers.get('Stripe-Signature');
  if (!signature) {
    console.error('❌ Header Stripe-Signature ausente');
    return new Response('Missing Stripe-Signature header', { status: 400 });
  }

  const body = await request.text(); // RAW body

  let event: Stripe.Event;

  try {
    event = await stripe.webhooks.constructEventAsync(
      body,
      signature,
      stripeWebhookSecret,
      undefined,
      cryptoProvider,
    );
  } catch (err: any) {
    console.error('❌ Stripe signature error:', {
      message: err?.message,
    });
    return new Response(`Webhook Error: ${err?.message}`, {
      status: 400,
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
    });
  }

  console.log(`✅ Event received: ${event.type} (${event.id})`);

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        await upsertFromCheckoutSession(session);
        break;
      }

      case 'customer.subscription.created':
      case 'customer.subscription.updated': {
        const subscription = event.data.object as Stripe.Subscription;
        await updateFromStripeSubscription(subscription);
        break;
      }

      case 'customer.subscription.deleted': {
        const subscription = event.data.object as Stripe.Subscription;
        await markSubscriptionCanceled(subscription);
        break;
      }

      case 'invoice.payment_failed': {
        const invoice = event.data.object as Stripe.Invoice;
        console.warn('⚠️ Pagamento de fatura falhou', {
          invoice: invoice.id,
          customer: invoice.customer,
          subscription: invoice.subscription,
        });
        break;
      }

      default:
        console.log('ℹ️ Evento não tratado explicitamente:', event.type);
        break;
    }

    return new Response(JSON.stringify({ ok: true, eventType: event.type }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (err: any) {
    console.error('❌ Erro interno ao processar evento Stripe:', err);
    return new Response(
      JSON.stringify({ error: err?.message ?? 'Unknown error' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      },
    );
  }
});
