import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { Textarea } from '@/components/ui/textarea';
import { journalService } from '@/services/journalService';
import { ArrowLeft, Mic } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function JournalNew() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [aiReflection, setAiReflection] = useState('');

  const handleSave = async () => {
    if (!content.trim()) {
      toast({
        title: 'Escreva algo primeiro',
        description: 'Seu diário não pode estar vazio',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      const entry = await journalService.createEntry(content);
      setIsSaved(true);

      toast({
        title: 'Diário salvo!',
        description: 'Sua entrada foi registrada',
      });

      // Get AI reflection
      const reflection = await journalService.getReflection(entry.id, content);
      setAiReflection(reflection);
    } catch (error) {
      toast({
        title: 'Erro ao salvar',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (isSaved && aiReflection) {
    return (
      <Layout showBottomNav={false}>
        <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/20 px-6 py-8">
          <div className="max-w-2xl mx-auto space-y-8">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-verde-nevoa rounded-full flex items-center justify-center mx-auto">
                <span className="text-4xl">✨</span>
              </div>
              <h1 className="text-2xl font-heading font-bold text-azul-salvia">
                Entrada salva!
              </h1>
            </div>

            <div className="bg-white rounded-2xl p-6 shadow-sm">
              <h3 className="font-heading font-semibold text-azul-salvia mb-3">
                Reflexão da Acollya
              </h3>
              <p className="text-azul-salvia/80 leading-relaxed">
                {aiReflection}
              </p>
            </div>

            <div className="space-y-3">
              <PrimaryButton
                onClick={() => navigate('/home')}
                className="w-full"
              >
                Voltar ao início
              </PrimaryButton>
              <SecondaryButton
                onClick={() => navigate('/journal')}
                className="w-full"
              >
                Ver meu diário
              </SecondaryButton>
            </div>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout showBottomNav={false}>
      <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/20 px-6 py-8">
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/journal')}
              className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm hover:shadow-md transition-shadow"
            >
              <ArrowLeft size={20} className="text-azul-salvia" />
            </button>
            <div>
              <h1 className="text-2xl font-heading font-bold text-azul-salvia">
                Nova Entrada
              </h1>
              <p className="text-sm text-azul-salvia/70">
                Escreva sobre seus pensamentos
              </p>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm space-y-4">
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Como você está se sentindo? O que aconteceu hoje? Escreva livremente..."
              className="min-h-[300px] rounded-xl border-cinza-neutro focus:border-lavanda-profunda resize-none text-base"
            />

            <button
              className="flex items-center gap-2 text-azul-salvia hover:text-lavanda-profunda transition-colors"
              onClick={() => toast({ title: 'Em breve', description: 'Gravação de áudio estará disponível em breve' })}
            >
              <Mic size={20} />
              <span className="text-sm font-medium">Gravar áudio (em breve)</span>
            </button>
          </div>

          <div className="space-y-3">
            <PrimaryButton
              onClick={handleSave}
              isLoading={isLoading}
              className="w-full"
            >
              Salvar diário
            </PrimaryButton>
            <SecondaryButton
              onClick={() => navigate('/journal')}
              className="w-full"
            >
              Cancelar
            </SecondaryButton>
          </div>
        </div>
      </div>
    </Layout>
  );
}