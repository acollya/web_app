import { useNavigate } from 'react-router-dom';
import { BackButton } from '@/components/BackButton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Shield, Lock, Brain, Eye, Users, Phone, Sprout, Mail } from 'lucide-react';

export default function PrivacySecurity() {
  const navigate = useNavigate();
  
  return (
    <div className="min-h-screen bg-offwhite">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center gap-4 mb-6">
          <BackButton onClick={() => navigate('/profile')} />
          <div>
            <h1 className="text-3xl font-heading font-bold text-azul-salvia flex items-center gap-3">
              <Shield className="w-8 h-8 text-lavanda-profunda" />
              Privacidade e Segurança
            </h1>
            <p className="text-azul-salvia/70 mt-1">
              Seu bem-estar começa pela sua segurança
            </p>
          </div>
        </div>

        <ScrollArea className="h-[calc(100vh-200px)]">
          <div className="bg-white rounded-2xl p-8 space-y-8">
            <div className="prose prose-sm max-w-none">
              <p className="text-azul-salvia/80 leading-relaxed">
                Na Acollya, acreditamos que cuidar da sua saúde emocional só é possível quando você se sente protegido, respeitado e no controle das suas informações.
              </p>
              <p className="text-azul-salvia/80 leading-relaxed">
                Por isso, tratamos privacidade e segurança como valores inegociáveis — tão essenciais quanto acolhimento, ciência acessível e humanidade ampliada pela tecnologia.
              </p>
              <p className="text-azul-salvia/80 leading-relaxed">
                Esta página explica, de forma clara e humana, como lidamos com seus dados, como protegemos sua jornada emocional e quais direitos você tem dentro do nosso app.
              </p>
            </div>

            {/* Section 1 */}
            <div className="border-l-4 border-lavanda-profunda pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6 text-lavanda-profunda" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  1. Compromisso com sua privacidade
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                A Acollya foi criada para democratizar o cuidado emocional com segurança e responsabilidade. Isso significa que:
              </p>
              <ul className="space-y-2 text-azul-salvia/80">
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Você continua sendo dono(a) de todas as suas informações.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Nunca vendemos seus dados.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Só usamos seus dados para melhorar sua experiência, personalizar seu autocuidado e garantir que o suporte emocional seja eficaz e seguro.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Seus check-ins, conversas, diários e registros são confidenciais.</span>
                </li>
              </ul>
              <p className="text-azul-salvia/80 leading-relaxed">
                Nossa missão inclui garantir privacidade, acolhimento e escalonamento humano quando necessário, respeitando toda a sua individualidade e vulnerabilidade.
              </p>
            </div>

            {/* Section 2 */}
            <div className="border-l-4 border-verde-esperanca pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Lock className="w-6 h-6 text-verde-esperanca" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  2. Como protegemos seus dados
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                Seguimos padrões rigorosos de segurança para garantir que sua jornada seja segura em cada etapa.
              </p>
              <div className="space-y-4 mt-4">
                <div className="bg-verde-esperanca/5 rounded-lg p-4">
                  <h3 className="font-semibold text-azul-salvia mb-2">✔ Criptografia completa</h3>
                  <p className="text-sm text-azul-salvia/70">
                    Todos os dados em trânsito e em repouso são criptografados utilizando protocolos de nível bancário.
                  </p>
                </div>
                <div className="bg-verde-esperanca/5 rounded-lg p-4">
                  <h3 className="font-semibold text-azul-salvia mb-2">✔ Armazenamento seguro</h3>
                  <p className="text-sm text-azul-salvia/70">
                    Servidores com camadas múltiplas de proteção, monitoramento contínuo e práticas modernas de segurança da informação.
                  </p>
                </div>
                <div className="bg-verde-esperanca/5 rounded-lg p-4">
                  <h3 className="font-semibold text-azul-salvia mb-2">✔ Acesso limitado</h3>
                  <p className="text-sm text-azul-salvia/70">
                    Somente sistemas autorizados — e nunca pessoas externas — têm acesso às informações necessárias para o funcionamento do app.
                  </p>
                </div>
                <div className="bg-verde-esperanca/5 rounded-lg p-4">
                  <h3 className="font-semibold text-azul-salvia mb-2">✔ Logs e auditoria</h3>
                  <p className="text-sm text-azul-salvia/70">
                    Monitoramos atividades suspeitas para impedir acessos indevidos e garantir integridade.
                  </p>
                </div>
                <div className="bg-verde-esperanca/5 rounded-lg p-4">
                  <h3 className="font-semibold text-azul-salvia mb-2">✔ Arquitetura que prioriza segurança</h3>
                  <p className="text-sm text-azul-salvia/70">
                    Nossa tecnologia foi desenhada para minimizar riscos e manter seus dados isolados de terceiros e outras aplicações.
                  </p>
                </div>
              </div>
            </div>

            {/* Section 3 */}
            <div className="border-l-4 border-lavanda-serenidade pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Brain className="w-6 h-6 text-lavanda-serenidade" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  3. Segurança no uso da Inteligência Artificial
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                Nosso assistente emocional é movido por um modelo de IA em português, ajustado com supervisão de psicólogos e baseado em Terapia Relacional Sistêmica e TCC.
              </p>
              <p className="text-azul-salvia/80 leading-relaxed font-semibold">
                Para garantir ética e segurança:
              </p>
              <ul className="space-y-2 text-azul-salvia/80">
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-serenidade mt-1">•</span>
                  <span>O modelo não tem acesso à sua identidade real.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-serenidade mt-1">•</span>
                  <span>Suas conversas são usadas apenas para melhorar recomendações e personalização.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-serenidade mt-1">•</span>
                  <span>A IA não substitui atendimento profissional — ela é uma ponte, não um destino final, refletindo nosso valor de humanidade ampliada pela tecnologia.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-serenidade mt-1">•</span>
                  <span>Indicadores de risco emocional ou sinais de urgência acionam protocolos seguros, incluindo orientação para o CVV ou encaminhamento a suporte humano quando necessário.</span>
                </li>
              </ul>
            </div>

            {/* Section 4 */}
            <div className="border-l-4 border-amarelo-acolhedor pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Eye className="w-6 h-6 text-amarelo-acolhedor" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  4. Transparência no uso dos seus dados
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                Coletamos apenas o que é essencial para oferecer a melhor experiência emocional possível. Entre os dados utilizados, estão:
              </p>
              
              <div className="space-y-4 mt-4">
                <div>
                  <h3 className="font-semibold text-azul-salvia mb-2">Dados que você fornece</h3>
                  <ul className="space-y-1 text-sm text-azul-salvia/70">
                    <li>• Check-ins de humor</li>
                    <li>• Diários emocionais</li>
                    <li>• Conversas com o assistente</li>
                    <li>• Informações de cadastro (nome, e-mail, login Google)</li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-semibold text-azul-salvia mb-2">Dados coletados automaticamente</h3>
                  <ul className="space-y-1 text-sm text-azul-salvia/70">
                    <li>• Dados de uso (para entender se as funcionalidades funcionam bem)</li>
                    <li>• Informações técnicas do dispositivo</li>
                  </ul>
                </div>
                
                <div>
                  <h3 className="font-semibold text-azul-salvia mb-2">Dados que não coletamos</h3>
                  <ul className="space-y-1 text-sm text-azul-salvia/70">
                    <li>• Fotos ou áudios sem sua autorização</li>
                    <li>• Dados sensíveis fora do contexto emocional</li>
                    <li>• Localização exata do usuário</li>
                    <li>• Informações financeiras não relacionadas ao pagamento</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Section 5 */}
            <div className="border-l-4 border-lavanda-profunda pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Users className="w-6 h-6 text-lavanda-profunda" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  5. Seus direitos
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                Você tem total controle sobre sua experiência na Acollya.
              </p>
              <p className="text-azul-salvia/80 leading-relaxed font-semibold">
                Pode, a qualquer momento:
              </p>
              <ul className="space-y-2 text-azul-salvia/80">
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Solicitar cópia dos seus dados</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Corrigir informações</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Excluir sua conta e todos os registros associados</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Retirar consentimentos</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Limitar o uso de dados para personalização</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-lavanda-profunda mt-1">•</span>
                  <span>Desabilitar notificações emocionais</span>
                </li>
              </ul>
              <p className="text-azul-salvia/80 leading-relaxed">
                Nosso compromisso é tornar tudo simples, acessível e sem burocracia — exatamente como acreditamos que o cuidado emocional deve ser.
              </p>
            </div>

            {/* Section 6 */}
            <div className="border-l-4 border-verde-esperanca pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Users className="w-6 h-6 text-verde-esperanca" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  6. Segurança no escalonamento humano
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                Quando você optar por falar com um psicólogo parceiro:
              </p>
              <ul className="space-y-2 text-azul-salvia/80">
                <li className="flex items-start gap-2">
                  <span className="text-verde-esperanca mt-1">•</span>
                  <span>Apenas as informações essenciais para o atendimento são compartilhadas.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-verde-esperanca mt-1">•</span>
                  <span>Você sempre será informado(a) sobre o que será transmitido.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-verde-esperanca mt-1">•</span>
                  <span>O profissional segue o sigilo ético da psicologia e a legislação vigente.</span>
                </li>
              </ul>
              <p className="text-azul-salvia/80 leading-relaxed">
                A Acollya conecta tecnologia e humanidade para entregar um cuidado psicológico humano, contínuo e seguro, como promete nossa marca.
              </p>
            </div>

            {/* Section 7 */}
            <div className="border-l-4 border-red-500 pl-6 space-y-3 bg-red-50 -ml-6 p-6 rounded-r-lg">
              <div className="flex items-center gap-3">
                <Phone className="w-6 h-6 text-red-600" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  7. Situações de emergência
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed font-semibold">
                A Acollya não é um serviço de crise.
              </p>
              <p className="text-azul-salvia/80 leading-relaxed">
                Se você estiver em risco imediato, orientamos contato com:
              </p>
              <div className="bg-white rounded-lg p-4 space-y-2">
                <p className="text-azul-salvia font-semibold">📞 CVV – 188</p>
                <p className="text-azul-salvia font-semibold">💬 Chat em www.cvv.org.br</p>
                <p className="text-sm text-azul-salvia/70">Atendimento 24h no Brasil.</p>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                O app detecta sinais de risco e direciona automaticamente para suporte adequado, respeitando sua privacidade e bem-estar.
              </p>
            </div>

            {/* Section 8 */}
            <div className="border-l-4 border-lavanda-serenidade pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Sprout className="w-6 h-6 text-lavanda-serenidade" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  8. Atualizações desta política
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                Melhoramos continuamente nossas práticas de privacidade para refletir inovação com propósito — um dos valores centrais da Acollya.
              </p>
              <p className="text-azul-salvia/80 leading-relaxed">
                Sempre que esta política for atualizada, você será notificado(a) de forma clara e transparente.
              </p>
            </div>

            {/* Section 9 */}
            <div className="border-l-4 border-amarelo-acolhedor pl-6 space-y-3">
              <div className="flex items-center gap-3">
                <Mail className="w-6 h-6 text-amarelo-acolhedor" />
                <h2 className="text-xl font-heading font-bold text-azul-salvia">
                  9. Fale conosco
                </h2>
              </div>
              <p className="text-azul-salvia/80 leading-relaxed">
                Estamos aqui para acolher você — inclusive nas dúvidas sobre sua privacidade.
              </p>
              <div className="bg-amarelo-acolhedor/10 rounded-lg p-4">
                <p className="text-azul-salvia font-semibold">📧 privacidade@acollya.com</p>
                <p className="text-sm text-azul-salvia/70 mt-2">
                  Responderemos com clareza, empatia e respeito.
                </p>
              </div>
            </div>

            <div className="border-t border-cinza-neutro pt-6 mt-8">
              <p className="text-xs text-azul-salvia/60 text-center">
                <strong>Última atualização:</strong> Dezembro de 2024
              </p>
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}