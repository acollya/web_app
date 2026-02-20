import { isDemoMode, getCurrentUser } from '@/lib/supabase';
import { callMoodInsights, callMoodCheckin } from '@/lib/edgeFunctions';
import { supabaseDataService } from './supabaseDataService';
import type {
  MoodInsights,
  MoodCheckinRequest,
} from '@/types/edgeFunctions';

export const moodService = {
  async getInsights(period: 'week' | 'month' | 'year'): Promise<MoodInsights> {
    // Demo mode - return mock data
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 1000));

      return {
        period,
        totalCheckins: 15,
        averageMood: 6.5,
        moodDistribution: {
          feliz: 6,
          ansioso: 5,
          calmo: 4,
        },
        trends: ['Seu humor tem melhorado consistentemente! 📈'],
        recommendations: ['Continue com as práticas que têm funcionado para você.'],
        mostCommonMood: 'feliz',
        moodImprovement: 12.5,
      };
    }

    // Production mode - use Edge Function
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const response = await callMoodInsights({
        userId: user.id,
        period,
      });

      return response.insights;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error getting mood insights:', error);
      throw new Error(
        errorMessage || 'Não foi possível gerar insights de humor'
      );
    }
  },

  async submitCheckin(data: {
    mood: string;
    intensity: number;
    note?: string;
    activities?: string[];
    generateInsight?: boolean;
  }): Promise<{ id: string; insight?: string }> {
    // Demo mode - use localStorage
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 800));

      const checkin = {
        id: Date.now().toString(),
        ...data,
        createdAt: new Date().toISOString(),
      };

      const stored = localStorage.getItem('acollya_mood_checkins');
      const checkins = stored ? JSON.parse(stored) : [];
      checkins.unshift(checkin);
      localStorage.setItem('acollya_mood_checkins', JSON.stringify(checkins));

      return { id: checkin.id };
    }

    // Production mode - use Edge Function
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const response = await callMoodCheckin({
        userId: user.id,
        mood: data.mood,
        intensity: data.intensity,
        note: data.note,
        activities: data.activities,
        generateInsight: data.generateInsight,
      });

      return {
        id: response.checkin.id,
        insight: response.insight,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error submitting mood check-in:', error);
      throw new Error(
        errorMessage || 'Não foi possível registrar check-in de humor'
      );
    }
  },

  async createCheckin(data: {
    primaryEmotion: string;
    secondaryEmotions?: string[];
    note?: string;
  }): Promise<void> {
    // Map emotion to intensity (simplified)
    const emotionToIntensity: Record<string, number> = {
      'muito-feliz': 10,
      'feliz': 8,
      'neutro': 5,
      'triste': 3,
      'muito-triste': 1,
      'ansioso': 4,
      'calmo': 7,
    };

    const intensity = emotionToIntensity[data.primaryEmotion] || 5;

    await this.submitCheckin({
      mood: data.primaryEmotion,
      intensity,
      note: data.note,
      activities: data.secondaryEmotions,
      generateInsight: false,
    });
  },
};