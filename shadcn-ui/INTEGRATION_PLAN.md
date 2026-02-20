# Acollya PWA - Stripe + Supabase + Firebase Analytics Integration Plan

## Overview
Complete integration of payment processing (Stripe), backend services (Supabase), and analytics tracking (Firebase) for the Acollya mental health PWA.

## Phase 1: Dependencies & Configuration

### 1.1 Install Required Packages
```bash
pnpm add @stripe/stripe-js stripe
pnpm add firebase
```

### 1.2 Environment Variables (.env.local)
```
# Supabase
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# Stripe
VITE_STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key

# Firebase
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_firebase_auth_domain
VITE_FIREBASE_PROJECT_ID=your_firebase_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_firebase_storage_bucket
VITE_FIREBASE_MESSAGING_SENDER_ID=your_firebase_messaging_sender_id
VITE_FIREBASE_APP_ID=your_firebase_app_id
VITE_FIREBASE_MEASUREMENT_ID=your_firebase_measurement_id
```

## Phase 2: Supabase Setup

### 2.1 Database Schema
Tables to create:
- users (extends auth.users)
- subscriptions
- mood_checkins
- journal_entries
- chat_messages
- programs
- program_progress
- appointments
- therapists

### 2.2 Row Level Security (RLS)
Enable RLS on all tables with policies for user data isolation.

### 2.3 Edge Functions
- stripe-webhook: Handle Stripe webhook events
- create-checkout: Create Stripe checkout sessions
- create-portal: Create Stripe customer portal sessions

## Phase 3: Stripe Integration

### 3.1 Frontend Components
- StripeProvider wrapper
- CheckoutButton component
- SubscriptionManager component

### 3.2 Payment Flow
1. User clicks upgrade → Create checkout session
2. Redirect to Stripe Checkout
3. Handle success/cancel redirects
4. Webhook updates subscription status

## Phase 4: Firebase Analytics

### 4.1 Events to Track
- User registration
- Login/Logout
- Mood check-in
- Journal entry created
- Chat message sent
- Program started/completed
- Appointment booked
- Subscription purchased
- Page views

### 4.2 Custom Parameters
- User plan (free/premium)
- Feature usage frequency
- Session duration
- Error tracking

## Phase 5: Migration Strategy

### 5.1 Dual Mode Support
- Demo mode: localStorage + mock data (current)
- Production mode: Supabase + Stripe + Firebase

### 5.2 Data Migration
- Provide migration scripts for existing localStorage data
- Graceful fallback if Supabase unavailable

## Phase 6: Testing & Documentation

### 6.1 Testing Checklist
- [ ] Auth flow (signup, login, logout)
- [ ] Subscription upgrade/downgrade
- [ ] Payment webhook processing
- [ ] Data persistence
- [ ] Analytics event firing
- [ ] Offline support

### 6.2 Documentation
- Setup guides for each service
- Environment variable configuration
- Deployment instructions
- Troubleshooting guide

## Implementation Order

1. ✅ Create integration plan
2. Install dependencies
3. Setup Supabase configuration & types
4. Create database schema SQL
5. Implement Supabase client & auth
6. Setup Firebase Analytics
7. Integrate Stripe checkout
8. Create Edge Functions (reference code)
9. Update services to use Supabase
10. Add analytics tracking throughout app
11. Create setup documentation
12. Test complete flow