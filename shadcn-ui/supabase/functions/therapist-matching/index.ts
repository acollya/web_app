// Supabase Edge Function: therapist-matching
// Algoritmo de matching inteligente de terapeutas baseado em preferências do usuário

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
interface MatchingAnswers {
  preferredGender?: 'male' | 'female' | 'any';
  specializations?: string[];
  ageRange?: 'young' | 'middle' | 'senior' | 'any';
  approach?: string[];
  language?: string[];
  availability?: 'morning' | 'afternoon' | 'evening' | 'any';
  budget?: 'low' | 'medium' | 'high' | 'any';
}

interface RequestBody {
  userId: string;
  answers: MatchingAnswers;
}

interface TherapistScore {
  id: string;
  name: string;
  specialization: string;
  bio: string;
  rating: number;
  hourlyRate: number;
  score: number;
  matchReasons: string[];
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
    const { userId, answers } = body;

    if (!userId || !answers) {
      return new Response(
        JSON.stringify({ error: 'userId e answers são obrigatórios' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Verificar se o usuário autenticado é o mesmo do request
    if (user.id !== userId) {
      return new Response(
        JSON.stringify({ error: 'Não autorizado' }),
        {
          status: 403,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Buscar todos os terapeutas (em produção, isso seria uma tabela real)
    // Por enquanto, vamos usar dados mock
    const mockTherapists = [
      {
        id: '1',
        name: 'Dra. Ana Silva',
        gender: 'female',
        specialization: 'Ansiedade e Depressão',
        specializations: ['ansiedade', 'depressão', 'terapia cognitivo-comportamental'],
        bio: 'Especialista em TCC com 10 anos de experiência',
        rating: 4.8,
        hourlyRate: 150,
        age: 'middle',
        approach: ['TCC', 'Mindfulness'],
        language: ['português', 'inglês'],
        availability: ['morning', 'afternoon'],
      },
      {
        id: '2',
        name: 'Dr. Carlos Santos',
        gender: 'male',
        specialization: 'Relacionamentos',
        specializations: ['relacionamentos', 'terapia de casal', 'comunicação'],
        bio: 'Terapeuta de casais e famílias',
        rating: 4.6,
        hourlyRate: 180,
        age: 'senior',
        approach: ['Sistêmica', 'Humanista'],
        language: ['português'],
        availability: ['afternoon', 'evening'],
      },
      {
        id: '3',
        name: 'Dra. Maria Oliveira',
        gender: 'female',
        specialization: 'Trauma e TEPT',
        specializations: ['trauma', 'TEPT', 'EMDR'],
        bio: 'Especialista em EMDR e trauma',
        rating: 4.9,
        hourlyRate: 200,
        age: 'middle',
        approach: ['EMDR', 'Psicodinâmica'],
        language: ['português', 'espanhol'],
        availability: ['morning', 'evening'],
      },
      {
        id: '4',
        name: 'Dr. João Costa',
        gender: 'male',
        specialization: 'Ansiedade Social',
        specializations: ['ansiedade social', 'fobia', 'TCC'],
        bio: 'Especialista em fobias e ansiedade social',
        rating: 4.7,
        hourlyRate: 140,
        age: 'young',
        approach: ['TCC', 'Exposição'],
        language: ['português'],
        availability: ['morning', 'afternoon', 'evening'],
      },
    ];

    // Calcular scores de compatibilidade
    const scoredTherapists: TherapistScore[] = mockTherapists.map((therapist) => {
      let score = 0;
      const matchReasons: string[] = [];

      // Gênero preferido (peso: 10)
      if (answers.preferredGender && answers.preferredGender !== 'any') {
        if (therapist.gender === answers.preferredGender) {
          score += 10;
          matchReasons.push('Gênero preferido');
        }
      } else {
        score += 5; // Bonus por aceitar qualquer gênero
      }

      // Especializações (peso: 30)
      if (answers.specializations && answers.specializations.length > 0) {
        const matchingSpecs = therapist.specializations.filter((spec) =>
          answers.specializations!.some((userSpec) =>
            spec.toLowerCase().includes(userSpec.toLowerCase())
          )
        );
        if (matchingSpecs.length > 0) {
          score += 30 * (matchingSpecs.length / answers.specializations.length);
          matchReasons.push(`Especialização em ${matchingSpecs.join(', ')}`);
        }
      }

      // Faixa etária (peso: 5)
      if (answers.ageRange && answers.ageRange !== 'any') {
        if (therapist.age === answers.ageRange) {
          score += 5;
          matchReasons.push('Faixa etária preferida');
        }
      }

      // Abordagem terapêutica (peso: 20)
      if (answers.approach && answers.approach.length > 0) {
        const matchingApproaches = therapist.approach.filter((app) =>
          answers.approach!.some((userApp) =>
            app.toLowerCase().includes(userApp.toLowerCase())
          )
        );
        if (matchingApproaches.length > 0) {
          score += 20 * (matchingApproaches.length / answers.approach.length);
          matchReasons.push(`Abordagem: ${matchingApproaches.join(', ')}`);
        }
      }

      // Idioma (peso: 10)
      if (answers.language && answers.language.length > 0) {
        const matchingLanguages = therapist.language.filter((lang) =>
          answers.language!.includes(lang)
        );
        if (matchingLanguages.length > 0) {
          score += 10;
          matchReasons.push(`Idioma: ${matchingLanguages.join(', ')}`);
        }
      }

      // Disponibilidade (peso: 10)
      if (answers.availability && answers.availability !== 'any') {
        if (therapist.availability.includes(answers.availability)) {
          score += 10;
          matchReasons.push(`Disponível no período: ${answers.availability}`);
        }
      }

      // Orçamento (peso: 15)
      if (answers.budget && answers.budget !== 'any') {
        const budgetRanges = {
          low: [0, 120],
          medium: [120, 180],
          high: [180, Infinity],
        };
        const [min, max] = budgetRanges[answers.budget];
        if (therapist.hourlyRate >= min && therapist.hourlyRate < max) {
          score += 15;
          matchReasons.push('Dentro do orçamento');
        }
      }

      // Bonus por avaliação alta (peso: 10)
      score += therapist.rating * 2;

      return {
        id: therapist.id,
        name: therapist.name,
        specialization: therapist.specialization,
        bio: therapist.bio,
        rating: therapist.rating,
        hourlyRate: therapist.hourlyRate,
        score: Math.round(score),
        matchReasons,
      };
    });

    // Ordenar por score (maior primeiro)
    scoredTherapists.sort((a, b) => b.score - a.score);

    // Retornar top 3
    const topMatches = scoredTherapists.slice(0, 3);

    return new Response(
      JSON.stringify({
        success: true,
        matches: topMatches,
        totalAnalyzed: mockTherapists.length,
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