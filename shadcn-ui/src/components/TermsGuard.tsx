import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TermsAcceptanceModal } from './TermsAcceptanceModal';
import { userService } from '@/services/userService';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';
import { useToast } from '@/hooks/use-toast';

interface TermsGuardProps {
  children: React.ReactNode;
}

export function TermsGuard({ children }: TermsGuardProps) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, logout } = useAuth();
  const { updateUser } = useAuthStore();
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkTermsAcceptance = async () => {
      if (!user) {
        setIsLoading(false);
        return;
      }

      // Check if user has accepted terms
      if (!user.termsAccepted) {
        setShowTermsModal(true);
      }
      
      setIsLoading(false);
    };

    checkTermsAcceptance();
  }, [user]);

  const handleAcceptTerms = async () => {
    if (!user) return;

    try {
      const updatedUser = await userService.acceptTerms(user.id);
      updateUser(updatedUser);
      setShowTermsModal(false);
      
      toast({
        title: 'Termos aceitos!',
        description: 'Bem-vinda à Acollya. Vamos começar sua jornada de autocuidado.',
      });
    } catch (error) {
      toast({
        title: 'Erro ao aceitar termos',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    }
  };

  const handleDeclineTerms = async () => {
    toast({
      title: 'Termos não aceitos',
      description: 'Você precisa aceitar os termos para usar a Acollya',
      variant: 'destructive',
    });
    
    await logout();
    navigate('/login');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-offwhite">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <>
      {children}
      <TermsAcceptanceModal
        open={showTermsModal}
        onAccept={handleAcceptTerms}
        onDecline={handleDeclineTerms}
      />
    </>
  );
}