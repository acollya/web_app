import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';
import { Heart } from 'lucide-react';

export default function About() {
  return (
    <Layout showBottomNav={false}>
      <div className="px-6 py-8">
        <PageHeader title="Sobre a Acollya" />
        
        <div className="space-y-6 mt-6">
          <div className="text-center py-8">
            <div className="w-24 h-24 bg-lavanda-profunda rounded-full flex items-center justify-center mx-auto mb-4">
              <Heart size={48} className="text-white" fill="white" />
            </div>
            <h2 className="text-xl font-heading font-bold text-azul-salvia mb-2">
              Acollya
            </h2>
            <p className="text-azul-salvia/70">
              Suporte emocional com IA
            </p>
          </div>

          <div className="bg-white rounded-2xl p-6 space-y-4">
            <div>
              <h3 className="font-heading font-semibold text-azul-salvia mb-2">
                Nossa Missão
              </h3>
              <p className="text-azul-salvia/80 text-sm leading-relaxed">
                Democratizar o acesso ao suporte emocional de qualidade, combinando tecnologia de IA com profissionais humanos.
              </p>
            </div>

            <div>
              <h3 className="font-heading font-semibold text-azul-salvia mb-2">
                Nossa Visão
              </h3>
              <p className="text-azul-salvia/80 text-sm leading-relaxed">
                Um mundo onde todas as pessoas tenham acesso a ferramentas e suporte para cuidar de sua saúde emocional.
              </p>
            </div>

            <div>
              <h3 className="font-heading font-semibold text-azul-salvia mb-2">
                Nossos Valores
              </h3>
              <ul className="text-azul-salvia/80 text-sm leading-relaxed space-y-1">
                <li>• Empatia e acolhimento</li>
                <li>• Privacidade e segurança</li>
                <li>• Acessibilidade</li>
                <li>• Inovação responsável</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}