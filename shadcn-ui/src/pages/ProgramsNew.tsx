import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { TrialExpiredModal } from '@/components/TrialExpiredModal';
import { Button } from '@/components/ui/button';
import { programService } from '@/services/programService';
import { Program } from '@/types/program';
import { useToast } from '@/hooks/use-toast';
import { Lock, Play, CheckCircle2 } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { canAccessRestrictedFeature } from '@/lib/trialValidation';

export default function ProgramsNew() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuthStore();
  const [programs, setPrograms] = useState<Program[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showTrialModal, setShowTrialModal] = useState(false);

  useEffect(() => {
    // Check trial access
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
    } else {
      loadPrograms();
    }
  }, [user]);

  const loadPrograms = async () => {
    try {
      const data = await programService.getPrograms();
      setPrograms(data);
    } catch (error) {
      toast({
        title: 'Erro ao carregar programas',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const isPremium = user?.planCode === 1;

  const handleProgramClick = (program: Program) => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }

    if (program.isPremium && !isPremium) {
      toast({
        title: 'Programa Premium',
        description: 'Assine o plano Premium para acessar este programa',
        variant: 'destructive',
      });
      navigate('/subscription');
      return;
    }
    navigate(`/programs/${program.id}`);
  };

  if (showTrialModal) {
    return (
      <div className="min-h-screen bg-offwhite pb-20">
        <PageHeader title="Programas de Autocuidado" showBack />
        <TrialExpiredModal open={showTrialModal} onOpenChange={setShowTrialModal} />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-offwhite flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader title="Programas de Autocuidado" showBack />
      
      <div className="px-6 py-6">
        <div className="mb-6">
          <h2 className="text-xl font-heading font-bold text-azul-salvia mb-2">
            Desenvolva hábitos saudáveis
          </h2>
          <p className="text-sm text-azul-salvia/70">
            Programas guiados para seu bem-estar emocional
          </p>
        </div>

        <div className="space-y-4">
          {programs.map((program) => {
            const progressPercentage = program.totalChapters > 0
              ? ((program.completedChapters || 0) / program.totalChapters) * 100
              : 0;

            return (
              <div
                key={program.id}
                onClick={() => handleProgramClick(program)}
                className="bg-white rounded-2xl overflow-hidden shadow-sm border border-cinza-neutro/30 cursor-pointer hover:shadow-md transition-shadow"
              >
                <div className="relative">
                  <img
                    src={program.coverImage}
                    alt={program.title}
                    className="w-full h-40 object-cover bg-lavanda-serenidade"
                  />
                  
                  {program.isPremium && !isPremium && (
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                      <div className="text-center text-white">
                        <Lock className="w-8 h-8 mx-auto mb-2" />
                        <p className="text-sm font-medium">Premium</p>
                      </div>
                    </div>
                  )}

                  <div className="absolute top-3 left-3">
                    <span className="px-3 py-1 bg-white/90 backdrop-blur-sm text-azul-salvia text-xs rounded-full font-medium">
                      {program.category}
                    </span>
                  </div>
                </div>

                <div className="p-5">
                  <h3 className="font-heading font-bold text-lg text-azul-salvia mb-2">
                    {program.title}
                  </h3>
                  
                  <p className="text-sm text-azul-salvia/70 mb-4 line-clamp-2">
                    {program.description}
                  </p>

                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      {progressPercentage > 0 ? (
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <div className="flex-1 h-2 bg-cinza-neutro/20 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-verde-esperanca transition-all"
                                style={{ width: `${progressPercentage}%` }}
                              />
                            </div>
                            <span className="text-xs text-azul-salvia/70 font-medium">
                              {Math.round(progressPercentage)}%
                            </span>
                          </div>
                          <p className="text-xs text-azul-salvia/60">
                            {program.completedChapters} de {program.totalChapters} capítulos
                          </p>
                        </div>
                      ) : (
                        <p className="text-xs text-azul-salvia/60">
                          {program.totalChapters} capítulos
                        </p>
                      )}
                    </div>

                    <div className="ml-4">
                      {program.isPremium && !isPremium ? (
                        <Button
                          size="sm"
                          className="bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white rounded-xl px-4"
                        >
                          R$ {program.price?.toFixed(2)}
                        </Button>
                      ) : progressPercentage === 100 ? (
                        <div className="flex items-center gap-1 text-verde-esperanca">
                          <CheckCircle2 className="w-5 h-5" />
                          <span className="text-sm font-medium">Concluído</span>
                        </div>
                      ) : progressPercentage > 0 ? (
                        <Button
                          size="sm"
                          className="bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white rounded-xl px-4"
                        >
                          <Play className="w-4 h-4 mr-1" />
                          Continuar
                        </Button>
                      ) : (
                        <span className="px-3 py-1 bg-verde-esperanca/20 text-verde-esperanca text-xs rounded-full font-medium">
                          Gratuito
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}