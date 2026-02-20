// Supabase Edge Function: mood-insights
// Gerar insights e análises do histórico de check-ins de humor

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ========== ENV VARS ==========
const supabaseUrl = Deno.env.get('SUPABASE_URL') as string;
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') as string;

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
  userId: string;
  period: 'week' | 'month' | 'year';
}

interface MoodCheckin {
  id: string;
  mood: string;
  intensity: number;
  note?: string;
  created_at: string;
}

interface MoodInsights {
  period: string;
  totalCheckins: number;
  averageMood: number;
  moodDistribution: Record<string, number>;
  trends: string[];
  recommendations: string[];
  mostCommonMood: string;
  moodImprovement: number;
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
    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      global: {
        headers: {
          Authorization: req.headers.get('Authorization') ?? '',
          apikey: req.headers.get('apikey') ?? '',
        },
      },
    });

    // Verificar autenticação
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

    // Parse body
    const body = (await req.json()) as RequestBody;
    const { userId, period } = body;

    if (!userId || !period) {
      return new Response(
        JSON.stringify({ error: 'userId e period são obrigatórios' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Verificar autorização
    if (user.id !== userId) {
      return new Response(
        JSON.stringify({ error: 'Não autorizado' }),
        {
          status: 403,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Calcular data de início baseada no período
    const now = new Date();
    let startDate: Date;

    switch (period) {
      case 'week':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case 'month':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case 'year':
        startDate = new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000);
        break;
      default:
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    }

    // Buscar check-ins do período
    const { data: checkins, error: checkinsError } = await supabase
      .from('mood_checkins')
      .select('*')
      .eq('user_id', userId)
      .gte('created_at', startDate.toISOString())
      .order('created_at', { ascending: true });

    if (checkinsError) {
      console.error('Erro ao buscar check-ins:', checkinsError);
      throw new Error('Erro ao buscar histórico de humor');
    }

    if (!checkins || checkins.length === 0) {
      return new Response(
        JSON.stringify({
          success: true,
          insights: {
            period,
            totalCheckins: 0,
            message: 'Sem dados suficientes para gerar insights. Comece a registrar seu humor!',
          },
        }),
        {
          status: 200,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Analisar dados
    const moodDistribution: Record<string, number> = {};
    let totalIntensity = 0;

    checkins.forEach((checkin: MoodCheckin) => {
      // Contar distribuição de humores
      moodDistribution[checkin.mood] = (moodDistribution[checkin.mood] || 0) + 1;
      // Somar intensidades
      totalIntensity += checkin.intensity;
    });

    // Calcular estatísticas
    const totalCheckins = checkins.length;
    const averageMood = totalIntensity / totalCheckins;

    // Encontrar humor mais comum
    const mostCommonMood = Object.entries(moodDistribution).reduce((a, b) =>
      b[1] > a[1] ? b : a
    )[0];

    // Calcular tendência (comparar primeira e segunda metade)
    const midpoint = Math.floor(totalCheckins / 2);
    const firstHalf = checkins.slice(0, midpoint);
    const secondHalf = checkins.slice(midpoint);

    const firstHalfAvg =
      firstHalf.reduce((sum: number, c: MoodCheckin) => sum + c.intensity, 0) / firstHalf.length;
    const secondHalfAvg =
      secondHalf.reduce((sum: number, c: MoodCheckin) => sum + c.intensity, 0) /
      secondHalf.length;

    const moodImprovement = ((secondHalfAvg - firstHalfAvg) / firstHalfAvg) * 100;

    // Gerar insights
    const trends: string[] = [];
    const recommendations: string[] = [];

    if (moodImprovement > 10) {
      trends.push('Seu humor tem melhorado consistentemente! 📈');
      recommendations.push('Continue com as práticas que têm funcionado para você.');
    } else if (moodImprovement < -10) {
      trends.push('Seu humor tem oscilado para baixo recentemente. 📉');
      recommendations.push(
        'Considere conversar com um terapeuta ou praticar atividades de autocuidado.'
      );
    } else {
      trends.push('Seu humor tem se mantido estável. ➡️');
      recommendations.push('Mantenha suas rotinas saudáveis e continue monitorando seu bem-estar.');
    }

    // Análise de frequência
    if (totalCheckins < 7 && period === 'week') {
      recommendations.push('Tente registrar seu humor diariamente para insights mais precisos.');
    }

    // Análise de humor predominante
    const moodMessages: Record<string, string> = {
      feliz: 'Você tem se sentido predominantemente feliz! Continue cultivando essa positividade. 😊',
      ansioso:
        'Ansiedade tem sido frequente. Considere técnicas de respiração e mindfulness. 🧘',
      triste:
        'Tristeza tem sido comum. Não hesite em buscar apoio profissional se precisar. 💙',
      estressado:
        'Estresse tem sido recorrente. Priorize momentos de descanso e relaxamento. 🌿',
      calmo: 'Você tem mantido a calma. Ótimo trabalho em gerenciar suas emoções! 🕊️',
    };

    if (moodMessages[mostCommonMood]) {
      trends.push(moodMessages[mostCommonMood]);
    }

    const insights: MoodInsights = {
      period,
      totalCheckins,
      averageMood: Math.round(averageMood * 10) / 10,
      moodDistribution,
      trends,
      recommendations,
      mostCommonMood,
      moodImprovement: Math.round(moodImprovement * 10) / 10,
    };

    return new Response(
      JSON.stringify({
        success: true,
        insights,
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