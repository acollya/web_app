import { supabase, isDemoMode } from '@/lib/supabase';

export const supabaseDataService = {
  // Mood Check-ins
  async createMoodCheckin(userId: string, mood: string, intensity: number, note?: string) {
    if (isDemoMode() || !supabase) {
      return { id: `mock_${Date.now()}`, userId, mood, intensity, note, createdAt: new Date().toISOString() };
    }

    const { data, error } = await supabase
      .from('mood_checkins')
      .insert({
        user_id: userId,
        mood,
        intensity,
        note,
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async getMoodCheckins(userId: string, limit = 30) {
    if (isDemoMode() || !supabase) {
      return [];
    }

    const { data, error } = await supabase
      .from('mood_checkins')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) throw error;
    return data || [];
  },

  // Journal Entries
  async createJournalEntry(userId: string, content: string) {
    if (isDemoMode() || !supabase) {
      return { id: `mock_${Date.now()}`, userId, content, createdAt: new Date().toISOString() };
    }

    const { data, error } = await supabase
      .from('journal_entries')
      .insert({
        user_id: userId,
        content,
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async updateJournalReflection(entryId: string, reflection: string) {
    if (isDemoMode() || !supabase) {
      return;
    }

    const { error } = await supabase
      .from('journal_entries')
      .update({ ai_reflection: reflection })
      .eq('id', entryId);

    if (error) throw error;
  },

  async getJournalEntries(userId: string, limit = 50) {
    if (isDemoMode() || !supabase) {
      return [];
    }

    const { data, error } = await supabase
      .from('journal_entries')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) throw error;
    return data || [];
  },

  async deleteJournalEntry(entryId: string) {
    if (isDemoMode() || !supabase) {
      return;
    }

    const { error } = await supabase
      .from('journal_entries')
      .delete()
      .eq('id', entryId);

    if (error) throw error;
  },

  // Chat Messages
  async createChatMessage(userId: string, role: 'user' | 'assistant', content: string) {
    if (isDemoMode() || !supabase) {
      return { id: `mock_${Date.now()}`, userId, role, content, createdAt: new Date().toISOString() };
    }

    const { data, error } = await supabase
      .from('chat_messages')
      .insert({
        user_id: userId,
        role,
        content,
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async getChatMessages(userId: string, limit = 100) {
    if (isDemoMode() || !supabase) {
      return [];
    }

    const { data, error } = await supabase
      .from('chat_messages')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: true })
      .limit(limit);

    if (error) throw error;
    return data || [];
  },

  // Appointments
  async createAppointment(
    userId: string,
    therapistId: string,
    date: string,
    time: string,
    amount: number
  ) {
    if (isDemoMode() || !supabase) {
      return {
        id: `mock_${Date.now()}`,
        userId,
        therapistId,
        date,
        time,
        amount,
        status: 'pending',
        paymentStatus: 'pending',
      };
    }

    const { data, error } = await supabase
      .from('appointments')
      .insert({
        user_id: userId,
        therapist_id: therapistId,
        date,
        time,
        amount,
        status: 'pending',
        payment_status: 'pending',
      })
      .select()
      .single();

    if (error) throw error;
    return data;
  },

  async updateAppointmentStatus(appointmentId: string, status: string, paymentStatus?: string) {
    if (isDemoMode() || !supabase) {
      return;
    }

    const updates: Record<string, string> = { status, updated_at: new Date().toISOString() };
    if (paymentStatus) {
      updates.payment_status = paymentStatus;
    }

    const { error } = await supabase
      .from('appointments')
      .update(updates)
      .eq('id', appointmentId);

    if (error) throw error;
  },

  async getAppointments(userId: string) {
    if (isDemoMode() || !supabase) {
      return [];
    }

    const { data, error } = await supabase
      .from('appointments')
      .select('*')
      .eq('user_id', userId)
      .order('date', { ascending: true });

    if (error) throw error;
    return data || [];
  },

  // Program Progress
  async updateProgramProgress(
    userId: string,
    programId: string,
    chapterId: string,
    completed: boolean
  ) {
    if (isDemoMode() || !supabase) {
      return;
    }

    const { error } = await supabase
      .from('program_progress')
      .upsert({
        user_id: userId,
        program_id: programId,
        chapter_id: chapterId,
        completed,
        completed_at: completed ? new Date().toISOString() : null,
        updated_at: new Date().toISOString(),
      }, {
        onConflict: 'user_id,program_id,chapter_id',
      });

    if (error) throw error;
  },

  async getProgramProgress(userId: string, programId: string) {
    if (isDemoMode() || !supabase) {
      return [];
    }

    const { data, error } = await supabase
      .from('program_progress')
      .select('*')
      .eq('user_id', userId)
      .eq('program_id', programId);

    if (error) throw error;
    return data || [];
  },

  // Subscriptions
  async getActiveSubscription(userId: string) {
    if (isDemoMode() || !supabase) {
      return null;
    }

    const { data, error } = await supabase
      .from('subscriptions')
      .select('*')
      .eq('user_id', userId)
      .eq('status', 'active')
      .single();

    if (error && error.code !== 'PGRST116') throw error; // PGRST116 is "no rows returned"
    return data;
  },
};