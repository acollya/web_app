// Supabase Edge Function: create-portal
// Cria uma sessão do Stripe Customer Portal para gerenciamento da assinatura

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import Stripe from 'https://esm.sh/stripe@14.21.0';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ====== ENV VARS ======
const stripeApiKey = Deno.env.get('STRIPE_API_KEY') || ''; // mesmo nome usado no webhook e create-checkout
const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

if (!stripeApiKey) console.error('⚠️ STRIPE_API_KEY não definido');
if (!supabaseUrl) console.error('⚠️ SUPABASE_URL não definido');
if (!supabaseServiceKey) console.error('⚠️ SUPABASE_SERVICE_ROLE_KEY não definido');

// ====== CLIENTES ======
const stripe = new Stripe(stripeApiKey, {
  apiVersion: '2024-11-20', // mesma versão da API do webhook/create-checkout
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
          Authorization: req.headers.get('Authorization') ?? '',
          apikey: req.headers.get('apikey') ?? '',
        },
      },
    });

    // 1) Autenticação – pegar usuário logado
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return new Response(
        JSON.stringify({ error: 'Usuário não autenticado' }),
        {
          status: 401,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    const userId = user.id;

    // 2) Body opcional (apenas returnUrl)
    const body = await req.json().catch(() => ({} as any));
    const { returnUrl } = body as { returnUrl?: string };

    // 3) Buscar stripe_customer_id do usuário no banco
    const { data: userRow, error: userError } = await supabase
      .from('users')
      .select('stripe_customer_id')
      .eq('id', userId)
      .single();

    if (userError || !userRow || !userRow.stripe_customer_id) {
      console.error('Usuário sem stripe_customer_id ao criar portal:', {
        userId,
        userError,
      });
      return new Response(
        JSON.stringify({ error: 'Cliente Stripe não encontrado para este usuário' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    const customerId = userRow.stripe_customer_id as string;

    // 4) Criar sessão do portal
    const origin = req.headers.get('origin') || '';
    const session = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url: returnUrl || `${origin}/subscription`,
    });

    return new Response(
      JSON.stringify({ url: session.url }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  } catch (error: any) {
    console.error('Error creating portal session:', error);
    return new Response(
      JSON.stringify({ error: error?.message ?? 'Unknown error' }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  }
});
