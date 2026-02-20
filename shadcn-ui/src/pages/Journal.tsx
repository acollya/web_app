import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';
import { TrialExpiredModal } from '@/components/TrialExpiredModal';
import { AILoadingState } from '@/components/AILoadingState';
import { Button } from '@/components/ui/button';
import { journalService } from '@/services/journalService';
import { JournalEntry } from '@/types/journal';
import { useToast } from '@/hooks/use-toast';
import { Plus, Calendar, Lock, Sparkles } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { canAccessRestrictedFeature } from '@/lib/trialValidation';

export default function Journal() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showTrialModal, setShowTrialModal] = useState(false);
  const [generatingReflectionFor, setGeneratingReflectionFor] = useState<string | null>(null);

  useEffect(() => {
    // Check trial access
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
    } else {
      loadEntries();
    }
  }, [user]);

  const loadEntries = async () => {
    try {
      const data = await journalService.getEntries();
      setEntries(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      toast({
        title: 'Erro ao carregar entradas',
        description: errorMessage || 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewEntry = () => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }
    navigate('/journal/new');
  };

  const handleGenerateReflection = async (entry: JournalEntry) => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }

    setGeneratingReflectionFor(entry.id);

    try {
      const reflection = await journalService.getReflection(entry.id, entry.content);
      
      // Update entry with reflection
      setEntries(prev => 
        prev.map(e => 
          e.id === entry.id 
            ? { ...e, aiReflection: reflection }
            : e
        )
      );

      toast({
        title: 'Reflexão Gerada',
        description: 'Sua reflexão foi gerada com sucesso!',
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error generating reflection:', error);
      
      toast({
        title: 'Erro ao Gerar Reflexão',
        description: errorMessage || 'Não foi possível gerar a reflexão. Tente novamente.',
        variant: 'destructive',
      });
    } finally {
      setGeneratingReflectionFor(null);
    }
  };

  if (showTrialModal) {
    return (
      <Layout>
        <div className="min-h-screen bg-offwhite">
          <PageHeader title="Meu Diário" showBack />
          <TrialExpiredModal open={showTrialModal} onOpenChange={setShowTrialModal} />
        </div>
      </Layout>
    );
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="min-h-screen bg-offwhite flex items-center justify-center">
          <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-offwhite pb-24">
        <PageHeader title="Meu Diário" showBack />

        <div className="px-6 py-6">
          {/* New Entry Button */}
          <Button
            onClick={handleNewEntry}
            className="w-full h-14 bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white rounded-xl mb-6 font-semibold"
          >
            <Plus className="w-5 h-5 mr-2" />
            Nova Entrada
          </Button>

          {/* Entries List */}
          {entries.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-20 h-20 bg-lavanda-serenidade rounded-full flex items-center justify-center mx-auto mb-4">
                <Lock className="w-10 h-10 text-lavanda-profunda" />
              </div>
              <h3 className="font-heading font-bold text-xl text-azul-salvia mb-2">
                Seu diário está vazio
              </h3>
              <p className="text-azul-salvia/70 mb-6">
                Comece a registrar seus pensamentos e sentimentos
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="bg-white rounded-2xl p-5 shadow-sm border border-cinza-neutro/30 hover:shadow-md transition-shadow"
                >
                  <div
                    className="cursor-pointer"
                    onClick={() => navigate(`/journal/${entry.id}`)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2 text-sm text-azul-salvia/70">
                        <Calendar className="w-4 h-4" />
                        <span>
                          {new Date(entry.createdAt).toLocaleDateString('pt-BR', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                          })}
                        </span>
                      </div>
                    </div>

                    {entry.title && (
                      <h3 className="font-heading font-semibold text-lg text-azul-salvia mb-2">
                        {entry.title}
                      </h3>
                    )}

                    <p className="text-sm text-azul-salvia/80 line-clamp-3 mb-3">
                      {entry.content}
                    </p>

                    {entry.tags && entry.tags.length > 0 && (
                      <div className="flex flex-wrap gap-2 mb-3">
                        {entry.tags.map((tag, index) => (
                          <span
                            key={index}
                            className="px-2 py-1 bg-lavanda-serenidade text-lavanda-profunda text-xs rounded-full"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* AI Reflection Section */}
                  {entry.aiReflection ? (
                    <div className="mt-4 p-4 bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-950 dark:to-blue-950 rounded-xl border border-purple-200 dark:border-purple-800">
                      <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                        <span className="text-sm font-semibold text-purple-900 dark:text-purple-100">
                          Reflexão da IA
                        </span>
                      </div>
                      <p className="text-sm text-purple-800 dark:text-purple-200">
                        {entry.aiReflection}
                      </p>
                    </div>
                  ) : (
                    <div className="mt-4">
                      {generatingReflectionFor === entry.id ? (
                        <AILoadingState message="Gerando reflexão sobre sua entrada..." />
                      ) : (
                        <Button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleGenerateReflection(entry);
                          }}
                          variant="outline"
                          size="sm"
                          className="w-full gap-2"
                        >
                          <Sparkles className="w-4 h-4" />
                          Gerar Reflexão com IA
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}