import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { EmotionIcon } from '@/components/EmotionIcon';
import { TrialExpiredModal } from '@/components/TrialExpiredModal';
import { AILoadingState } from '@/components/AILoadingState';
import { Textarea } from '@/components/ui/textarea';
import { moodService } from '@/services/moodService';
import { useMoodStore } from '@/store/moodStore';
import { EMOTIONS } from '@/lib/constants';
import { EmotionLevel } from '@/types/mood';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/hooks/useAuth';
import { canAccessRestrictedFeature } from '@/lib/trialValidation';
import { Sparkles } from 'lucide-react';

export default function MoodCheckin() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const { setTodayMood } = useMoodStore();
  const [primaryEmotion, setPrimaryEmotion] = useState<EmotionLevel | null>(null);
  const [secondaryEmotions, setSecondaryEmotions] = useState<EmotionLevel[]>([]);
  const [note, setNote] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showTrialModal, setShowTrialModal] = useState(false);
  const [aiInsight, setAiInsight] = useState<string | null>(null);

  useEffect(() => {
    // Check trial access
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
    }
  }, [user]);

  const handleSecondaryToggle = (emotion: EmotionLevel) => {
    if (secondaryEmotions.includes(emotion)) {
      setSecondaryEmotions(secondaryEmotions.filter(e => e !== emotion));
    } else {
      setSecondaryEmotions([...secondaryEmotions, emotion]);
    }
  };

  const handleSubmit = async () => {
    if (!canAccessRestrictedFeature(user)) {
      setShowTrialModal(true);
      return;
    }

    if (!primaryEmotion) {
      toast({
        title: 'Selecione uma emoção',
        description: 'Por favor, escolha como você está se sentindo',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);

    try {
      // Submit check-in using new Edge Function
      const result = await moodService.submitCheckin({
        mood: primaryEmotion,
        intensity: getMoodIntensity(primaryEmotion),
        note: note.trim() || undefined,
        activities: secondaryEmotions,
        generateInsight: true, // Request AI insight
      });

      setTodayMood(primaryEmotion);

      // Show AI insight if available
      if (result.insight) {
        setAiInsight(result.insight);
        toast({
          title: 'Check-in registrado!',
          description: result.insight,
          duration: 5000,
        });
      } else {
        toast({
          title: 'Check-in registrado!',
          description: 'Obrigada por compartilhar como você está',
        });
      }

      // Show suggestion if negative emotion
      if (primaryEmotion === 'triste' || primaryEmotion === 'muito-triste') {
        setTimeout(() => {
          toast({
            title: 'Que tal conversar?',
            description: 'A Acollya está aqui para te ouvir',
          });
        }, 1500);
      }

      // Navigate to home after successful check-in
      setTimeout(() => {
        navigate('/home');
      }, 2000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error submitting check-in:', error);
      toast({
        title: 'Erro ao registrar',
        description: errorMessage || 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Helper to map emotion to intensity (1-10)
  const getMoodIntensity = (emotion: EmotionLevel): number => {
    const intensityMap: Record<EmotionLevel, number> = {
      'muito-feliz': 10,
      'feliz': 8,
      'neutro': 5,
      'triste': 3,
      'muito-triste': 1,
      'ansioso': 4,
      'calmo': 7,
      'irritado': 3,
      'animado': 9,
    };
    return intensityMap[emotion] || 5;
  };

  return (
    <Layout showBottomNav={false}>
      <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/20 px-6 py-8">
        <div className="max-w-2xl mx-auto space-y-8">
          <PageHeader 
            title="Como você está?" 
            subtitle="Registre seu momento atual"
            showBack
            onBack={() => navigate('/home')}
          />

          {/* Primary Emotion */}
          <div className="space-y-4">
            <h2 className="font-heading font-semibold text-azul-salvia">
              Emoção principal <span className="text-pessego">*</span>
            </h2>
            <div className="grid grid-cols-3 gap-3">
              {EMOTIONS.map((emotion) => (
                <EmotionIcon
                  key={emotion.id}
                  emotion={emotion.id as EmotionLevel}
                  label={emotion.label}
                  icon={emotion.icon}
                  selected={primaryEmotion === emotion.id}
                  onClick={() => setPrimaryEmotion(emotion.id as EmotionLevel)}
                />
              ))}
            </div>
          </div>

          {/* Secondary Emotions */}
          <div className="space-y-4">
            <h2 className="font-heading font-semibold text-azul-salvia">
              Outras emoções (opcional)
            </h2>
            <p className="text-sm text-azul-salvia/70">
              Você pode selecionar mais de uma
            </p>
            <div className="grid grid-cols-3 gap-3">
              {EMOTIONS.filter(e => e.id !== primaryEmotion).map((emotion) => (
                <EmotionIcon
                  key={emotion.id}
                  emotion={emotion.id as EmotionLevel}
                  label={emotion.label}
                  icon={emotion.icon}
                  selected={secondaryEmotions.includes(emotion.id as EmotionLevel)}
                  onClick={() => handleSecondaryToggle(emotion.id as EmotionLevel)}
                />
              ))}
            </div>
          </div>

          {/* Note */}
          <div className="space-y-4">
            <h2 className="font-heading font-semibold text-azul-salvia">
              Quer contar um pouco mais?
            </h2>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="O que aconteceu hoje? Como você está se sentindo?"
              className="min-h-[120px] rounded-xl border-cinza-neutro focus:border-lavanda-profunda resize-none"
            />
          </div>

          {/* AI Insight Display */}
          {aiInsight && (
            <div className="p-4 bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-950 dark:to-blue-950 rounded-xl border border-purple-200 dark:border-purple-800">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <span className="text-sm font-semibold text-purple-900 dark:text-purple-100">
                  Insight da IA
                </span>
              </div>
              <p className="text-sm text-purple-800 dark:text-purple-200">
                {aiInsight}
              </p>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <AILoadingState message="Processando seu check-in e gerando insights..." />
          )}

          {/* Actions */}
          <div className="space-y-3 pt-4">
            <PrimaryButton
              onClick={handleSubmit}
              isLoading={isLoading}
              className="w-full"
              disabled={isLoading}
            >
              Registrar meu momento
            </PrimaryButton>
            <SecondaryButton
              onClick={() => navigate('/home')}
              className="w-full"
              disabled={isLoading}
            >
              Pular por enquanto
            </SecondaryButton>
          </div>
        </div>
      </div>

      <TrialExpiredModal open={showTrialModal} onOpenChange={setShowTrialModal} />
    </Layout>
  );
}