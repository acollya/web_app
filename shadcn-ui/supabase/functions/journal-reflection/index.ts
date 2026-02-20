// Supabase Edge Function: journal-reflection
// Gera reflexão empática usando OpenAI sobre entradas de diário

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ========== ENV VARS ==========
const openaiApiKey = Deno.env.get('OPENAI_API_KEY') as string;
const supabaseUrl = Deno.env.get('SUPABASE_URL') as string;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') as string;

if (!openaiApiKey) console.error('⚠️ OPENAI_API_KEY não definido');
if (!supabaseUrl) console.error('⚠️ SUPABASE_URL não definido');
if (!supabaseServiceKey) console.error('⚠️ SUPABASE_SERVICE_ROLE_KEY não definido');

// ========== CORS HEADERS ==========
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};

// ========== TIPOS ==========
interface RequestBody {
  entryId: string;
  content: string;
  userId: string;
}

interface OpenAIMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface OpenAIResponse {
  choices: Array<{
    message: {
      content: string;
    };
  }>;
}

// ========== FUNÇÃO PRINCIPAL ==========
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
    // 1) Criar cliente Supabase
    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      global: {
        headers: {
          Authorization: req.headers.get('Authorization') ?? '',
          apikey: req.headers.get('apikey') ?? '',
        },
      },
    });

    // 2) Verificar autenticação
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

    // 3) Parse body
    const body = (await req.json()) as RequestBody;
    const { entryId, content, userId } = body;

    if (!entryId || !content || !userId) {
      return new Response(
        JSON.stringify({ error: 'entryId, content e userId são obrigatórios' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // 4) Verificar se o usuário autenticado é o dono da entrada
    if (user.id !== userId) {
      return new Response(
        JSON.stringify({ error: 'Não autorizado a gerar reflexão para esta entrada' }),
        {
          status: 403,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // 5) Buscar dados do usuário para personalização
    const { data: userData, error: userError } = await supabase
      .from('users')
      .select('name')
      .eq('id', userId)
      .single();

    if (userError) {
      console.error('Erro ao buscar dados do usuário:', userError);
    }

    const userName = userData?.name || 'Usuário';

    // 6) Chamar OpenAI API para gerar reflexão
    const systemPrompt = `Você é um terapeuta empático e acolhedor.
Leia a entrada de diário de ${userName} e forneça uma reflexão gentil e encorajadora.
Sua reflexão deve:
- Validar os sentimentos expressos
- Oferecer perspectivas positivas quando apropriado
- Ser breve (2-3 parágrafos)
- Ser calorosa e não julgadora
- Terminar com uma pergunta reflexiva ou encorajamento`;

    const messages: OpenAIMessage[] = [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: `Entrada de diário: "${content}"` },
    ];

    let reflection: string;

    try {
      const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${openaiApiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'gpt-3.5-turbo',
          messages,
          max_tokens: 400,
          temperature: 0.7,
        }),
      });

      if (!openaiResponse.ok) {
        const errorText = await openaiResponse.text();
        console.error('Erro OpenAI API:', errorText);
        throw new Error(`OpenAI API error: ${openaiResponse.status}`);
      }

      const openaiData = (await openaiResponse.json()) as OpenAIResponse;
      reflection = openaiData.choices[0].message.content.trim();
    } catch (openaiError: any) {
      console.error('❌ Erro ao chamar OpenAI API:', openaiError);
      return new Response(
        JSON.stringify({ error: `Erro ao gerar reflexão: ${openaiError?.message}` }),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // 7) Salvar reflexão na tabela journal_entries
    const { error: updateError } = await supabase
      .from('journal_entries')
      .update({
        ai_reflection: reflection,
        updated_at: new Date().toISOString(),
      })
      .eq('id', entryId)
      .eq('user_id', userId); // segurança adicional

    if (updateError) {
      console.error('❌ Erro ao salvar reflexão no banco:', updateError);
      return new Response(
        JSON.stringify({ error: 'Erro ao salvar reflexão no banco de dados' }),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // 8) Retornar reflexão
    return new Response(
      JSON.stringify({
        success: true,
        reflection,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  } catch (error: any) {
    console.error('❌ Erro interno:', error);
    return new Response(
      JSON.stringify({ error: error?.message ?? 'Erro interno desconhecido' }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      },
    );
  }
});