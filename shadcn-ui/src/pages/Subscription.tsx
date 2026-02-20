import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useAuth } from '@/hooks/useAuth';
import { supabase } from '@/lib/supabase';
import { Check, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function Subscription() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuth();
  const [loadingPlan, setLoadingPlan] = useState<'monthly' | 'yearly' | null>(null);

  const plans = [
    {
      name: 'Gratuito',
      price: 'R$ 0',
      features: [
        'Check-ins de humor ilimitados',
        'Diário emocional',
        'Chat com IA (10 mensagens/dia)',
        '1 programa gratuito de autocuidado',
      ],
    },
    {
      name: 'Premium Mensal',
      price: 'R$ 17,90/mês',
      priceId: import.meta.env.VITE_STRIPE_PRICE_ID_MONTHLY,
      planType: 'monthly' as const,
      popular: true,
      features: [
        'Tudo do plano gratuito',
        'Chat com IA ilimitado',
        'Todos os programas gratuitos de autocuidado',
        'Análises detalhadas de humor',
        'Acesso prioritário a psicólogos',
        'Sem anúncios',
      ],
    },
    {
      name: 'Premium Anual',
      price: 'R$ 179,90/ano',
      priceId: import.meta.env.VITE_STRIPE_PRICE_ID_YEARLY,
      planType: 'yearly' as const,
      badge: 'Economia de 17%',
      features: [
        'Tudo do plano gratuito',
        'Chat com IA ilimitado',
        'Todos os programas gratuitos de autocuidado',
        'Análises detalhadas de humor',
        'Acesso prioritário a psicólogos',
        'Sem anúncios',
        '2 meses grátis (equivalente a R$ 14,99/mês)',
      ],
    },
  ];

  const handleUpgrade = async (
    priceId: string, 
    planName: string, 
    planType: 'monthly' | 'yearly',
    e: React.MouseEvent<HTMLButtonElement>
  ) => {
    // Prevent event propagation and default behavior
    e.preventDefault();
    e.stopPropagation();

    console.log('🚀 [Subscription] handleUpgrade called:', { priceId, planName, planType });

    if (!user || !supabase) {
      console.error('❌ [Subscription] User not logged in or Supabase not initialized');
      toast({
        title: 'Erro',
        description: 'Você precisa estar logado para assinar',
        variant: 'destructive',
      });
      return;
    }

    // Validate Price ID format
    if (!priceId) {
      console.error('❌ [Subscription] Price ID is empty');
      toast({
        title: 'Erro de configuração',
        description: 'ID do plano não configurado. Entre em contato com o suporte.',
        variant: 'destructive',
      });
      return;
    }

    // Check if Price ID starts with "price_" or "prod_"
    if (!priceId.startsWith('price_') && !priceId.startsWith('prod_')) {
      console.error('❌ [Subscription] Invalid Price ID format:', priceId);
      toast({
        title: 'Erro de configuração',
        description: 'ID do plano inválido. Entre em contato com o suporte.',
        variant: 'destructive',
      });
      return;
    }

    console.log('✅ [Subscription] Validation passed, setting loading state');
    setLoadingPlan(planType);

    try {
      console.log('📡 [Subscription] Showing processing toast');
      toast({
        title: 'Processando...',
        description: 'Redirecionando para o checkout seguro do Stripe',
      });

      console.log('📡 [Subscription] Calling Edge Function create-checkout with:', {
        priceId,
        successUrl: `${window.location.origin}/subscription?success=true`,
        cancelUrl: `${window.location.origin}/subscription?canceled=true`,
      });

      // Call Supabase Edge Function to create checkout session
      const { data, error } = await supabase.functions.invoke('create-checkout', {
        body: {
          priceId: priceId,
          successUrl: `${window.location.origin}/subscription?success=true`,
          cancelUrl: `${window.location.origin}/subscription?canceled=true`,
        },
      });

      console.log('📡 [Subscription] Edge Function response:', { data, error });

      if (error) {
        console.error('❌ [Subscription] Error from Edge Function:', error);
        throw new Error(error.message || 'Erro ao criar sessão de checkout');
      }

      if (data?.url) {
        console.log('✅ [Subscription] Checkout URL received:', data.url);
        console.log('🔄 [Subscription] Redirecting to Stripe Checkout...');
        
        // Redirect to Stripe Checkout
        window.location.href = data.url;
      } else {
        console.error('❌ [Subscription] No URL returned from Edge Function:', data);
        throw new Error('URL de checkout não retornada');
      }
    } catch (error) {
      console.error('❌ [Subscription] Subscription error:', error);
      
      toast({
        title: 'Erro no pagamento',
        description: error instanceof Error ? error.message : 'Não foi possível processar a assinatura. Tente novamente.',
        variant: 'destructive',
      });
      
      setLoadingPlan(null);
    }
  };

  const currentPlan = user?.planCode === 1 ? 'Premium' : 'Gratuito';

  console.log('🎨 [Subscription] Rendering with:', { 
    user: user?.email, 
    currentPlan, 
    loadingPlan,
    priceIdMonthly: import.meta.env.VITE_STRIPE_PRICE_ID_MONTHLY,
    priceIdYearly: import.meta.env.VITE_STRIPE_PRICE_ID_YEARLY,
  });

  return (
    <Layout showBottomNav={false}>
      <div className="px-6 py-8">
        <PageHeader title="Planos e Assinaturas" subtitle="Escolha o melhor para você" />

        <div className="space-y-4 max-w-2xl">
          {plans.map((plan) => {
            const isCurrentPlan = plan.name.includes(currentPlan);
            const isPremiumMonthly = plan.name === 'Premium Mensal';
            const isPremiumYearly = plan.name === 'Premium Anual';
            const isLoading = plan.planType && loadingPlan === plan.planType;

            return (
              <div
                key={plan.name}
                className={`bg-white rounded-2xl p-6 shadow-sm ${
                  plan.popular ? 'border-2 border-lavanda-profunda' : ''
                } ${
                  plan.badge ? 'border-2 border-verde-nevoa' : ''
                }`}
              >
                {plan.popular && (
                  <div className="inline-block bg-lavanda-profunda text-white text-xs font-semibold px-3 py-1 rounded-full mb-4">
                    Mais popular
                  </div>
                )}
                {plan.badge && (
                  <div className="inline-block bg-verde-nevoa text-white text-xs font-semibold px-3 py-1 rounded-full mb-4">
                    {plan.badge}
                  </div>
                )}
                
                <h3 className="text-xl font-heading font-bold text-azul-salvia mb-2">
                  {plan.name}
                </h3>
                <p className="text-3xl font-heading font-bold text-lavanda-profunda mb-6">
                  {plan.price}
                </p>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <Check size={20} className="text-verde-nevoa flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-azul-salvia">{feature}</span>
                    </li>
                  ))}
                </ul>

                {isPremiumMonthly && !isCurrentPlan && (
                  <PrimaryButton 
                    type="button"
                    onClick={(e) => handleUpgrade(plan.priceId || '', plan.name, 'monthly', e)} 
                    disabled={loadingPlan !== null}
                    isLoading={isLoading}
                    className="w-full"
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Processando...
                      </span>
                    ) : (
                      'Assinar Mensal'
                    )}
                  </PrimaryButton>
                )}

                {isPremiumYearly && !isCurrentPlan && (
                  <PrimaryButton 
                    type="button"
                    onClick={(e) => handleUpgrade(plan.priceId || '', plan.name, 'yearly', e)} 
                    disabled={loadingPlan !== null}
                    isLoading={isLoading}
                    className="w-full bg-verde-nevoa hover:bg-verde-nevoa/90"
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Processando...
                      </span>
                    ) : (
                      'Assinar Anual'
                    )}
                  </PrimaryButton>
                )}

                {isCurrentPlan && (
                  <div className="w-full h-12 bg-verde-nevoa/30 rounded-xl flex items-center justify-center text-azul-salvia font-semibold">
                    Plano Atual
                  </div>
                )}
              </div>
            );
          })}

          <div className="bg-lavanda-serenidade/20 rounded-2xl p-5 mt-6">
            <p className="text-sm text-azul-salvia leading-relaxed">
              <strong>Método de pagamento:</strong> Cartão de Crédito via Stripe
              <br />
              <span className="text-xs text-azul-salvia/70 mt-1 block">
                O pagamento será processado de forma segura através do Stripe. A assinatura é recorrente e pode ser cancelada a qualquer momento através do portal do cliente.
              </span>
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}