import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';
import { useAuth } from '@/hooks/useAuth';
import { Shield, Info, CreditCard, LogOut, User, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function Profile() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const menuItems = [
    { icon: User, label: 'Meus Dados', path: '/profile/my-data' },
    { icon: Shield, label: 'Privacidade e Segurança', path: '/privacy-security' },
    { icon: Info, label: 'Sobre a Acollya', path: '/about' },
    { icon: CreditCard, label: 'Gerenciar Plano', path: '/subscription' },
  ];

  const handleLogout = async () => {
    console.log('🚪 [Profile] Logout button clicked');
    setIsLoggingOut(true);

    try {
      await logout();
      
      console.log('✅ [Profile] Logout successful, navigating to /login');
      
      toast({
        title: 'Até logo!',
        description: 'Você saiu da sua conta com sucesso.',
      });

      navigate('/login', { replace: true });
    } catch (error) {
      console.error('❌ [Profile] Logout error:', error);
      
      toast({
        title: 'Erro ao sair',
        description: 'Ocorreu um erro, mas sua sessão local foi encerrada.',
        variant: 'destructive',
      });

      // Even if there's an error, force navigate to login
      navigate('/login', { replace: true });
    } finally {
      setIsLoggingOut(false);
    }
  };

  const planName = user?.planCode === 1 ? 'Premium' : 'Gratuito';

  return (
    <Layout>
      <div className="px-6 py-8 space-y-8">
        <PageHeader title="Perfil" />

        <div className="text-center space-y-4">
          <div className="w-24 h-24 bg-lavanda-serenidade rounded-full flex items-center justify-center mx-auto text-4xl font-heading font-bold text-lavanda-profunda">
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-2xl font-heading font-bold text-azul-salvia">
              {user?.name}
            </h1>
            <p className="text-sm text-azul-salvia/70">{user?.email}</p>
            <div className="inline-block mt-2 px-4 py-1 rounded-full bg-lavanda-serenidade text-xs font-medium text-lavanda-profunda">
              Plano {planName}
            </div>
          </div>
        </div>

        <div className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className="w-full bg-white rounded-xl p-4 flex items-center gap-4 hover:shadow-md transition-shadow"
              >
                <Icon size={24} className="text-lavanda-profunda" />
                <span className="flex-1 text-left font-medium text-azul-salvia">
                  {item.label}
                </span>
                <span className="text-cinza-calmo">›</span>
              </button>
            );
          })}
        </div>

        <button
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="w-full bg-white rounded-xl p-4 flex items-center gap-4 hover:shadow-md transition-shadow border border-red-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoggingOut ? (
            <Loader2 size={24} className="text-red-500 animate-spin" />
          ) : (
            <LogOut size={24} className="text-red-500" />
          )}
          <span className="flex-1 text-left font-medium text-red-500">
            {isLoggingOut ? 'Saindo...' : 'Sair'}
          </span>
        </button>
      </div>
    </Layout>
  );
}