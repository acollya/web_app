import { useNavigate } from 'react-router-dom';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useAuth } from '@/hooks/useAuth';

interface TrialExpiredModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TrialExpiredModal({ open, onOpenChange }: TrialExpiredModalProps) {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleUpgrade = () => {
    onOpenChange(false);
    navigate('/subscription');
  };

  const handleLater = () => {
    onOpenChange(false);
    navigate('/home');
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-azul-salvia font-heading text-xl">
            Continue Cuidando da Sua Saúde Mental
          </AlertDialogTitle>
          <AlertDialogDescription className="text-azul-salvia/80 text-base leading-relaxed pt-2">
            Olá {user?.name?.split(' ')[0]}! 💜
            <br /><br />
            Seu período de teste gratuito de 14 dias chegou ao fim. Para continuar tendo acesso ao chat com IA, check-ins de humor, diário emocional e programas de autocuidado, faça upgrade para o plano Premium por apenas <strong>R$ 17,90/mês</strong>.
            <br /><br />
            Continue sua jornada de autocuidado conosco! ✨
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex-col gap-2 sm:flex-col">
          <AlertDialogAction
            onClick={handleUpgrade}
            className="w-full h-12 bg-lavanda-profunda text-white rounded-xl font-semibold hover:bg-lavanda-profunda/90 transition-colors"
          >
            Fazer Upgrade Agora
          </AlertDialogAction>
          <AlertDialogCancel
            onClick={handleLater}
            className="w-full h-12 bg-transparent border-2 border-cinza-neutro text-azul-salvia rounded-xl hover:bg-gray-50"
          >
            Talvez Depois
          </AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}