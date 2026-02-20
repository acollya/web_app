import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SecondaryButton } from '@/components/SecondaryButton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { authService } from '@/services/authService';
import { Mail } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [emailSent, setEmailSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await authService.forgotPassword(email);
      setEmailSent(true);
      toast({
        title: 'E-mail enviado!',
        description: 'Verifique sua caixa de entrada',
      });
    } catch (error) {
      toast({
        title: 'Erro ao enviar e-mail',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  if (emailSent) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/30 flex flex-col items-center justify-center p-6">
        <div className="max-w-md w-full space-y-8 animate-fade-in text-center">
          <div className="inline-block">
            <div className="w-20 h-20 bg-verde-nevoa rounded-full flex items-center justify-center shadow-lg">
              <Mail size={40} className="text-azul-salvia" />
            </div>
          </div>
          
          <div className="space-y-4">
            <h1 className="text-3xl font-heading font-bold text-azul-salvia">
              E-mail enviado!
            </h1>
            
            <p className="text-azul-salvia/80 leading-relaxed">
              Enviamos instruções para recuperar sua senha para <strong>{email}</strong>
            </p>

            <p className="text-sm text-azul-salvia/70">
              Não recebeu? Verifique sua caixa de spam ou tente novamente em alguns minutos.
            </p>
          </div>

          <PrimaryButton
            onClick={() => navigate('/login')}
            className="w-full"
          >
            Voltar para login
          </PrimaryButton>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/30 flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-heading font-bold text-azul-salvia">
            Recuperar senha
          </h1>
          
          <p className="text-azul-salvia/70">
            Digite seu e-mail e enviaremos instruções para redefinir sua senha
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="email" className="text-azul-salvia font-medium">
              E-mail
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="h-12 rounded-xl border-cinza-neutro focus:border-lavanda-profunda"
            />
          </div>

          <div className="space-y-3">
            <PrimaryButton
              type="submit"
              isLoading={isLoading}
              className="w-full"
            >
              Enviar instruções
            </PrimaryButton>
            
            <SecondaryButton
              type="button"
              onClick={() => navigate('/login')}
              className="w-full"
            >
              Voltar
            </SecondaryButton>
          </div>
        </form>

        <div className="text-center">
          <p className="text-sm text-azul-salvia/70">
            Lembrou sua senha?{' '}
            <Link to="/login" className="text-lavanda-profunda font-semibold hover:underline">
              Fazer login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}