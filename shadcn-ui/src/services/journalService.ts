import { JournalEntry } from '@/types/journal';
import { mockJournalEntries } from '@/lib/mockData';
import { isDemoMode, getCurrentUser } from '@/lib/supabase';
import { callJournalReflection } from '@/lib/edgeFunctions';
import { supabaseDataService } from './supabaseDataService';

interface DatabaseJournalEntry {
  id: string;
  user_id: string;
  content: string;
  ai_reflection?: string;
  created_at: string;
}

export const journalService = {
  async createEntry(content: string, audioUrl?: string): Promise<JournalEntry> {
    // Demo mode - use localStorage
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 800));

      const newEntry: JournalEntry = {
        id: Date.now().toString(),
        userId: '1',
        content,
        audioUrl,
        createdAt: new Date().toISOString(),
      };

      // Store locally for offline support
      const stored = localStorage.getItem('acollya_journal_entries');
      const entries = stored ? JSON.parse(stored) : [];
      entries.unshift(newEntry);
      localStorage.setItem('acollya_journal_entries', JSON.stringify(entries));

      return newEntry;
    }

    // Production mode - use Supabase
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const entry = await supabaseDataService.createJournalEntry(user.id, content);

      return {
        id: entry.id,
        userId: entry.user_id,
        content: entry.content,
        audioUrl,
        createdAt: entry.created_at,
      };
    } catch (error) {
      console.error('Error creating journal entry:', error);

      // Fallback to localStorage
      const newEntry: JournalEntry = {
        id: Date.now().toString(),
        userId: '1',
        content,
        audioUrl,
        createdAt: new Date().toISOString(),
      };

      const stored = localStorage.getItem('acollya_journal_entries');
      const entries = stored ? JSON.parse(stored) : [];
      entries.unshift(newEntry);
      localStorage.setItem('acollya_journal_entries', JSON.stringify(entries));

      return newEntry;
    }
  },

  async getEntries(): Promise<JournalEntry[]> {
    // Demo mode - use localStorage
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 500));

      const stored = localStorage.getItem('acollya_journal_entries');
      if (stored) {
        return JSON.parse(stored);
      }

      return mockJournalEntries;
    }

    // Production mode - get from Supabase
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const entries = await supabaseDataService.getJournalEntries(user.id);

      return entries.map((entry: DatabaseJournalEntry) => ({
        id: entry.id,
        userId: entry.user_id,
        content: entry.content,
        aiReflection: entry.ai_reflection,
        createdAt: entry.created_at,
      }));
    } catch (error) {
      console.error('Error getting journal entries:', error);

      // Fallback to localStorage
      const stored = localStorage.getItem('acollya_journal_entries');
      if (stored) {
        return JSON.parse(stored);
      }

      return mockJournalEntries;
    }
  },

  async getReflection(entryId: string, content: string): Promise<string> {
    // Demo mode - use mock reflections
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const reflections = [
        'É importante reconhecer seus sentimentos. Escrever sobre eles é um grande passo.',
        'Percebo que você está passando por um momento desafiador. Como posso te apoiar?',
        'Que bom que você compartilhou isso. Suas emoções são válidas.',
        'Vejo que você está se esforçando para entender seus sentimentos. Isso é muito valioso.',
      ];

      return reflections[Math.floor(Math.random() * reflections.length)];
    }

    // Production mode - use journal-reflection Edge Function
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const response = await callJournalReflection({
        entryId,
        content,
        userId: user.id,
      });

      // Save reflection to database
      await supabaseDataService.updateJournalReflection(entryId, response.reflection);

      return response.reflection;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error getting journal reflection:', error);

      // Handle specific errors
      if (errorMessage.includes('não autenticado')) {
        throw new Error('Você precisa estar autenticado para gerar reflexões.');
      }

      if (errorMessage.includes('OpenAI')) {
        throw new Error(
          'Não foi possível gerar a reflexão no momento. Por favor, tente novamente mais tarde.'
        );
      }

      // Fallback to mock reflection
      console.warn('Falling back to mock reflection due to error');

      const fallbackReflections = [
        'Obrigado por compartilhar seus pensamentos. Suas emoções são importantes e válidas.',
        'É corajoso expressar o que você está sentindo. Continue escrevendo quando precisar.',
        'Reconheço que você está passando por algo significativo. Estou aqui para apoiar você.',
      ];

      return fallbackReflections[Math.floor(Math.random() * fallbackReflections.length)];
    }
  },

  async deleteEntry(entryId: string): Promise<void> {
    // Demo mode - remove from localStorage
    if (isDemoMode()) {
      const stored = localStorage.getItem('acollya_journal_entries');
      if (stored) {
        const entries = JSON.parse(stored);
        const filtered = entries.filter((entry: JournalEntry) => entry.id !== entryId);
        localStorage.setItem('acollya_journal_entries', JSON.stringify(filtered));
      }
      return;
    }

    // Production mode - delete from Supabase
    try {
      await supabaseDataService.deleteJournalEntry(entryId);
    } catch (error) {
      console.error('Error deleting journal entry:', error);
      throw new Error('Não foi possível excluir a entrada. Por favor, tente novamente.');
    }
  },
};