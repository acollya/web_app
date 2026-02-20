import { useNavigate } from 'react-router-dom';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { Heart, BookOpen, MessageCircle, Sparkles } from 'lucide-react';

export default function Onboarding2() {
  const navigate = useNavigate();

  const features = [
    {
      icon: Heart,
      title: 'Check-ins de Humor',
      description: 'Registre como você está se sentindo todos os dias',
    },
    {
      icon: BookOpen,
      title: 'Diário Emocional',
      description: 'Escreva ou grave áudios sobre seus sentimentos',
    },
    {
      icon: MessageCircle,
      title: 'Chat 24/7',
      description: 'Converse com a IA sempre que precisar',
    },
    {
      icon: Sparkles,
      title: 'Programas de Autocuidado',
      description: 'Jornadas guiadas para seu bem-estar',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/30 flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full space-y-8 animate-fade-in">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-heading font-bold text-azul-salvia">
            O que você pode fazer
          </h1>
          <p className="text-azul-salvia/70">
            Ferramentas para cuidar da sua saúde emocional
          </p>
        </div>

        <div className="space-y-4">
          {features.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="bg-white rounded-2xl p-5 shadow-sm flex gap-4 items-start hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 bg-lavanda-serenidade rounded-xl flex items-center justify-center flex-shrink-0">
                <Icon size={24} className="text-lavanda-profunda" />
              </div>
              <div>
                <h3 className="font-heading font-semibold text-azul-salvia mb-1">
                  {title}
                </h3>
                <p className="text-sm text-azul-salvia/70">{description}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-3 pt-4">
          <PrimaryButton
            onClick={() => navigate('/onboarding-3')}
            className="w-full"
          >
            Continuar
          </PrimaryButton>
          <SecondaryButton
            onClick={() => navigate('/onboarding-1')}
            className="w-full"
          >
            Voltar
          </SecondaryButton>
        </div>

        <div className="flex justify-center gap-2 pt-4">
          <div className="w-2 h-2 bg-cinza-neutro rounded-full" />
          <div className="w-8 h-2 bg-lavanda-profunda rounded-full" />
          <div className="w-2 h-2 bg-cinza-neutro rounded-full" />
        </div>
      </div>
    </div>
  );
}