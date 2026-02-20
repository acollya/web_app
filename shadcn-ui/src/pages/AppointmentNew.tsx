import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { TrialExpiredModal } from '@/components/TrialExpiredModal';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { appointmentService } from '@/services/appointmentService';
import { Therapist, MatchingAnswers } from '@/types/appointment';
import { useToast } from '@/hooks/use-toast';
import { Star } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { canAccessRestrictedFeature } from '@/lib/trialValidation';

export default function AppointmentNew() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuthStore();
  const [answers, setAnswers] = useState<MatchingAnswers>({
    energy: '',
    emotional: '',
    physical: '',
    routine: '',
  });
  const [therapists, setTherapists] = useState<Therapist[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showTrialModal, setShowTrialModal] = useState(false);

  useEffect(() => {
    // Check trial access
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
    }
  }, [user]);

  const questions = [
    {
      id: 'energy',
      question: 'Como você descreveria seu nível de energia ultimamente?',
      options: [
        { value: 'muito-alta', label: 'Muito alta - me sinto energizado(a)' },
        { value: 'alta', label: 'Alta - tenho disposição' },
        { value: 'media', label: 'Média - nem alta nem baixa' },
        { value: 'baixa', label: 'Baixa - me sinto cansado(a)' },
        { value: 'muito-baixa', label: 'Muito baixa - exausto(a)' },
      ],
    },
    {
      id: 'emotional',
      question: 'Como você tem se sentido emocionalmente?',
      options: [
        { value: 'muito-bem', label: 'Muito bem - feliz e realizado(a)' },
        { value: 'bem', label: 'Bem - geralmente positivo(a)' },
        { value: 'neutro', label: 'Neutro - nem bem nem mal' },
        { value: 'mal', label: 'Mal - frequentemente triste' },
        { value: 'muito-mal', label: 'Muito mal - sofrendo bastante' },
      ],
    },
    {
      id: 'physical',
      question: 'Como está seu corpo e seus pensamentos?',
      options: [
        { value: 'relaxado', label: 'Relaxado - corpo e mente tranquilos' },
        { value: 'levemente-tenso', label: 'Levemente tenso - algum desconforto' },
        { value: 'tenso', label: 'Tenso - bastante desconforto' },
        { value: 'muito-tenso', label: 'Muito tenso - dificuldade para relaxar' },
        { value: 'ansioso', label: 'Ansioso - pensamentos acelerados' },
      ],
    },
    {
      id: 'routine',
      question: 'Como está sua rotina de sono e alimentação?',
      options: [
        { value: 'excelente', label: 'Excelente - durmo bem e como saudável' },
        { value: 'boa', label: 'Boa - geralmente equilibrada' },
        { value: 'regular', label: 'Regular - poderia melhorar' },
        { value: 'ruim', label: 'Ruim - sono irregular ou má alimentação' },
        { value: 'muito-ruim', label: 'Muito ruim - ambos problemáticos' },
      ],
    },
  ];

  const allQuestionsAnswered = Object.values(answers).every(answer => answer !== '');

  const handleFindTherapist = async () => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }

    if (!allQuestionsAnswered) {
      toast({
        title: 'Responda todas as perguntas',
        description: 'Por favor, complete o questionário',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    try {
      const matched = await appointmentService.matchTherapists(answers);
      setTherapists(matched);
      
      if (matched.length === 0) {
        toast({
          title: 'Nenhum terapeuta encontrado',
          description: 'Tente ajustar suas respostas',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Erro ao buscar terapeutas',
        description: 'Tente novamente',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const isPremium = user?.planCode === 1;

  if (showTrialModal) {
    return (
      <div className="min-h-screen bg-offwhite">
        <PageHeader title="Agendar Consulta" showBack />
        <TrialExpiredModal open={showTrialModal} onOpenChange={setShowTrialModal} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader title="Agendar Consulta" showBack />
      
      <div className="max-w-2xl mx-auto px-6 py-6">
        {therapists.length === 0 ? (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl p-6 border border-cinza-neutro/30">
              <h2 className="text-xl font-heading font-bold text-azul-salvia mb-2">
                Vamos encontrar o terapeuta ideal para você
              </h2>
              <p className="text-sm text-azul-salvia/70">
                Responda algumas perguntas para te conectarmos com profissionais compatíveis
              </p>
            </div>

            {questions.map((q) => (
              <div key={q.id} className="bg-white rounded-2xl p-6 border border-cinza-neutro/30">
                <label className="block font-semibold text-azul-salvia mb-3">
                  {q.question}
                </label>
                <Select
                  value={answers[q.id as keyof MatchingAnswers]}
                  onValueChange={(value) => setAnswers({ ...answers, [q.id]: value })}
                >
                  <SelectTrigger className="w-full h-12 rounded-xl border-cinza-neutro">
                    <SelectValue placeholder="Selecione uma opção" />
                  </SelectTrigger>
                  <SelectContent>
                    {q.options.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}

            <Button
              onClick={handleFindTherapist}
              disabled={!allQuestionsAnswered || isLoading}
              className="w-full h-14 bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white rounded-xl text-lg font-semibold"
            >
              {isLoading ? 'Buscando...' : 'Encontrar meu terapeuta'}
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl p-6 border border-cinza-neutro/30">
              <h2 className="text-xl font-heading font-bold text-azul-salvia mb-2">
                Terapeutas Recomendados
              </h2>
              <p className="text-sm text-azul-salvia/70">
                Baseado nas suas respostas, estes profissionais são ideais para você
              </p>
            </div>

            <div className="space-y-4">
              {therapists.map((therapist) => {
                const discountedPrice = isPremium ? therapist.price * 0.8 : therapist.price;
                
                return (
                  <div
                    key={therapist.id}
                    className="bg-white rounded-2xl p-5 border border-cinza-neutro/30 hover:shadow-md transition-shadow"
                  >
                    <div className="flex gap-4 mb-4">
                      <img
                        src={therapist.photo}
                        alt={therapist.name}
                        className="w-20 h-20 rounded-full object-cover bg-lavanda-serenidade"
                      />
                      
                      <div className="flex-1 min-w-0">
                        <h3 className="font-heading font-bold text-lg text-azul-salvia mb-1">
                          {therapist.name}
                        </h3>
                        
                        <div className="flex items-center gap-1 mb-2">
                          {[...Array(5)].map((_, i) => (
                            <Star
                              key={i}
                              className={`w-4 h-4 ${
                                i < Math.floor(therapist.rating)
                                  ? 'fill-amarelo-acolhedor text-amarelo-acolhedor'
                                  : 'text-cinza-neutro'
                              }`}
                            />
                          ))}
                          <span className="text-sm text-azul-salvia/70 ml-1">
                            {therapist.rating.toFixed(1)}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-1">
                          {therapist.specialties.slice(0, 3).map((specialty, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 bg-lavanda-serenidade text-lavanda-profunda text-xs rounded-full"
                            >
                              {specialty}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-cinza-neutro">
                      <div>
                        {isPremium && therapist.price !== discountedPrice ? (
                          <div className="flex items-baseline gap-2">
                            <span className="text-sm text-azul-salvia/50 line-through">
                              R$ {therapist.price.toFixed(2)}
                            </span>
                            <span className="text-xl font-bold text-verde-esperanca">
                              R$ {discountedPrice.toFixed(2)}
                            </span>
                          </div>
                        ) : (
                          <span className="text-xl font-bold text-azul-salvia">
                            R$ {therapist.price.toFixed(2)}
                          </span>
                        )}
                      </div>
                      
                      <Button
                        onClick={() => navigate(`/appointments/book/${therapist.id}`)}
                        className="bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white rounded-xl px-6"
                      >
                        Agendar
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>

            <Button
              onClick={() => {
                setTherapists([]);
                setAnswers({ energy: '', emotional: '', physical: '', routine: '' });
              }}
              variant="outline"
              className="w-full h-12 rounded-xl border-cinza-neutro"
            >
              Refazer Questionário
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}