import { isDemoMode, getCurrentUser } from '@/lib/supabase';
import { callTherapistMatching } from '@/lib/edgeFunctions';
import type {
  TherapistMatchingRequest,
  TherapistMatch,
} from '@/types/edgeFunctions';

export const therapistService = {
  async findMatches(
    answers: TherapistMatchingRequest['answers']
  ): Promise<TherapistMatch[]> {
    // Demo mode - return mock data
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 1500));

      return [
        {
          id: '1',
          name: 'Dra. Ana Silva',
          specialization: 'Ansiedade e Depressão',
          bio: 'Especialista em TCC com 10 anos de experiência',
          rating: 4.8,
          hourlyRate: 150,
          score: 85,
          matchReasons: ['Gênero preferido', 'Especialização em ansiedade'],
        },
        {
          id: '2',
          name: 'Dr. Carlos Santos',
          specialization: 'Relacionamentos',
          bio: 'Terapeuta de casais e famílias',
          rating: 4.6,
          hourlyRate: 180,
          score: 75,
          matchReasons: ['Abordagem: Sistêmica'],
        },
      ];
    }

    // Production mode - use Edge Function
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const response = await callTherapistMatching({
        userId: user.id,
        answers,
      });

      return response.matches;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error finding therapist matches:', error);
      throw new Error(
        errorMessage || 'Não foi possível encontrar terapeutas compatíveis'
      );
    }
  },
};