import { isDemoMode, getCurrentUser } from '@/lib/supabase';
import { callProgramProgress } from '@/lib/edgeFunctions';
import type { ProgramProgress } from '@/types/edgeFunctions';

interface StoredChapter {
  id: string;
  completed: boolean;
  completedAt: string | null;
}

interface StoredProgress {
  chapters: StoredChapter[];
}

export const programService = {
  async updateProgress(
    programId: string,
    chapterId: string,
    action: 'complete' | 'reset'
  ): Promise<ProgramProgress> {
    // Demo mode - return mock data
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 500));

      const stored = localStorage.getItem(`acollya_program_${programId}`);
      const progress: StoredProgress = stored ? JSON.parse(stored) : { chapters: [] };

      const chapterIndex = progress.chapters.findIndex(
        (c) => c.id === chapterId
      );

      if (chapterIndex >= 0) {
        progress.chapters[chapterIndex].completed = action === 'complete';
        progress.chapters[chapterIndex].completedAt =
          action === 'complete' ? new Date().toISOString() : null;
      } else {
        progress.chapters.push({
          id: chapterId,
          completed: action === 'complete',
          completedAt: action === 'complete' ? new Date().toISOString() : null,
        });
      }

      localStorage.setItem(`acollya_program_${programId}`, JSON.stringify(progress));

      const completedCount = progress.chapters.filter((c) => c.completed).length;
      const totalChapters = 10; // Mock

      return {
        totalChapters,
        completedChapters: completedCount,
        percentageComplete: Math.round((completedCount / totalChapters) * 100),
        lastUpdated: new Date().toISOString(),
        chapters: progress.chapters,
      };
    }

    // Production mode - use Edge Function
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const response = await callProgramProgress({
        userId: user.id,
        programId,
        chapterId,
        action,
      });

      return response.progress;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error updating program progress:', error);
      throw new Error(
        errorMessage || 'Não foi possível atualizar progresso do programa'
      );
    }
  },

  async getProgress(programId: string): Promise<ProgramProgress> {
    // Demo mode - get from localStorage
    if (isDemoMode()) {
      const stored = localStorage.getItem(`acollya_program_${programId}`);
      const progress: StoredProgress = stored ? JSON.parse(stored) : { chapters: [] };

      const completedCount = progress.chapters.filter((c) => c.completed).length;
      const totalChapters = 10; // Mock

      return {
        totalChapters,
        completedChapters: completedCount,
        percentageComplete: Math.round((completedCount / totalChapters) * 100),
        lastUpdated: new Date().toISOString(),
        chapters: progress.chapters,
      };
    }

    // Production mode - would need a separate Edge Function or query
    // For now, return empty progress
    return {
      totalChapters: 10,
      completedChapters: 0,
      percentageComplete: 0,
      lastUpdated: new Date().toISOString(),
      chapters: [],
    };
  },
};