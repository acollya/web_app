import { supabase, isDemoMode } from '@/lib/supabase';
import { User } from '@/types/user';

export const supabaseAuthService = {
  async signUp(email: string, password: string, name: string) {
    if (isDemoMode() || !supabase) {
      throw new Error('Supabase not configured - using demo mode');
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          name,
        },
      },
    });

    if (error) throw error;
    return data;
  },

  async signIn(email: string, password: string) {
    if (isDemoMode() || !supabase) {
      throw new Error('Supabase not configured - using demo mode');
    }

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;
    return data;
  },

  async signInWithGoogle() {
    if (isDemoMode() || !supabase) {
      throw new Error('Supabase not configured - using demo mode');
    }

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    });

    if (error) throw error;
    return data;
  },

  async signOut() {
    if (isDemoMode() || !supabase) {
      return;
    }

    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  },

  async resetPassword(email: string) {
    if (isDemoMode() || !supabase) {
      throw new Error('Supabase not configured - using demo mode');
    }

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    if (error) throw error;
  },

  async updatePassword(newPassword: string) {
    if (isDemoMode() || !supabase) {
      throw new Error('Supabase not configured - using demo mode');
    }

    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    });

    if (error) throw error;
  },

  async getCurrentUser() {
    if (isDemoMode() || !supabase) {
      return null;
    }

    const { data: { user }, error } = await supabase.auth.getUser();
    if (error) throw error;
    return user;
  },

  async getUserProfile(userId: string): Promise<User | null> {
    if (isDemoMode() || !supabase) {
      return null;
    }

    const { data, error } = await supabase
      .from('users')
      .select('*')
      .eq('id', userId)
      .single();

    if (error) throw error;

    if (!data) return null;

    return {
      id: data.id,
      email: data.email,
      name: data.name,
      phone: data.phone || '',
      birthDate: data.birth_date || '',
      gender: data.gender || '',
      planCode: data.plan_code,
      trialEndsAt: data.trial_ends_at || '',
      termsAccepted: data.terms_accepted,
      termsAcceptedDate: data.terms_accepted_date || '',
    };
  },

  async updateUserProfile(userId: string, updates: Partial<User>) {
    if (isDemoMode() || !supabase) {
      throw new Error('Supabase not configured - using demo mode');
    }

    const { error } = await supabase
      .from('users')
      .update({
        name: updates.name,
        phone: updates.phone,
        birth_date: updates.birthDate,
        gender: updates.gender,
        terms_accepted: updates.termsAccepted,
        terms_accepted_date: updates.termsAcceptedDate,
        updated_at: new Date().toISOString(),
      })
      .eq('id', userId);

    if (error) throw error;
  },
};