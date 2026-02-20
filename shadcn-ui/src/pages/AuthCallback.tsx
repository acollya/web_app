import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/lib/supabase';
import { useAuthStore } from '@/store/authStore';
import { supabaseAuthService } from '@/services/supabaseAuthService';
import { useToast } from '@/hooks/use-toast';

export default function AuthCallback() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const { toast } = useToast();

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        if (!supabase) {
          throw new Error('Supabase not configured');
        }

        // Get the session from the URL
        const { data: { session }, error } = await supabase.auth.getSession();

        if (error) {
          console.error('Error getting session:', error);
          throw error;
        }

        if (session && session.user) {
          // Wait a bit for the trigger to create the user (if it's a new signup)
          await new Promise(resolve => setTimeout(resolve, 1000));

          // Try to get user profile from database
          let userProfile = await supabaseAuthService.getUserProfile(session.user.id);

          // If user profile doesn't exist yet, create it manually
          if (!userProfile) {
            console.log('User profile not found, creating manually...');
            
            const { error: insertError } = await supabase
              .from('users')
              .insert({
                id: session.user.id,
                email: session.user.email,
                name: session.user.user_metadata?.full_name || 
                      session.user.user_metadata?.name || 
                      session.user.email?.split('@')[0] || 
                      'Usuário',
                trial_ends_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
                subscription_status: 'trialing',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              });

            if (insertError) {
              console.error('Error creating user profile:', insertError);
              // If error is duplicate key, ignore it (user was created by trigger)
              if (!insertError.message.includes('duplicate key')) {
                throw insertError;
              }
            }

            // Fetch the profile again
            userProfile = await supabaseAuthService.getUserProfile(session.user.id);
          }

          // Log Google SSO session
          try {
            await supabase.from('user_sessions').insert({
              user_id: session.user.id,
              session_type: 'google',
              login_at: new Date().toISOString(),
              user_agent: navigator.userAgent,
            });
            console.log('✅ [AuthCallback] Google SSO session logged');
          } catch (sessionError) {
            console.warn('⚠️ [AuthCallback] Failed to log session:', sessionError);
          }

          if (userProfile) {
            // Login with user profile data
            login(userProfile, session.access_token);
            
            toast({
              title: 'Login realizado com sucesso!',
              description: `Bem-vinda, ${userProfile.name}`,
            });

            // Navigate to home
            navigate('/home');
          } else {
            // Fallback: create a basic user object from auth data
            const basicUser = {
              id: session.user.id,
              email: session.user.email || '',
              name: session.user.user_metadata?.full_name || 
                    session.user.user_metadata?.name || 
                    session.user.email?.split('@')[0] || 
                    'Usuário',
              phone: '',
              birthDate: '',
              gender: '',
              planCode: 0,
              trialEndsAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
              termsAccepted: false,
              termsAcceptedDate: '',
            };

            login(basicUser, session.access_token);

            toast({
              title: 'Bem-vinda à Acollya!',
              description: 'Complete seu perfil para continuar',
            });

            navigate('/home');
          }
        } else {
          throw new Error('No session found');
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        
        toast({
          title: 'Erro na autenticação',
          description: 'Não foi possível completar o login. Tente novamente.',
          variant: 'destructive',
        });

        navigate('/login');
      }
    };

    handleAuthCallback();
  }, [navigate, login, toast]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-offwhite to-lavanda-serenidade/30 flex flex-col items-center justify-center p-6">
      <div className="text-center space-y-4">
        <div className="w-16 h-16 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin mx-auto"></div>
        <h2 className="text-xl font-heading font-semibold text-azul-salvia">
          Autenticando...
        </h2>
        <p className="text-sm text-azul-salvia/70">
          Por favor, aguarde enquanto completamos seu login
        </p>
      </div>
    </div>
  );
}