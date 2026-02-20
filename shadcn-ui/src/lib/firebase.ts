import { initializeApp, FirebaseApp } from 'firebase/app';
import { getAnalytics, Analytics, logEvent as firebaseLogEvent, setUserId, setUserProperties } from 'firebase/analytics';

// Firebase configuration
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

// Check if Firebase is configured
export const isFirebaseConfigured = () => {
  return Boolean(
    firebaseConfig.apiKey &&
    firebaseConfig.projectId &&
    firebaseConfig.apiKey !== 'your_firebase_api_key_here'
  );
};

// Initialize Firebase
let app: FirebaseApp | null = null;
let analytics: Analytics | null = null;

if (isFirebaseConfigured()) {
  try {
    app = initializeApp(firebaseConfig);
    analytics = getAnalytics(app);
    console.log('Firebase Analytics initialized successfully');
  } catch (error) {
    console.error('Error initializing Firebase:', error);
  }
}

// Analytics helper functions
export const logEvent = (eventName: string, eventParams?: Record<string, string | number | boolean>) => {
  if (!analytics) {
    console.log('[Demo Mode] Analytics event:', eventName, eventParams);
    return;
  }
  
  try {
    firebaseLogEvent(analytics, eventName, eventParams);
  } catch (error) {
    console.error('Error logging event:', error);
  }
};

export const setAnalyticsUserId = (userId: string | null) => {
  if (!analytics) return;
  
  try {
    setUserId(analytics, userId);
  } catch (error) {
    console.error('Error setting user ID:', error);
  }
};

export const setAnalyticsUserProperties = (properties: Record<string, string | number | boolean>) => {
  if (!analytics) return;
  
  try {
    setUserProperties(analytics, properties);
  } catch (error) {
    console.error('Error setting user properties:', error);
  }
};

// Predefined analytics events
export const analyticsEvents = {
  // Authentication
  signUp: (method: string) => logEvent('sign_up', { method }),
  login: (method: string) => logEvent('login', { method }),
  logout: () => logEvent('logout'),
  
  // User Actions
  moodCheckin: (mood: string) => logEvent('mood_checkin', { mood }),
  journalEntry: () => logEvent('journal_entry_created'),
  chatMessage: () => logEvent('chat_message_sent'),
  
  // Programs
  programStarted: (programId: string, programName: string) => 
    logEvent('program_started', { program_id: programId, program_name: programName }),
  programCompleted: (programId: string, programName: string) => 
    logEvent('program_completed', { program_id: programId, program_name: programName }),
  chapterViewed: (programId: string, chapterId: string) => 
    logEvent('chapter_viewed', { program_id: programId, chapter_id: chapterId }),
  
  // Appointments
  appointmentBooked: (therapistId: string, amount: number) => 
    logEvent('appointment_booked', { therapist_id: therapistId, value: amount, currency: 'BRL' }),
  appointmentCancelled: (appointmentId: string) => 
    logEvent('appointment_cancelled', { appointment_id: appointmentId }),
  
  // Subscription
  subscriptionStarted: (plan: string, amount: number) => 
    logEvent('purchase', { 
      transaction_id: `sub_${Date.now()}`,
      value: amount, 
      currency: 'BRL',
      items: JSON.stringify([{ item_id: plan, item_name: `Plano ${plan}` }])
    }),
  subscriptionCancelled: (plan: string) => 
    logEvent('subscription_cancelled', { plan }),
  
  // Page Views
  pageView: (pageName: string, pageTitle: string) => 
    logEvent('page_view', { page_name: pageName, page_title: pageTitle }),
  
  // Errors
  error: (errorMessage: string, errorContext?: string) => 
    logEvent('error', { error_message: errorMessage, error_context: errorContext || '' }),
};

export { analytics };