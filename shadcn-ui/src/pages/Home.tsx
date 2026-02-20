import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { useAuth } from '@/hooks/useAuth';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { moodService } from '@/services/moodService';
import { MoodSummary } from '@/types/mood';
import { Heart, BookOpen, MessageCircle, Sparkles, TrendingUp, Calendar } from 'lucide-react';

export default function Home() {
  const navigate = useNavigate();
  const { user, isLoading: authLoading } = useAuth();
  const [moodSummary, setMoodSummary] = useState<MoodSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login');
    }
  }, [user, authLoading, navigate]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const summary = await moodService.getSummary();
        setMoodSummary(summary);
      } catch (error) {
        console.error('Error loading mood summary:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (user) {
      loadData();
    }
  }, [user]);

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-offwhite">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const cards = [
    {
      title: 'Fazer check-in de humor',
      description: 'Como você está se sentindo hoje?',
      icon: Heart,
      color: 'bg-pessego/30',
      iconColor: 'text-lavanda-profunda',
      path: '/mood-checkin',
    },
    {
      title: 'Escrever no diário',
      description: 'Registre seus pensamentos',
      icon: BookOpen,
      color: 'bg-lavanda-serenidade/40',
      iconColor: 'text-azul-salvia',
      path: '/journal',
    },
    {
      title: 'Falar com a Acollya',
      description: 'Chat com IA 24/7',
      icon: MessageCircle,
      color: 'bg-verde-nevoa/40',
      iconColor: 'text-lavanda-profunda',
      path: '/chat',
    },
    {
      title: 'Programas de autocuidado',
      description: 'Jornadas guiadas para você',
      icon: Sparkles,
      color: 'bg-lavanda-profunda/10',
      iconColor: 'text-lavanda-profunda',
      path: '/programs',
    },
    {
      title: 'Minhas Consultas',
      description: 'Agende com terapeutas',
      icon: Calendar,
      color: 'bg-verde-esperanca/20',
      iconColor: 'text-verde-esperanca',
      path: '/appointments',
    },
  ];

  return (
    <Layout>
      <div className="px-6 pt-8 pb-6 space-y-8">
        {/* Greeting */}
        <div className="animate-fade-in">
          <h1 className="text-3xl font-heading font-bold text-azul-salvia mb-2">
            Oi, {user?.name?.split(' ')[0]}! 👋
          </h1>
          <p className="text-lg text-azul-salvia/70">
            Como você está hoje?
          </p>
        </div>

        {/* Main Cards */}
        <div className="grid grid-cols-1 gap-4 animate-slide-up">
          {cards.map((card) => {
            const Icon = card.icon;
            return (
              <button
                key={card.path}
                onClick={() => navigate(card.path)}
                className={`${card.color} rounded-2xl p-6 text-left hover:shadow-lg transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]`}
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
                    <Icon size={24} className={card.iconColor} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-heading font-semibold text-azul-salvia text-lg mb-1">
                      {card.title}
                    </h3>
                    <p className="text-sm text-azul-salvia/70">
                      {card.description}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Mood Summary */}
        {moodSummary && moodSummary.last7Days && moodSummary.last7Days.length > 0 && (
          <div className="bg-white rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={20} className="text-lavanda-profunda" />
              <h2 className="font-heading font-semibold text-azul-salvia text-lg">
                Seus últimos 7 dias
              </h2>
            </div>

            {/* Simple mood visualization */}
            <div className="flex justify-between items-end h-32 gap-2">
              {moodSummary.last7Days.map((day, index) => {
                const heights = {
                  'muito-bem': 'h-full',
                  'bem': 'h-4/5',
                  'neutro': 'h-3/5',
                  'triste': 'h-2/5',
                  'muito-triste': 'h-1/5',
                };
                return (
                  <div key={index} className="flex-1 flex flex-col items-center gap-2">
                    <div className={`w-full ${heights[day.emotion]} bg-lavanda-profunda/80 rounded-t-lg transition-all`} />
                    <span className="text-xs text-cinza-calmo">
                      {new Date(day.date).toLocaleDateString('pt-BR', { weekday: 'short' })}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Insights */}
            {moodSummary.insights && moodSummary.insights.length > 0 && (
              <div className="pt-4 border-t border-cinza-neutro space-y-2">
                {moodSummary.insights.map((insight, index) => (
                  <p key={index} className="text-sm text-azul-salvia/80">
                    💡 {insight}
                  </p>
                ))}
              </div>
            )}

            {/* Recommendation */}
            {moodSummary.recommendation && (
              <div className="bg-pessego/20 rounded-xl p-4 border border-pessego/40">
                <p className="text-sm text-azul-salvia">
                  <strong className="font-semibold">Sugestão:</strong> {moodSummary.recommendation}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}