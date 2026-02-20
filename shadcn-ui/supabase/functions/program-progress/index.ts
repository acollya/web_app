// Supabase Edge Function: program-progress
// Atualizar e gerenciar progresso em programas de autocuidado

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
  programId: string;
  chapterId: string;
  action: 'complete' | 'reset';
}

interface ProgramProgress {
  totalChapters: number;
  completedChapters: number;
  percentageComplete: number;
  lastUpdated: string;
  chapters: Array<{
    id: string;
    completed: boolean;
    completedAt?: string;
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
    const { userId, programId, chapterId, action } = body;

    if (!userId || !programId || !chapterId || !action) {
      return new Response(
        JSON.stringify({ error: 'userId, programId, chapterId e action são obrigatórios' }),
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

    // Validar action
    if (action !== 'complete' && action !== 'reset') {
      return new Response(
        JSON.stringify({ error: 'action deve ser "complete" ou "reset"' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    const now = new Date().toISOString();

    // Atualizar progresso no banco
    const { error: upsertError } = await supabase.from('program_progress').upsert(
      {
        user_id: userId,
        program_id: programId,
        chapter_id: chapterId,
        completed: action === 'complete',
        completed_at: action === 'complete' ? now : null,
        updated_at: now,
      },
      {
        onConflict: 'user_id,program_id,chapter_id',
      }
    );

    if (upsertError) {
      console.error('Erro ao atualizar progresso:', upsertError);
      throw new Error('Erro ao atualizar progresso');
    }

    // Buscar todo o progresso do programa
    const { data: allProgress, error: progressError } = await supabase
      .from('program_progress')
      .select('*')
      .eq('user_id', userId)
      .eq('program_id', programId);

    if (progressError) {
      console.error('Erro ao buscar progresso:', progressError);
      throw new Error('Erro ao buscar progresso');
    }

    // Calcular estatísticas
    // Em produção, você buscaria o número total de capítulos do programa
    // Por enquanto, vamos usar um valor fixo
    const totalChapters = 10; // Mock: assumir 10 capítulos por programa

    const completedChapters = allProgress?.filter((p: any) => p.completed).length || 0;
    const percentageComplete = Math.round((completedChapters / totalChapters) * 100);

    const chapters = allProgress?.map((p: any) => ({
      id: p.chapter_id,
      completed: p.completed,
      completedAt: p.completed_at,
    })) || [];

    const progress: ProgramProgress = {
      totalChapters,
      completedChapters,
      percentageComplete,
      lastUpdated: now,
      chapters,
    };

    return new Response(
      JSON.stringify({
        success: true,
        progress,
        message:
          action === 'complete'
            ? 'Capítulo marcado como concluído! 🎉'
            : 'Progresso resetado.',
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