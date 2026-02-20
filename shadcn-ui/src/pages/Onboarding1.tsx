import { useNavigate } from 'react-router-dom';
import { PrimaryButton } from '@/components/PrimaryButton';
import { Heart } from 'lucide-react';

export default function Onboarding1() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/30 flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="inline-block animate-breathe">
            <div className="w-24 h-24 bg-lavanda-profunda rounded-full flex items-center justify-center shadow-lg">
              <Heart size={48} className="text-white" fill="white" />
            </div>
          </div>
          
          <h1 className="text-4xl font-heading font-bold text-azul-salvia">
            Bem-vinda à Acollya
          </h1>
          
          <p className="text-lg text-azul-salvia/80 leading-relaxed">
            Seu espaço seguro de suporte emocional, combinando inteligência artificial com profissionais humanos
          </p>
        </div>

        <div className="space-y-4 pt-8">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h3 className="font-heading font-semibold text-azul-salvia mb-2">
              🤖 Suporte com IA 24/7
            </h3>
            <p className="text-sm text-azul-salvia/70">
              Converse quando precisar, sem julgamentos
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <h3 className="font-heading font-semibold text-azul-salvia mb-2">
              👥 Profissionais Humanos
            </h3>
            <p className="text-sm text-azul-salvia/70">
              Conecte-se com psicólogos quando estiver pronta
            </p>
          </div>
        </div>

        <div className="pt-8">
          <PrimaryButton
            onClick={() => navigate('/onboarding-2')}
            className="w-full"
          >
            Continuar
          </PrimaryButton>
        </div>

        <div className="flex justify-center gap-2 pt-4">
          <div className="w-8 h-2 bg-lavanda-profunda rounded-full" />
          <div className="w-2 h-2 bg-cinza-neutro rounded-full" />
          <div className="w-2 h-2 bg-cinza-neutro rounded-full" />
        </div>
      </div>
    </div>
  );
}