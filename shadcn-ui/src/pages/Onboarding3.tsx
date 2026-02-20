import { useNavigate } from 'react-router-dom';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { Shield, Lock, Heart } from 'lucide-react';

export default function Onboarding3() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/30 flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="inline-block">
            <div className="w-20 h-20 bg-verde-nevoa rounded-full flex items-center justify-center shadow-lg">
              <Shield size={40} className="text-azul-salvia" />
            </div>
          </div>
          
          <h1 className="text-3xl font-heading font-bold text-azul-salvia">
            Sua privacidade é sagrada
          </h1>
          
          <p className="text-lg text-azul-salvia/80 leading-relaxed">
            Tudo o que você compartilhar aqui é confidencial e protegido pela LGPD
          </p>
        </div>

        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <Lock size={24} className="text-lavanda-profunda flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-heading font-semibold text-azul-salvia mb-2">
                  Dados Criptografados
                </h3>
                <p className="text-sm text-azul-salvia/70">
                  Suas informações são protegidas com criptografia de ponta a ponta
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <Heart size={24} className="text-lavanda-profunda flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-heading font-semibold text-azul-salvia mb-2">
                  Sem Julgamentos
                </h3>
                <p className="text-sm text-azul-salvia/70">
                  Este é um espaço seguro para você ser autêntica
                </p>
              </div>
            </div>
          </div>

          <div className="bg-pessego/30 rounded-2xl p-5 border border-pessego">
            <p className="text-sm text-azul-salvia leading-relaxed">
              <strong className="font-semibold">Importante:</strong> A Acollya é uma ferramenta de suporte emocional e não substitui terapia profissional ou atendimento de emergência.
            </p>
          </div>
        </div>

        <div className="space-y-3 pt-4">
          <PrimaryButton
            onClick={() => navigate('/login')}
            className="w-full"
          >
            Começar
          </PrimaryButton>
          <SecondaryButton
            onClick={() => navigate('/onboarding-2')}
            className="w-full"
          >
            Voltar
          </SecondaryButton>
        </div>

        <div className="flex justify-center gap-2 pt-4">
          <div className="w-2 h-2 bg-cinza-neutro rounded-full" />
          <div className="w-2 h-2 bg-cinza-neutro rounded-full" />
          <div className="w-8 h-2 bg-lavanda-profunda rounded-full" />
        </div>
      </div>
    </div>
  );
}