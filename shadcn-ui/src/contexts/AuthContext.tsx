import { createContext, useContext, useEffect, useState } from 'react';
import { User as SupabaseUser } from '@supabase/supabase-js';
import { supabase, isDemoMode } from '@/lib/supabase';
import { User } from '@/types/user';
import { analyticsEvents, setAnalyticsUserId, setAnalyticsUserProperties } from '@/lib/firebase';
import { useAuthStore } from '@/store/authStore';

interface AuthContextType {
  user: User | null;
  supabaseUser: SupabaseUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signUp: (email: string, password: string, name: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  logout: () => Promise<void>; // Alias for signOut
  updateUserProfile: (updates: Partial<User>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// Helper to log session events to Supabase
const logSessionEvent = async (
  userId: string,
  eventType: 'login' | 'logout',
  sessionType: string = 'email'
) => {
  if (isDemoMode() || !supabase) return;

  try {
    if (eventType === 'login') {
      await supabase.from('user_sessions').insert({
        user_id: userId,
        session_type: sessionType,
        login_at: new Date().toISOString(),
        user_agent: navigator.userAgent,
      });
      console.log('✅ [Session] Login event logged');
    } else if (eventType === 'logout') {
      // Update the most recent session that has no logout_at
      const { data: sessions } = await supabase
        .from('user_sessions')
        .select('id')
        .eq('user_id', userId)
        .is('logout_at', null)
        .order('login_at', { ascending: false })
        .limit(1);

      if (sessions && sessions.length > 0) {
        await supabase
          .from('user_sessions')
          .update({ logout_at: new Date().toISOString() })
          .eq('id', sessions[0].id);
        console.log('✅ [Session] Logout event logged');
      } else {
        // No open session found, create a complete record
        await supabase.from('user_sessions').insert({
          user_id: userId,
          session_type: sessionType,
          login_at: new Date().toISOString(),
          logout_at: new Date().toISOString(),
          user_agent: navigator.userAgent,
        });
        console.log('✅ [Session] Logout event logged (no open session found)');
      }
    }
  } catch (error) {
    // Don't block the auth flow if session logging fails
    console.warn('⚠️ [Session] Failed to log session event:', error);
  }
};

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [supabaseUser, setSupabaseUser] = useState<SupabaseUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const authStore = useAuthStore();

  // Sync authStore user to context when authStore changes
  useEffect(() => {
    if (authStore.user && !user) {
      setUser(authStore.user);
    }
  }, [authStore.user]);

  useEffect(() => {
    // Initialize auth state
    initializeAuth();

    // Listen for auth changes (only in production mode)
    if (!isDemoMode() && supabase) {
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, session) => {
          console.log('🔄 [Auth] State changed:', event);
          
          if (session?.user) {
            setSupabaseUser(session.user);
            await loadUserProfile(session.user.id);
          } else if (event === 'SIGNED_OUT') {
            setUser(null);
            setSupabaseUser(null);
            // Also clear authStore
            authStore.logout();
          }
        }
      );

      return () => {
        subscription.unsubscribe();
      };
    }
  }, []);

  const initializeAuth = async () => {
    if (isDemoMode()) {
      // Demo mode: use localStorage
      const storedUser = localStorage.getItem('acollya_user');
      if (storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser);
          setUser(parsedUser);
          
          // Set analytics user
          setAnalyticsUserId(parsedUser.id);
          setAnalyticsUserProperties({
            plan: parsedUser.planCode === 1 ? 'premium' : 'free',
          });
        } catch (e) {
          console.error('Error parsing stored user:', e);
          localStorage.removeItem('acollya_user');
        }
      }
      setIsLoading(false);
      return;
    }

    // Production mode: use Supabase
    if (!supabase) {
      setIsLoading(false);
      return;
    }

    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (session?.user) {
        setSupabaseUser(session.user);
        await loadUserProfile(session.user.id);
      }
    } catch (error) {
      console.error('Error initializing auth:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadUserProfile = async (userId: string) => {
    if (!supabase) return;

    try {
      const { data, error } = await supabase
        .from('users')
        .select('*')
        .eq('id', userId)
        .single();

      if (error) throw error;

      if (data) {
        const userProfile: User = {
          id: data.id,
          email: data.email,
          name: data.name,
          phone: data.phone || '',
          birthDate: data.birth_date || '',
          gender: data.gender || '',
          planCode: data.plan_code,
          trialEndsAt: data.trial_ends_at || '',
          termsAccepted: data.terms_accepted,
          termsAcceptedDate: data.terms_accepted_date || '',
        };

        setUser(userProfile);
        
        // Sync to authStore
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
          authStore.login(userProfile, session.access_token);
        }
        
        // Set analytics user
        setAnalyticsUserId(userProfile.id);
        setAnalyticsUserProperties({
          plan: userProfile.planCode === 1 ? 'premium' : 'free',
        });
      }
    } catch (error) {
      console.error('Error loading user profile:', error);
    }
  };

  const signUp = async (email: string, password: string, name: string) => {
    if (isDemoMode()) {
      // Demo mode: create mock user
      const mockUser: User = {
        id: `demo_${Date.now()}`,
        email,
        name,
        phone: '',
        birthDate: '',
        gender: '',
        planCode: 0,
        trialEndsAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        termsAccepted: false,
        termsAcceptedDate: '',
      };
      
      localStorage.setItem('acollya_user', JSON.stringify(mockUser));
      localStorage.setItem('acollya_token', 'demo_token');
      setUser(mockUser);
      authStore.login(mockUser, 'demo_token');
      
      analyticsEvents.signUp('email');
      return;
    }

    if (!supabase) throw new Error('Supabase not configured');

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          name,
        },
      },
    });

    if (error) throw error;

    if (data.user) {
      setSupabaseUser(data.user);
      await loadUserProfile(data.user.id);
      
      // Log session
      await logSessionEvent(data.user.id, 'login', 'email');
      
      analyticsEvents.signUp('email');
    }
  };

  const signIn = async (email: string, password: string) => {
    if (isDemoMode()) {
      // Demo mode: simulate login
      const storedUser = localStorage.getItem('acollya_user');
      if (storedUser) {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
        authStore.login(parsedUser, 'demo_token');
        analyticsEvents.login('email');
        return;
      }
      throw new Error('Usuário não encontrado');
    }

    if (!supabase) throw new Error('Supabase not configured');

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;

    if (data.user) {
      setSupabaseUser(data.user);
      await loadUserProfile(data.user.id);
      
      // Log session
      await logSessionEvent(data.user.id, 'login', 'email');
      
      analyticsEvents.login('email');
    }
  };

  const handleSignOut = async () => {
    console.log('🚪 [Auth] Starting logout...');
    
    const currentUserId = user?.id || supabaseUser?.id;

    if (isDemoMode()) {
      // Demo mode: clear localStorage
      localStorage.removeItem('acollya_user');
      localStorage.removeItem('acollya_token');
      sessionStorage.clear();
      setUser(null);
      authStore.logout();
      analyticsEvents.logout();
      console.log('✅ [Auth] Demo logout complete');
      return;
    }

    // Log logout event BEFORE signing out (we need the session to be active)
    if (currentUserId) {
      await logSessionEvent(currentUserId, 'logout');
    }

    // Clear all local state first
    setUser(null);
    setSupabaseUser(null);
    setAnalyticsUserId(null);
    authStore.logout();
    
    // Clear all storage
    localStorage.removeItem('acollya_user');
    localStorage.removeItem('acollya_token');
    sessionStorage.clear();

    // Sign out from Supabase
    if (supabase) {
      try {
        const { error } = await supabase.auth.signOut();
        if (error) {
          console.error('⚠️ [Auth] Supabase signOut error:', error);
          // Don't throw - we already cleared local state
        }
      } catch (error) {
        console.error('⚠️ [Auth] Supabase signOut exception:', error);
        // Don't throw - we already cleared local state
      }
    }

    analyticsEvents.logout();
    console.log('✅ [Auth] Production logout complete');
  };

  const updateUserProfile = async (updates: Partial<User>) => {
    if (!user) return;

    if (isDemoMode()) {
      // Demo mode: update localStorage
      const updatedUser = { ...user, ...updates };
      localStorage.setItem('acollya_user', JSON.stringify(updatedUser));
      setUser(updatedUser);
      authStore.updateUser(updatedUser);
      return;
    }

    if (!supabase) throw new Error('Supabase not configured');

    const { error } = await supabase
      .from('users')
      .update({
        name: updates.name,
        phone: updates.phone,
        birth_date: updates.birthDate,
        gender: updates.gender,
        terms_accepted: updates.termsAccepted,
        terms_accepted_date: updates.termsAcceptedDate,
        updated_at: new Date().toISOString(),
      })
      .eq('id', user.id);

    if (error) throw error;

    const updatedUser = { ...user, ...updates };
    setUser(updatedUser);
    authStore.updateUser(updatedUser);
  };

  const value: AuthContextType = {
    user,
    supabaseUser,
    isLoading,
    isAuthenticated: !!user,
    signUp,
    signIn,
    signOut: handleSignOut,
    logout: handleSignOut, // Alias for backward compatibility
    updateUserProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};