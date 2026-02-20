/**
 * Supabase Edge Function: mood-checkin
 * Processar check-ins de humor com análise IA usando OpenAI
 */

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ========================================
// INTERFACES
// ========================================

interface RequestBody {
  userId: string;
  mood: string;
  intensity: number;
  note?: string;
  activities?: string[];
  generateInsight?: boolean;
}

interface MoodCheckin {
  id: string;
  user_id: string;
  mood: string;
  intensity: number;
  note?: string;
  created_at: string;
}

interface MoodCheckinResponse {
  success: boolean;
  checkin: {
    id: string;
    mood: string;
    intensity: number;
    note?: string;
    createdAt: string;
  };
  insight?: string;
  message: string;
}

// ========================================
// CONFIGURATION
// ========================================

const OPENAI_API_KEY = Deno.env.get('OPENAI_MOOD_API_KEY');
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;

if (!OPENAI_API_KEY) {
  console.warn('⚠️ OPENAI_MOOD_API_KEY não definido - insights IA desabilitados');
}

// ========================================
// MOOD DESCRIPTIONS
// ========================================

const MOOD_DESCRIPTIONS: Record<string, string> = {
  'muito-feliz': 'muito feliz e animado',
  'feliz': 'feliz e contente',
  'neutro': 'neutro, sem emoções fortes',
  'triste': 'triste e desanimado',
  'muito-triste': 'muito triste e deprimido',
  'ansioso': 'ansioso e preocupado',
  'calmo': 'calmo e tranquilo',
  'irritado': 'irritado e frustrado',
  'animado': 'animado e entusiasmado',
};

// ========================================
// FALLBACK INSIGHTS
// ========================================

const FALLBACK_INSIGHTS: Record<string, string[]> = {
  'muito-feliz': [
    'Que maravilha ver você tão feliz! 🌟 Aproveite esse momento e tente identificar o que contribuiu para esse sentimento positivo.',
    'Sua energia positiva é contagiante! Continue cultivando esses momentos de alegria e compartilhe-os com quem você ama.',
  ],
  'feliz': [
    'É ótimo saber que você está se sentindo bem! 😊 Momentos assim são preciosos - aproveite e celebre suas conquistas.',
    'Que bom ver você feliz! Continue fazendo o que está funcionando para você e lembre-se de agradecer por esses momentos.',
  ],
  'neutro': [
    'Está tudo bem sentir-se neutro às vezes. É um momento de equilíbrio. Que tal fazer algo que normalmente te traz alegria?',
    'Dias neutros fazem parte da vida. Use esse momento para refletir sobre o que você gostaria de sentir e como chegar lá.',
  ],
  'triste': [
    'Percebo que você está passando por um momento difícil. 💙 Suas emoções são válidas. Que tal conversar com alguém de confiança ou fazer algo que te conforta?',
    'É corajoso reconhecer quando não estamos bem. Lembre-se: sentimentos difíceis são temporários. Seja gentil consigo mesmo hoje.',
  ],
  'muito-triste': [
    'Sinto muito que você esteja se sentindo assim. 💙 Você não está sozinho. Considere conversar com um profissional ou alguém próximo. Pequenos passos são válidos.',
    'Reconheço que este é um momento muito difícil para você. Por favor, seja gentil consigo mesmo e busque apoio. Você merece cuidado e compreensão.',
  ],
  'ansioso': [
    'A ansiedade pode ser desafiadora. 🌿 Tente fazer algumas respirações profundas e focar no momento presente. Você está seguro agora.',
    'Percebo sua ansiedade. Lembre-se: você já superou momentos difíceis antes. Tente uma técnica de relaxamento ou uma caminhada curta.',
  ],
  'calmo': [
    'Que paz! 🌊 Aproveite esse estado de calma e tente identificar o que contribuiu para isso. Esses momentos são valiosos para recarregar.',
    'É maravilhoso estar em paz. Continue cultivando práticas que te trazem tranquilidade e equilíbrio.',
  ],
  'irritado': [
    'A frustração é uma emoção válida. 🔥 Tente identificar o que está te incomodando e se há algo que você pode fazer sobre isso. Respirar fundo pode ajudar.',
    'Percebo sua irritação. Às vezes, dar um tempo e voltar depois com a mente mais clara pode fazer toda a diferença.',
  ],
  'animado': [
    'Sua energia está contagiante! ⚡ Aproveite esse entusiasmo para fazer algo que você ama ou começar aquele projeto que estava adiando.',
    'Que animação! Use essa energia positiva a seu favor e lembre-se de também descansar quando precisar.',
  ],
};

// ========================================
// HELPER FUNCTIONS
// ========================================

/**
 * Get fallback insight based on mood and intensity
 */
function getFallbackInsight(mood: string, intensity: number): string {
  const insights = FALLBACK_INSIGHTS[mood] || [
    'Obrigado por compartilhar como você está se sentindo. Continue registrando seus momentos para acompanhar seu bem-estar. 💙',
  ];

  // Select insight based on intensity
  const index = intensity > 5 ? 0 : (insights.length > 1 ? 1 : 0);
  return insights[index];
}

/**
 * Generate AI insight using OpenAI
 */
async function generateAIInsight(
  mood: string,
  intensity: number,
  note?: string,
  activities?: string[]
): Promise<string> {
  if (!OPENAI_API_KEY) {
    console.log('OpenAI API Key não disponível');
    return getFallbackInsight(mood, intensity);
  }

  try {
    // Build rich context for the prompt
    const moodDescription = MOOD_DESCRIPTIONS[mood] || mood;
    const intensityLevel = intensity <= 3 ? 'baixa' : (intensity <= 6 ? 'média' : 'alta');

    const contextParts: string[] = [
      `Humor: ${moodDescription}`,
      `Intensidade: ${intensity}/10 (${intensityLevel})`,
    ];

    if (note && note.trim()) {
      contextParts.push(`Descrição: "${note}"`);
    }

    if (activities && activities.length > 0) {
      contextParts.push(`Atividades/Emoções secundárias: ${activities.join(', ')}`);
    }

    const context = contextParts.join('\n');

    // Create detailed prompt in Brazilian Portuguese
    const systemPrompt = `Você é Acollya, uma assistente de saúde mental empática e acolhedora. Sua função é fornecer insights personalizados sobre o estado emocional do usuário.

Diretrizes:
- Use linguagem calorosa, empática e encorajadora
- Reconheça e valide os sentimentos do usuário
- Identifique possíveis padrões ou gatilhos emocionais
- Ofereça 1-2 sugestões práticas e acionáveis
- Mantenha o tom positivo e esperançoso, mesmo em situações difíceis
- Seja conciso (máximo 4-5 frases)
- Use português brasileiro natural e acessível`;

    const userPrompt = `Analise este check-in de humor e forneça um insight personalizado:

${context}

Forneça:
1. Reconhecimento empático do estado atual
2. Um insight sobre o que pode estar influenciando esse humor
3. Uma sugestão prática e acionável para o momento
4. Uma mensagem de encorajamento`;

    console.log('🤖 Gerando insight com OpenAI...');

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: systemPrompt,
          },
          {
            role: 'user',
            content: userPrompt,
          },
        ],
        max_tokens: 250,
        temperature: 0.8,
        presence_penalty: 0.3,
        frequency_penalty: 0.3,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`OpenAI API error: ${error}`);
    }

    const data = await response.json();
    const insight = data.choices[0]?.message?.content?.trim();

    if (!insight) {
      throw new Error('No insight generated');
    }

    console.log('✅ Insight gerado com sucesso');
    return insight;

  } catch (error) {
    console.error('❌ Erro ao gerar insight IA:', error);
    return getFallbackInsight(mood, intensity);
  }
}

// ========================================
// MAIN HANDLER
// ========================================

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      },
    });
  }

  // Only allow POST
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  }

  try {
    // Get auth headers
    const authHeader = req.headers.get('Authorization') || '';
    const apikeyHeader = req.headers.get('apikey') || '';

    // Create Supabase client
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
      auth: {
        persistSession: false,
      },
      global: {
        headers: {
          Authorization: authHeader,
          apikey: apikeyHeader,
        },
      },
    });

    // Verify authentication
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      console.error('❌ Erro de autenticação:', authError);
      return new Response(JSON.stringify({ error: 'Usuário não autenticado' }), {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // Parse request body
    let body: RequestBody;
    try {
      body = await req.json();
    } catch (e) {
      return new Response(JSON.stringify({ error: 'JSON inválido' }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    const { userId, mood, intensity, note, activities, generateInsight = false } = body;

    // Validate required fields
    if (!userId || !mood || intensity === undefined || intensity === null) {
      return new Response(
        JSON.stringify({ error: 'userId, mood e intensity são obrigatórios' }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    }

    // Verify authorization
    if (user.id !== userId) {
      return new Response(JSON.stringify({ error: 'Não autorizado' }), {
        status: 403,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // Validate intensity (1-10)
    if (typeof intensity !== 'number' || intensity < 1 || intensity > 10) {
      return new Response(
        JSON.stringify({ error: 'intensity deve estar entre 1 e 10' }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    }

    const now = new Date().toISOString();

    // Save check-in to database
    let checkin: MoodCheckin;
    try {
      const checkinData = {
        user_id: userId,
        mood,
        intensity,
        note: note || null,
        created_at: now,
      };

      const { data, error } = await supabase
        .from('mood_checkins')
        .insert(checkinData)
        .select()
        .single();

      if (error) {
        throw error;
      }

      if (!data) {
        throw new Error('Nenhum dado retornado após inserção');
      }

      checkin = data as MoodCheckin;
      console.log(`✅ Check-in salvo: ${checkin.id}`);

    } catch (checkinError) {
      console.error('❌ Erro ao salvar check-in:', checkinError);
      throw new Error('Erro ao salvar check-in de humor');
    }

    // Generate AI insight if requested
    let insight: string | undefined;
    if (generateInsight) {
      console.log('🤖 Gerando insight IA...');
      insight = await generateAIInsight(mood, intensity, note, activities);
    }

    // Build response
    const response: MoodCheckinResponse = {
      success: true,
      checkin: {
        id: checkin.id,
        mood: checkin.mood,
        intensity: checkin.intensity,
        note: checkin.note,
        createdAt: checkin.created_at,
      },
      insight,
      message: 'Check-in de humor registrado com sucesso! 💙',
    };

    return new Response(JSON.stringify(response), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('❌ Erro interno:', errorMessage);

    return new Response(
      JSON.stringify({
        error: errorMessage,
        success: false,
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    );
  }
});