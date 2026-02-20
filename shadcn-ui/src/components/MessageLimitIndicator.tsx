import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Sparkles, Crown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface MessageLimitIndicatorProps {
  messagesRemaining: number | null;
  totalMessages?: number;
  className?: string;
}

export function MessageLimitIndicator({
  messagesRemaining,
  totalMessages = 10,
  className = '',
}: MessageLimitIndicatorProps) {
  const navigate = useNavigate();

  // Se null, usuário é premium (mensagens ilimitadas)
  if (messagesRemaining === null) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Badge variant="default" className="bg-gradient-to-r from-yellow-500 to-amber-600">
          <Crown className="w-3 h-3 mr-1" />
          Premium
        </Badge>
        <span className="text-sm text-muted-foreground">Mensagens ilimitadas</span>
      </div>
    );
  }

  const messagesUsed = totalMessages - messagesRemaining;
  const progressPercentage = (messagesUsed / totalMessages) * 100;
  const isLowRemaining = messagesRemaining <= 3;

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge
            variant={isLowRemaining ? 'destructive' : 'secondary'}
            className="font-medium"
          >
            {messagesRemaining} {messagesRemaining === 1 ? 'mensagem' : 'mensagens'} restantes
          </Badge>
          {isLowRemaining && (
            <span className="text-xs text-muted-foreground animate-pulse">
              Limite quase atingido
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate('/subscription')}
          className="gap-1"
        >
          <Sparkles className="w-3 h-3" />
          Upgrade
        </Button>
      </div>

      <div className="space-y-1">
        <Progress
          value={progressPercentage}
          className="h-2"
          indicatorClassName={
            isLowRemaining
              ? 'bg-gradient-to-r from-red-500 to-orange-500'
              : 'bg-gradient-to-r from-blue-500 to-purple-500'
          }
        />
        <p className="text-xs text-muted-foreground">
          {messagesUsed} de {totalMessages} mensagens usadas hoje
        </p>
      </div>

      {isLowRemaining && (
        <div className="p-3 bg-orange-50 dark:bg-orange-950 rounded-lg border border-orange-200 dark:border-orange-800">
          <p className="text-sm text-orange-800 dark:text-orange-200">
            💡 <strong>Dica:</strong> Faça upgrade para Premium e tenha mensagens ilimitadas por
            apenas R$ 17,90/mês!
          </p>
        </div>
      )}
    </div>
  );
}