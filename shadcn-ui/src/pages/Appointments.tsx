import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { TrialExpiredModal } from '@/components/TrialExpiredModal';
import { Calendar, Clock, Info } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { canAccessRestrictedFeature } from '@/lib/trialValidation';

export default function Appointments() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [showTrialModal, setShowTrialModal] = useState(false);

  useEffect(() => {
    // Check trial access
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
    }
  }, [user]);

  const handleNewAppointment = () => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }
    navigate('/appointments/new');
  };

  const handleMyAppointments = () => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }
    navigate('/appointments/my');
  };

  if (showTrialModal) {
    return (
      <div className="min-h-screen bg-offwhite">
        <PageHeader title="Minhas Consultas" showBack />
        <TrialExpiredModal open={showTrialModal} onOpenChange={setShowTrialModal} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader title="Minhas Consultas" showBack />
      
      <div className="px-6 py-6 space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-xl font-heading font-bold text-azul-salvia mb-2">
            Agende com Terapeutas
          </h2>
          <p className="text-sm text-azul-salvia/70">
            Conecte-se com profissionais qualificados
          </p>
        </div>

        {/* Action Cards */}
        <div className="space-y-4">
          <button
            onClick={handleNewAppointment}
            className="w-full bg-gradient-to-br from-lavanda-profunda to-lavanda-profunda/80 rounded-2xl p-6 text-left hover:shadow-lg transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center flex-shrink-0">
                <Calendar className="w-7 h-7 text-white" />
              </div>
              <div className="flex-1 text-white">
                <h3 className="font-heading font-bold text-lg mb-1">
                  Agendar uma Consulta
                </h3>
                <p className="text-sm text-white/90">
                  Encontre o terapeuta ideal para você
                </p>
              </div>
            </div>
          </button>

          <button
            onClick={handleMyAppointments}
            className="w-full bg-white rounded-2xl p-6 text-left hover:shadow-lg transition-all hover:scale-[1.02] active:scale-[0.98] border border-cinza-neutro/30"
          >
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 bg-verde-esperanca/10 rounded-xl flex items-center justify-center flex-shrink-0">
                <Clock className="w-7 h-7 text-verde-esperanca" />
              </div>
              <div className="flex-1">
                <h3 className="font-heading font-bold text-lg text-azul-salvia mb-1">
                  Meus Agendamentos
                </h3>
                <p className="text-sm text-azul-salvia/70">
                  Veja suas consultas agendadas
                </p>
              </div>
            </div>
          </button>
        </div>

        {/* Info Card */}
        <div className="bg-lavanda-serenidade/30 border border-lavanda-profunda/20 rounded-2xl p-5">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-lavanda-profunda mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-azul-salvia mb-2">
                Como Funciona
              </h4>
              <ul className="text-sm text-azul-salvia/80 space-y-2">
                <li>• Responda um breve questionário</li>
                <li>• Encontre terapeutas compatíveis com você</li>
                <li>• Escolha data e horário disponíveis</li>
                <li>• Realize consultas online por videochamada</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Benefits */}
        <div className="bg-white rounded-2xl p-5 border border-cinza-neutro/30">
          <h4 className="font-heading font-semibold text-azul-salvia mb-3">
            Benefícios das Consultas
          </h4>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-verde-esperanca rounded-full mt-2 flex-shrink-0" />
              <p className="text-sm text-azul-salvia/80">
                <strong>Profissionais Qualificados:</strong> Todos os terapeutas são certificados e experientes
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-verde-esperanca rounded-full mt-2 flex-shrink-0" />
              <p className="text-sm text-azul-salvia/80">
                <strong>Flexibilidade:</strong> Agende no horário que melhor funciona para você
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-verde-esperanca rounded-full mt-2 flex-shrink-0" />
              <p className="text-sm text-azul-salvia/80">
                <strong>Privacidade:</strong> Consultas online seguras e confidenciais
              </p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 bg-verde-esperanca rounded-full mt-2 flex-shrink-0" />
              <p className="text-sm text-azul-salvia/80">
                <strong>Desconto Premium:</strong> Membros Premium têm 20% de desconto
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}