// Supabase Edge Function: appointment-booking
// Gerenciar agendamentos de consultas com terapeutas

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
  therapistId: string;
  date: string;
  time: string;
  action?: 'create' | 'cancel';
  appointmentId?: string;
}

interface AppointmentDetails {
  id: string;
  userId: string;
  therapistId: string;
  therapistName: string;
  date: string;
  time: string;
  status: string;
  meetLink: string;
  amount: number;
  createdAt: string;
}

// ========== FUNÇÕES AUXILIARES ==========
function generateMeetLink(appointmentId: string): string {
  // Em produção, você integraria com Google Meet API
  // Por enquanto, geramos um link mock
  const meetCode = `acollya-${appointmentId.substring(0, 8)}`;
  return `https://meet.google.com/${meetCode}`;
}

function isValidDateTime(date: string, time: string): boolean {
  try {
    const appointmentDate = new Date(`${date}T${time}`);
    const now = new Date();

    // Verificar se é uma data futura
    if (appointmentDate <= now) {
      return false;
    }

    // Verificar se é dentro de horário comercial (8h-20h)
    const hour = parseInt(time.split(':')[0]);
    if (hour < 8 || hour >= 20) {
      return false;
    }

    return true;
  } catch {
    return false;
  }
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
    const { userId, therapistId, date, time, action = 'create', appointmentId } = body;

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

    // Ação: Cancelar agendamento
    if (action === 'cancel') {
      if (!appointmentId) {
        return new Response(
          JSON.stringify({ error: 'appointmentId é obrigatório para cancelamento' }),
          {
            status: 400,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          },
        );
      }

      const { error: cancelError } = await supabase
        .from('appointments')
        .update({
          status: 'cancelled',
          updated_at: new Date().toISOString(),
        })
        .eq('id', appointmentId)
        .eq('user_id', userId);

      if (cancelError) {
        console.error('Erro ao cancelar agendamento:', cancelError);
        throw new Error('Erro ao cancelar agendamento');
      }

      return new Response(
        JSON.stringify({
          success: true,
          message: 'Agendamento cancelado com sucesso',
        }),
        {
          status: 200,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Ação: Criar agendamento
    if (!therapistId || !date || !time) {
      return new Response(
        JSON.stringify({ error: 'therapistId, date e time são obrigatórios' }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Validar data e hora
    if (!isValidDateTime(date, time)) {
      return new Response(
        JSON.stringify({
          error:
            'Data/hora inválida. Escolha uma data futura dentro do horário comercial (8h-20h)',
        }),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Verificar disponibilidade (se já existe agendamento nesse horário)
    const { data: existingAppointments, error: checkError } = await supabase
      .from('appointments')
      .select('id')
      .eq('therapist_id', therapistId)
      .eq('date', date)
      .eq('time', time)
      .neq('status', 'cancelled');

    if (checkError) {
      console.error('Erro ao verificar disponibilidade:', checkError);
      throw new Error('Erro ao verificar disponibilidade');
    }

    if (existingAppointments && existingAppointments.length > 0) {
      return new Response(
        JSON.stringify({
          error: 'Este horário não está disponível. Por favor, escolha outro.',
        }),
        {
          status: 409,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        },
      );
    }

    // Buscar informações do terapeuta (mock)
    // Em produção, você buscaria de uma tabela de terapeutas
    const therapistName = 'Dra. Ana Silva'; // Mock
    const hourlyRate = 150; // Mock

    const now = new Date().toISOString();

    // Criar agendamento
    const { data: appointment, error: createError } = await supabase
      .from('appointments')
      .insert({
        user_id: userId,
        therapist_id: therapistId,
        date,
        time,
        amount: hourlyRate,
        status: 'pending',
        payment_status: 'pending',
        created_at: now,
        updated_at: now,
      })
      .select()
      .single();

    if (createError) {
      console.error('Erro ao criar agendamento:', createError);
      throw new Error('Erro ao criar agendamento');
    }

    // Gerar link do Google Meet
    const meetLink = generateMeetLink(appointment.id);

    // Atualizar com o link do Meet
    await supabase
      .from('appointments')
      .update({ meet_link: meetLink })
      .eq('id', appointment.id);

    const appointmentDetails: AppointmentDetails = {
      id: appointment.id,
      userId: appointment.user_id,
      therapistId: appointment.therapist_id,
      therapistName,
      date: appointment.date,
      time: appointment.time,
      status: appointment.status,
      meetLink,
      amount: appointment.amount,
      createdAt: appointment.created_at,
    };

    return new Response(
      JSON.stringify({
        success: true,
        appointment: appointmentDetails,
        message: 'Agendamento criado com sucesso! 📅',
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