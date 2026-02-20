import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';
import { TrialExpiredModal } from '@/components/TrialExpiredModal';
import { programService } from '@/services/programService';
import { Program, ProgramProgress } from '@/types/program';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Sparkles, Clock, CheckCircle } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { canAccessRestrictedFeature } from '@/lib/trialValidation';

export default function Programs() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [programs, setPrograms] = useState<Program[]>([]);
  const [progress, setProgress] = useState<Record<string, ProgramProgress>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [showTrialModal, setShowTrialModal] = useState(false);

  useEffect(() => {
    // Check trial access
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }

    const loadData = async () => {
      try {
        const programsData = await programService.getPrograms();
        setPrograms(programsData);

        const progressData: Record<string, ProgramProgress> = {};
        for (const program of programsData) {
          const prog = await programService.getProgress(program.id);
          if (prog) {
            progressData[program.id] = prog;
          }
        }
        setProgress(progressData);
      } catch (error) {
        console.error('Error loading programs:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [user]);

  const handleProgramClick = (programId: string) => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }
    navigate(`/programs/${programId}`);
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="h-screen flex items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="px-6 py-8 space-y-6">
        <PageHeader 
          title="Programas de Autocuidado" 
          subtitle="Jornadas guiadas para seu bem-estar"
        />

        <div className="space-y-4">
          {programs.map((program) => {
            const prog = progress[program.id];
            const statusConfig = {
              'not-started': { label: 'Começar', color: 'bg-lavanda-profunda' },
              'in-progress': { label: 'Continuar', color: 'bg-pessego' },
              'completed': { label: 'Concluído', color: 'bg-verde-nevoa' },
            };
            const status = prog?.status || 'not-started';
            const config = statusConfig[status];

            return (
              <div
                key={program.id}
                onClick={() => handleProgramClick(program.id)}
                className="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-all cursor-pointer"
              >
                <div className="flex items-start gap-4">
                  <div className="w-16 h-16 bg-lavanda-serenidade rounded-xl flex items-center justify-center flex-shrink-0">
                    <Sparkles size={28} className="text-lavanda-profunda" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-heading font-semibold text-azul-salvia text-lg mb-2">
                      {program.title}
                    </h3>
                    <p className="text-sm text-azul-salvia/70 mb-3">
                      {program.description}
                    </p>
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-1 text-cinza-calmo">
                        <Clock size={16} />
                        <span>{program.duration} dias</span>
                      </div>
                      {prog && (
                        <div className="flex items-center gap-1 text-cinza-calmo">
                          <CheckCircle size={16} />
                          <span>{prog.completedDays.length}/{program.duration}</span>
                        </div>
                      )}
                    </div>
                    <div className={`inline-block mt-3 px-4 py-1.5 rounded-full text-xs font-medium ${config.color} text-azul-salvia`}>
                      {config.label}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <TrialExpiredModal open={showTrialModal} onOpenChange={setShowTrialModal} />
    </Layout>
  );
}