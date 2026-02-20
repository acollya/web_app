// Supabase Edge Function: create-checkout
// Cria uma Stripe Checkout Session para assinatura (subscription)

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import Stripe from 'https://esm.sh/stripe@14.21.0';

// ====== ENV VARS ======
const stripeApiKey = Deno.env.get('STRIPE_API_KEY') || ''; // <-- MESMO NOME DO WEBHOOK
const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

if (!stripeApiKey) console.error('⚠️ STRIPE_API_KEY não definido');
if (!supabaseUrl) console.error('⚠️ SUPABASE_URL não definido');
if (!supabaseServiceKey) console.error('⚠️ SUPABASE_SERVICE_ROLE_KEY não definido');

// ====== CLIENTES ======
const stripe = new Stripe(stripeApiKey, {
  apiVersion: '2024-11-20', // mesma versão do webhook
  httpClient: Stripe.createFetchHttpClient(),
});

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req: Request): Promise<Response> => {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  if (req.method !== 'POST') {
    return new Response('Method not allowed', {
      status: 405,
      headers: corsHeaders,
    });
  }

  try {
    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      global: {
        headers: {
          // repassa tokens caso existam (boa prática p/ auth)
          Authorization: req.headers.get('Authorization') ?? '',
          apikey: req.headers.get('apikey') ?? '',
        },
      },
    });

    // ---------- Segurança: obter userId autenticado ----------
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Usuário não autenticado' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    const userId = user.id; // UUID do Supabase (vai bater com o webhook)

    // ---------- Body da requisição ----------
    const body = await req.json().catch(() => ({} as any));
    const { priceId, successUrl, cancelUrl } = body as {
      priceId?: string;
      successUrl?: string;
      cancelUrl?: string;
    };

    if (!priceId) {
      return new Response(
        JSON.stringify({ error: 'priceId é obrigatório' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // ---------- Buscar dados do usuário ----------
    const { data: userRow, error: userError } = await supabase
      .from('users')
      .select('email, stripe_customer_id')
      .eq('id', userId)
      .single();

    if (userError || !userRow) {
      console.error('Erro ao buscar usuário:', userError);
      return new Response(
        JSON.stringify({ error: 'Usuário não encontrado' }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } },
      );
    }

    // ---------- Criar ou usar customer do Stripe ----------
    let customerId = userRow.stripe_customer_id as string | null;

    if (!customerId) {
      const customer = await stripe.customers.create({
        email: userRow.email,
        metadata: {
          supabase_user_id: userId,
        },
      });

      customerId = customer.id;

      const { error: updateError } = await supabase
        .from('users')
        .update({ stripe_customer_id: customerId })
        .eq('id', userId);

      if (updateError) {
        console.error('Erro ao salvar stripe_customer_id no usuário:', updateError);
      }
    }

    // ---------- Criar Checkout Session ----------
    const origin = req.headers.get('origin') || '';

    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      success_url: successUrl || `${origin}/subscription?success=true`,
      cancel_url: cancelUrl || `${origin}/subscription?canceled=true`,
      metadata: {
        user_id: userId,       // <-- usado no stripe-webhook (checkout.session.completed)
      },
      subscription_data: {
        metadata: {
          user_id: userId,     // <-- também fica na Subscription
        },
      },
    });

    return new Response(
      JSON.stringify({
        sessionId: session.id,
        url: session.url,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  } catch (error: any) {
    console.error('Error creating checkout session:', error);
    return new Response(
      JSON.stringify({ error: error?.message ?? 'Unknown error' }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  }
});
