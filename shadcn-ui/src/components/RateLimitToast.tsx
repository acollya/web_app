import { AlertCircle, Clock, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

interface RateLimitToastProps {
  onUpgrade?: () => void;
}

export function RateLimitToast({ onUpgrade }: RateLimitToastProps) {
  const navigate = useNavigate();

  const handleUpgrade = () => {
    if (onUpgrade) {
      onUpgrade();
    } else {
      navigate('/subscription');
    }
  };

  // Calcular tempo até meia-noite
  const getTimeUntilReset = () => {
    const now = new Date();
    const midnight = new Date();
    midnight.setHours(24, 0, 0, 0);

    const diff = midnight.getTime() - now.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    return `${hours}h ${minutes}min`;
  };

  return (
    <div className="flex flex-col gap-3 p-4 bg-background border rounded-lg shadow-lg max-w-md">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-950 flex items-center justify-center flex-shrink-0">
          <AlertCircle className="w-5 h-5 text-orange-600 dark:text-orange-400" />
        </div>

        <div className="flex-1 space-y-1">
          <h4 className="font-semibold text-sm">Limite de Mensagens Atingido</h4>
          <p className="text-sm text-muted-foreground">
            Você atingiu o limite de 10 mensagens diárias do plano gratuito.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-muted-foreground pl-13">
        <Clock className="w-3 h-3" />
        <span>Seu limite será renovado em {getTimeUntilReset()}</span>
      </div>

      <div className="pl-13 space-y-2">
        <Button onClick={handleUpgrade} className="w-full gap-2" size="sm">
          <Sparkles className="w-4 h-4" />
          Upgrade para Premium
        </Button>

        <div className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950 dark:to-blue-950 p-3 rounded-lg border border-purple-200 dark:border-purple-800">
          <p className="text-xs text-center">
            <strong>Premium:</strong> Mensagens ilimitadas por apenas{' '}
            <span className="text-purple-600 dark:text-purple-400 font-bold">R$ 17,90/mês</span>
          </p>
        </div>
      </div>
    </div>
  );
}

// Hook para usar com toast do shadcn
export function useRateLimitToast() {
  const navigate = useNavigate();

  return {
    showRateLimitToast: (toast: (options: { title: string; description: React.ReactNode; variant?: string; duration?: number }) => void) => {
      toast({
        title: 'Limite de Mensagens Atingido',
        description: (
          <div className="space-y-3 mt-2">
            <p>Você atingiu o limite de 10 mensagens diárias do plano gratuito.</p>
            <Button
              onClick={() => navigate('/subscription')}
              className="w-full gap-2"
              size="sm"
            >
              <Sparkles className="w-4 h-4" />
              Upgrade para Premium
            </Button>
          </div>
        ),
        variant: 'destructive',
        duration: 8000,
      });
    },
  };
}