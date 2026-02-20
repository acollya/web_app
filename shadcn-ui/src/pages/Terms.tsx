import { useNavigate } from 'react-router-dom';
import { BackButton } from '@/components/BackButton';

export default function Terms() {
  const navigate = useNavigate();
  
  return (
    <div className="min-h-screen bg-offwhite px-6 py-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <BackButton />
          <h1 className="text-2xl font-heading font-bold text-azul-salvia">
            Termos de Uso
          </h1>
        </div>

        <div className="bg-white rounded-2xl p-6 space-y-4">
          <p className="text-azul-salvia/80 text-sm leading-relaxed">
            <strong>Última atualização:</strong> Dezembro de 2024
          </p>

          <div>
            <h3 className="font-heading font-semibold text-azul-salvia mb-2">
              1. Aceitação dos Termos
            </h3>
            <p className="text-azul-salvia/80 text-sm leading-relaxed">
              Ao utilizar a Acollya, você concorda com estes termos de uso. Se não concordar, não utilize o serviço.
            </p>
          </div>

          <div>
            <h3 className="font-heading font-semibold text-azul-salvia mb-2">
              2. Natureza do Serviço
            </h3>
            <p className="text-azul-salvia/80 text-sm leading-relaxed">
              A Acollya é uma ferramenta de suporte emocional e não substitui terapia profissional, diagnóstico médico ou atendimento de emergência.
            </p>
          </div>

          <div>
            <h3 className="font-heading font-semibold text-azul-salvia mb-2">
              3. Privacidade
            </h3>
            <p className="text-azul-salvia/80 text-sm leading-relaxed">
              Seus dados são protegidos conforme nossa Política de Privacidade e a LGPD (Lei Geral de Proteção de Dados).
            </p>
          </div>

          <p className="text-azul-salvia/70 text-xs pt-4">
            Este é um documento resumido. A versão completa dos Termos de Uso estará disponível em breve.
          </p>
        </div>
      </div>
    </div>
  );
}