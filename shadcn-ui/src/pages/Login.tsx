import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PrimaryButton } from '@/components/PrimaryButton';
import { TertiaryButton } from '@/components/TertiaryButton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { supabaseAuthService } from '@/services/supabaseAuthService';
import { Heart } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { isDemoMode } from '@/lib/supabase';

export default function Login() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { signIn } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await signIn(formData.email, formData.password);
      
      toast({
        title: 'Bem-vinda de volta!',
        description: 'Login realizado com sucesso',
      });
      navigate('/home');
    } catch (error) {
      console.error('Login error:', error);
      toast({
        title: 'Erro ao fazer login',
        description: 'Verifique suas credenciais e tente novamente',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    
    try {
      if (isDemoMode()) {
        toast({
          title: 'Modo Demo',
          description: 'Login com Google não disponível no modo demo. Use email/senha.',
          variant: 'destructive',
        });
        setIsLoading(false);
        return;
      }
      
      // Real Supabase OAuth
      await supabaseAuthService.signInWithGoogle();
      // Supabase will redirect to Google, then back to /auth/callback
    } catch (error) {
      console.error('Google login error:', error);
      toast({
        title: 'Erro ao fazer login',
        description: 'Não foi possível conectar com o Google. Verifique se o OAuth está configurado no Supabase.',
        variant: 'destructive',
      });
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/30 flex flex-col items-center justify-center p-6">
      <div className="max-w-md w-full space-y-8 animate-fade-in">
        <div className="text-center space-y-4">
          <div className="inline-block animate-breathe">
            <div className="w-20 h-20 bg-lavanda-profunda rounded-full flex items-center justify-center shadow-lg">
              <Heart size={40} className="text-white" fill="white" />
            </div>
          </div>
          
          <h1 className="text-3xl font-heading font-bold text-azul-salvia">
            Entrar na Acollya
          </h1>
          
          <p className="text-azul-salvia/70">
            Que bom ter você de volta
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
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              className="h-12 rounded-xl border-cinza-neutro focus:border-lavanda-profunda"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password" className="text-azul-salvia font-medium">
              Senha
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              className="h-12 rounded-xl border-cinza-neutro focus:border-lavanda-profunda"
            />
          </div>

          <div className="flex justify-end">
            <Link to="/forgot-password">
              <TertiaryButton type="button">
                Esqueci minha senha
              </TertiaryButton>
            </Link>
          </div>

          <PrimaryButton
            type="submit"
            isLoading={isLoading}
            className="w-full"
          >
            Entrar
          </PrimaryButton>
        </form>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-cinza-neutro" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-offwhite text-cinza-calmo">ou</span>
          </div>
        </div>

        <button
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className="w-full h-12 px-6 rounded-xl border-2 border-cinza-neutro bg-white text-azul-salvia font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Continuar com Google
        </button>

        <div className="text-center">
          <p className="text-sm text-azul-salvia/70">
            Ainda não tem conta?{' '}
            <Link to="/register" className="text-lavanda-profunda font-semibold hover:underline">
              Criar conta
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}