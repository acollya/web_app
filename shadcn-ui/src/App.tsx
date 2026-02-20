import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { TermsGuard } from '@/components/TermsGuard';

// Onboarding & Auth
import Onboarding1 from './pages/Onboarding1';
import Onboarding2 from './pages/Onboarding2';
import Onboarding3 from './pages/Onboarding3';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import AuthCallback from './pages/AuthCallback';

// Main App
import Home from './pages/Home';
import MoodCheckin from './pages/MoodCheckin';
import Journal from './pages/Journal';
import JournalNew from './pages/JournalNew';
import Chat from './pages/Chat';
import Programs from './pages/Programs';
import ProgramsNew from './pages/ProgramsNew';
import ProgramDetail from './pages/ProgramDetail';
import ChapterView from './pages/ChapterView';
import Analytics from './pages/Analytics';
import Therapists from './pages/Therapists';
import TherapistDetail from './pages/TherapistDetail';
import Booking from './pages/Booking';
import Appointments from './pages/Appointments';
import AppointmentNew from './pages/AppointmentNew';
import AppointmentBook from './pages/AppointmentBook';
import AppointmentMy from './pages/AppointmentMy';
import AppointmentDetails from './pages/AppointmentDetails';
import Profile from './pages/Profile';
import MyData from './pages/MyData';
import Settings from './pages/Settings';
import Privacy from './pages/Privacy';
import PrivacySecurity from './pages/PrivacySecurity';
import About from './pages/About';
import Subscription from './pages/Subscription';
import Terms from './pages/Terms';
import PrivacyPolicy from './pages/PrivacyPolicy';
import NotFound from './pages/NotFound';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-offwhite">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <TermsGuard>
      {children}
    </TermsGuard>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Toaster />
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Navigate to="/onboarding-1" replace />} />
            <Route path="/onboarding-1" element={<Onboarding1 />} />
            <Route path="/onboarding-2" element={<Onboarding2 />} />
            <Route path="/onboarding-3" element={<Onboarding3 />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy-policy" element={<PrivacyPolicy />} />

            {/* Protected Routes */}
            <Route
              path="/home"
              element={
                <ProtectedRoute>
                  <Home />
                </ProtectedRoute>
              }
            />
            <Route
              path="/mood-checkin"
              element={
                <ProtectedRoute>
                  <MoodCheckin />
                </ProtectedRoute>
              }
            />
            <Route
              path="/journal"
              element={
                <ProtectedRoute>
                  <Journal />
                </ProtectedRoute>
              }
            />
            <Route
              path="/journal/new"
              element={
                <ProtectedRoute>
                  <JournalNew />
                </ProtectedRoute>
              }
            />
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <Chat />
                </ProtectedRoute>
              }
            />
            <Route
              path="/programs"
              element={
                <ProtectedRoute>
                  <ProgramsNew />
                </ProtectedRoute>
              }
            />
            <Route
              path="/programs/:id"
              element={
                <ProtectedRoute>
                  <ProgramDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/programs/:programId/chapter/:chapterId"
              element={
                <ProtectedRoute>
                  <ChapterView />
                </ProtectedRoute>
              }
            />
            <Route
              path="/appointments"
              element={
                <ProtectedRoute>
                  <Appointments />
                </ProtectedRoute>
              }
            />
            <Route
              path="/appointments/new"
              element={
                <ProtectedRoute>
                  <AppointmentNew />
                </ProtectedRoute>
              }
            />
            <Route
              path="/appointments/book/:therapistId"
              element={
                <ProtectedRoute>
                  <AppointmentBook />
                </ProtectedRoute>
              }
            />
            <Route
              path="/appointments/my"
              element={
                <ProtectedRoute>
                  <AppointmentMy />
                </ProtectedRoute>
              }
            />
            <Route
              path="/appointments/details/:id"
              element={
                <ProtectedRoute>
                  <AppointmentDetails />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <Analytics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/therapists"
              element={
                <ProtectedRoute>
                  <Therapists />
                </ProtectedRoute>
              }
            />
            <Route
              path="/therapists/:id"
              element={
                <ProtectedRoute>
                  <TherapistDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/booking/:therapistId"
              element={
                <ProtectedRoute>
                  <Booking />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route
              path="/profile/my-data"
              element={
                <ProtectedRoute>
                  <MyData />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <Settings />
                </ProtectedRoute>
              }
            />
            <Route
              path="/privacy"
              element={
                <ProtectedRoute>
                  <Privacy />
                </ProtectedRoute>
              }
            />
            <Route
              path="/privacy-security"
              element={
                <ProtectedRoute>
                  <PrivacySecurity />
                </ProtectedRoute>
              }
            />
            <Route
              path="/about"
              element={
                <ProtectedRoute>
                  <About />
                </ProtectedRoute>
              }
            />
            <Route
              path="/subscription"
              element={
                <ProtectedRoute>
                  <Subscription />
                </ProtectedRoute>
              }
            />

            {/* 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;