import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';
import { PrimaryButton } from '@/components/PrimaryButton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { userService } from '@/services/userService';
import { useAuthStore } from '@/store/authStore';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { useToast } from '@/hooks/use-toast';

export default function MyData() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user, setUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    whatsapp: '',
  });

  useEffect(() => {
    const loadUserData = async () => {
      try {
        const userData = await userService.getUser();
        setFormData({
          name: userData.name,
          whatsapp: userData.whatsapp || '',
        });
      } catch (error) {
        console.error('Error loading user data:', error);
        toast({
          title: 'Erro ao carregar dados',
          description: 'Tente novamente mais tarde',
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    loadUserData();
  }, [toast]);

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast({
        title: 'Nome obrigatório',
        description: 'Por favor, preencha seu nome',
        variant: 'destructive',
      });
      return;
    }

    setIsSaving(true);

    try {
      const updatedUser = await userService.updateUser({
        name: formData.name.trim(),
        whatsapp: formData.whatsapp.trim() || undefined,
      });

      setUser(updatedUser);

      toast({
        title: 'Dados atualizados!',
        description: 'Suas informações foram salvas com sucesso',
      });

      // Navigate to home after successful save
      navigate('/home');
    } catch (error) {
      toast({
        title: 'Erro ao salvar',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <Layout showBottomNav={false}>
        <div className="h-screen flex items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      </Layout>
    );
  }

  const planName = user?.planCode === 1 ? 'Premium' : 'Gratuito';
  const registrationDate = user?.registrationDate 
    ? new Date(user.registrationDate).toLocaleDateString('pt-BR')
    : '-';

  return (
    <Layout showBottomNav={false}>
      <div className="px-6 py-8">
        <PageHeader title="Meus Dados" subtitle="Informações da sua conta" showBack onBack={() => navigate('/profile')} />

        <div className="space-y-6 max-w-2xl">
          {/* Data de Cadastro */}
          <div className="space-y-2">
            <Label className="text-azul-salvia font-medium">
              Data de Cadastro
            </Label>
            <div className="h-12 px-4 rounded-xl border border-cinza-neutro bg-gray-50 flex items-center text-azul-salvia/70">
              {registrationDate}
            </div>
          </div>

          {/* Nome */}
          <div className="space-y-2">
            <Label htmlFor="name" className="text-azul-salvia font-medium">
              Nome <span className="text-pessego">*</span>
            </Label>
            <Input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Seu nome completo"
              required
              className="h-12 rounded-xl border-cinza-neutro focus:border-lavanda-profunda"
            />
          </div>

          {/* E-mail */}
          <div className="space-y-2">
            <Label className="text-azul-salvia font-medium">
              E-mail
            </Label>
            <div className="h-12 px-4 rounded-xl border border-cinza-neutro bg-gray-50 flex items-center text-azul-salvia/70">
              {user?.email}
            </div>
          </div>

          {/* WhatsApp */}
          <div className="space-y-2">
            <Label htmlFor="whatsapp" className="text-azul-salvia font-medium">
              WhatsApp (opcional)
            </Label>
            <Input
              id="whatsapp"
              type="tel"
              value={formData.whatsapp}
              onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
              placeholder="+55 11 98765-4321"
              className="h-12 rounded-xl border-cinza-neutro focus:border-lavanda-profunda"
            />
            <p className="text-xs text-azul-salvia/60">
              Formato: +55 11 98765-4321
            </p>
          </div>

          {/* Plano Atual */}
          <div className="space-y-2">
            <Label className="text-azul-salvia font-medium">
              Plano Atual
            </Label>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-12 px-4 rounded-xl border border-cinza-neutro bg-gray-50 flex items-center text-azul-salvia/70">
                {planName}
              </div>
              {user?.planCode === 0 && (
                <button
                  onClick={() => navigate('/subscription')}
                  className="h-12 px-6 bg-lavanda-profunda text-white rounded-xl font-semibold hover:bg-lavanda-profunda/90 transition-colors whitespace-nowrap"
                >
                  Fazer Upgrade
                </button>
              )}
            </div>
            {user?.planCode === 0 && (
              <p className="text-xs text-azul-salvia/60">
                Faça upgrade para Premium por R$ 17,90/mês e tenha acesso ilimitado
              </p>
            )}
          </div>

          {/* Save Button */}
          <div className="pt-4">
            <PrimaryButton
              onClick={handleSave}
              isLoading={isSaving}
              className="w-full"
            >
              Salvar Alterações
            </PrimaryButton>
          </div>
        </div>
      </div>
    </Layout>
  );
}