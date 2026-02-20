import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Shield, FileText, Lock } from 'lucide-react';
import { Link } from 'react-router-dom';

interface TermsAcceptanceModalProps {
  open: boolean;
  onAccept: () => void;
  onDecline: () => void;
}

export function TermsAcceptanceModal({ open, onAccept, onDecline }: TermsAcceptanceModalProps) {
  const [hasReadTerms, setHasReadTerms] = useState(false);
  const [hasReadPrivacy, setHasReadPrivacy] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);

  const canProceed = hasReadTerms && hasReadPrivacy && acceptedTerms;

  const handleAccept = () => {
    if (canProceed) {
      onAccept();
    }
  };

  return (
    <Dialog open={open} onOpenChange={() => {}}>
      <DialogContent className="max-w-2xl max-h-[90vh] p-0" onInteractOutside={(e) => e.preventDefault()}>
        <DialogHeader className="p-6 pb-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 bg-lavanda-profunda/10 rounded-full flex items-center justify-center">
              <Shield className="w-6 h-6 text-lavanda-profunda" />
            </div>
            <div>
              <DialogTitle className="text-2xl font-heading text-azul-salvia">
                Bem-vinda à Acollya
              </DialogTitle>
              <DialogDescription className="text-azul-salvia/70">
                Antes de começar, precisamos do seu consentimento
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <ScrollArea className="px-6 max-h-[50vh]">
          <div className="space-y-6 pb-4">
            <div className="bg-lavanda-serenidade/20 rounded-xl p-4 space-y-3">
              <div className="flex items-start gap-3">
                <FileText className="w-5 h-5 text-lavanda-profunda mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold text-azul-salvia mb-2">
                    Termos de Uso
                  </h3>
                  <p className="text-sm text-azul-salvia/70 mb-3">
                    Nossos termos explicam como você pode usar a Acollya, seus direitos e responsabilidades.
                  </p>
                  <Link 
                    to="/terms" 
                    target="_blank"
                    onClick={() => setHasReadTerms(true)}
                    className="text-sm text-lavanda-profunda hover:underline font-medium inline-flex items-center gap-1"
                  >
                    Ler Termos de Uso completos →
                  </Link>
                </div>
              </div>
              
              <div className="flex items-center gap-3 pl-8">
                <Checkbox
                  id="terms-read"
                  checked={hasReadTerms}
                  onCheckedChange={(checked) => setHasReadTerms(checked === true)}
                  className="border-lavanda-profunda data-[state=checked]:bg-lavanda-profunda"
                />
                <label 
                  htmlFor="terms-read" 
                  className="text-sm text-azul-salvia cursor-pointer"
                >
                  Li e compreendi os Termos de Uso
                </label>
              </div>
            </div>

            <div className="bg-verde-esperanca/10 rounded-xl p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Lock className="w-5 h-5 text-verde-esperanca mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold text-azul-salvia mb-2">
                    Política de Privacidade
                  </h3>
                  <p className="text-sm text-azul-salvia/70 mb-3">
                    Sua privacidade é fundamental. Saiba como protegemos e utilizamos seus dados.
                  </p>
                  <Link 
                    to="/privacy-policy" 
                    target="_blank"
                    onClick={() => setHasReadPrivacy(true)}
                    className="text-sm text-verde-esperanca hover:underline font-medium inline-flex items-center gap-1"
                  >
                    Ler Política de Privacidade completa →
                  </Link>
                </div>
              </div>
              
              <div className="flex items-center gap-3 pl-8">
                <Checkbox
                  id="privacy-read"
                  checked={hasReadPrivacy}
                  onCheckedChange={(checked) => setHasReadPrivacy(checked === true)}
                  className="border-verde-esperanca data-[state=checked]:bg-verde-esperanca"
                />
                <label 
                  htmlFor="privacy-read" 
                  className="text-sm text-azul-salvia cursor-pointer"
                >
                  Li e compreendi a Política de Privacidade
                </label>
              </div>
            </div>

            <div className="border-t border-cinza-neutro pt-4">
              <div className="flex items-start gap-3">
                <Checkbox
                  id="accept-all"
                  checked={acceptedTerms}
                  onCheckedChange={(checked) => setAcceptedTerms(checked === true)}
                  disabled={!hasReadTerms || !hasReadPrivacy}
                  className="mt-1 border-lavanda-profunda data-[state=checked]:bg-lavanda-profunda"
                />
                <label 
                  htmlFor="accept-all" 
                  className={`text-sm leading-relaxed ${
                    !hasReadTerms || !hasReadPrivacy 
                      ? 'text-azul-salvia/40 cursor-not-allowed' 
                      : 'text-azul-salvia cursor-pointer'
                  }`}
                >
                  <span className="font-semibold">Aceito os Termos de Uso e a Política de Privacidade</span>
                  <br />
                  <span className="text-xs text-azul-salvia/60">
                    Ao aceitar, você concorda em utilizar a Acollya de acordo com nossos termos e reconhece como tratamos seus dados pessoais.
                  </span>
                </label>
              </div>
            </div>

            <div className="bg-amarelo-acolhedor/10 border border-amarelo-acolhedor/30 rounded-lg p-4">
              <p className="text-xs text-azul-salvia/70 leading-relaxed">
                <strong className="text-azul-salvia">Importante:</strong> A Acollya é uma ferramenta de suporte emocional e não substitui atendimento psicológico profissional, diagnóstico médico ou serviços de emergência. Em caso de crise, entre em contato com o CVV (188) ou procure ajuda profissional imediata.
              </p>
            </div>
          </div>
        </ScrollArea>

        <div className="flex gap-3 p-6 pt-4 border-t border-cinza-neutro">
          <Button
            variant="outline"
            onClick={onDecline}
            className="flex-1 h-12 rounded-xl border-cinza-neutro hover:bg-gray-50"
          >
            Recusar e Sair
          </Button>
          <Button
            onClick={handleAccept}
            disabled={!canProceed}
            className="flex-1 h-12 rounded-xl bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Aceitar e Continuar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}