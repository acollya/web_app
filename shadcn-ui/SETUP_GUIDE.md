# Acollya PWA - Complete Setup Guide

This guide will walk you through setting up Stripe, Supabase, and Firebase Analytics for the Acollya mental health PWA.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Supabase Setup](#supabase-setup)
3. [Stripe Setup](#stripe-setup)
4. [Firebase Setup](#firebase-setup)
5. [Environment Configuration](#environment-configuration)
6. [Testing](#testing)
7. [Deployment](#deployment)

---

## Prerequisites

- Node.js 18+ and pnpm installed
- A Supabase account (https://supabase.com)
- A Stripe account (https://stripe.com)
- A Firebase account (https://firebase.google.com)

---

## Supabase Setup

### 1. Create a New Supabase Project

1. Go to https://supabase.com/dashboard
2. Click "New Project"
3. Fill in project details:
   - Name: `acollya-pwa`
   - Database Password: (generate a strong password)
   - Region: Choose closest to your users
4. Wait for project to be created (~2 minutes)

### 2. Get Your Supabase Credentials

1. Go to Project Settings > API
2. Copy the following:
   - Project URL: `https://xxxxx.supabase.co`
   - Anon/Public Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Service Role Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (keep this secret!)

### 3. Run Database Schema

1. Go to SQL Editor in Supabase Dashboard
2. Click "New Query"
3. Copy the entire content from `supabase/schema.sql`
4. Paste and click "Run"
5. Verify all tables were created successfully

### 4. Configure Authentication

1. Go to Authentication > Providers
2. Enable Email provider
3. Configure email templates (optional):
   - Confirmation email
   - Password reset email
   - Magic link email

### 5. Setup Edge Functions

#### Install Supabase CLI

```bash
npm install -g supabase
```

#### Login to Supabase

```bash
supabase login
```

#### Link Your Project

```bash
supabase link --project-ref your-project-ref
```

#### Deploy Edge Functions

```bash
# Deploy stripe-webhook function
supabase functions deploy stripe-webhook --no-verify-jwt

# Deploy create-checkout function
supabase functions deploy create-checkout

# Deploy create-portal function
supabase functions deploy create-portal
```

#### Set Edge Function Secrets

```bash
# Set Stripe secret key
supabase secrets set STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key

# Set Stripe webhook secret (get this after creating webhook in Stripe)
supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

---

## Stripe Setup

### 1. Create a Stripe Account

1. Go to https://stripe.com
2. Sign up for an account
3. Complete business verification (for production)

### 2. Get Your Stripe Keys

1. Go to Developers > API Keys
2. Copy:
   - Publishable key: `pk_test_...`
   - Secret key: `sk_test_...` (keep this secret!)

### 3. Create Products and Prices

1. Go to Products in Stripe Dashboard
2. Create a new product:
   - Name: "Acollya Premium"
   - Description: "Premium subscription for Acollya mental health app"

3. Add pricing:
   - **Monthly Plan:**
     - Price: R$ 49.90/month
     - Billing period: Monthly
     - Copy the Price ID: `price_xxxxx`
   
   - **Yearly Plan:**
     - Price: R$ 499.00/year
     - Billing period: Yearly
     - Copy the Price ID: `price_xxxxx`

4. Update `src/lib/stripe.ts` with your Price IDs:
```typescript
export const STRIPE_PRICES = {
  PREMIUM_MONTHLY: 'price_xxxxx', // Your monthly price ID
  PREMIUM_YEARLY: 'price_xxxxx',  // Your yearly price ID
};
```

### 4. Setup Webhook

1. Go to Developers > Webhooks
2. Click "Add endpoint"
3. Endpoint URL: `https://your-project-ref.supabase.co/functions/v1/stripe-webhook`
4. Select events to listen to:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copy the Webhook Signing Secret: `whsec_xxxxx`
6. Add it to Supabase secrets:
```bash
supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

### 5. Test Stripe Integration

Use Stripe test cards:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- 3D Secure: `4000 0025 0000 3155`

---

## Firebase Setup

### 1. Create a Firebase Project

1. Go to https://console.firebase.google.com
2. Click "Add project"
3. Enter project name: `acollya-pwa`
4. Disable Google Analytics (optional, or enable for more features)
5. Click "Create project"

### 2. Register Your Web App

1. In Firebase Console, click the web icon (</>)
2. Register app:
   - App nickname: `Acollya PWA`
   - Check "Also set up Firebase Hosting" (optional)
3. Copy the Firebase configuration

### 3. Enable Analytics

1. Go to Analytics > Dashboard
2. Click "Enable Analytics"
3. Configure data streams
4. Copy your Measurement ID: `G-XXXXXXXXXX`

### 4. Get Firebase Credentials

From the Firebase SDK configuration, copy:
```javascript
{
  apiKey: "AIzaSy...",
  authDomain: "acollya-pwa.firebaseapp.com",
  projectId: "acollya-pwa",
  storageBucket: "acollya-pwa.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123",
  measurementId: "G-XXXXXXXXXX"
}
```

---

## Environment Configuration

### 1. Create .env.local File

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

### 2. Fill in Your Credentials

Edit `.env.local`:

```env
# Supabase
VITE_SUPABASE_URL=https://your-project-ref.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# Stripe
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key

# Firebase
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id
VITE_FIREBASE_APP_ID=your_firebase_app_id
VITE_FIREBASE_MEASUREMENT_ID=G-your_measurement_id

# Application Mode (demo or production)
VITE_APP_MODE=production
```

### 3. Verify Configuration

Run the app:

```bash
pnpm install
pnpm run dev
```

Check the browser console for:
- ✅ "Firebase Analytics initialized successfully"
- ✅ No Supabase connection errors
- ✅ Stripe loaded successfully

---

## Testing

### 1. Test Authentication Flow

1. Register a new user
2. Check Supabase Dashboard > Authentication > Users
3. Verify user profile was created in `users` table

### 2. Test Subscription Flow

1. Go to Subscription page
2. Click "Upgrade to Premium"
3. Use test card: `4242 4242 4242 4242`
4. Complete checkout
5. Verify:
   - Subscription created in Stripe Dashboard
   - User `plan_code` updated to 1 in Supabase
   - Subscription record created in `subscriptions` table

### 3. Test Analytics

1. Perform various actions (mood check-in, journal entry, etc.)
2. Go to Firebase Console > Analytics > Events
3. Verify events are being tracked (may take a few minutes to appear)

### 4. Test Data Persistence

1. Create mood check-ins, journal entries
2. Logout and login again
3. Verify data persists

---

## Deployment

### 1. Production Environment Variables

Set environment variables in your hosting platform (Vercel, Netlify, etc.):

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_production_anon_key
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_your_live_key
VITE_FIREBASE_API_KEY=your_production_api_key
# ... other Firebase config
VITE_APP_MODE=production
```

### 2. Switch Stripe to Live Mode

1. In Stripe Dashboard, toggle to "Live mode"
2. Get live API keys
3. Update webhook endpoint to production URL
4. Update environment variables with live keys

### 3. Build and Deploy

```bash
pnpm run build
```

Deploy the `dist` folder to your hosting platform.

---

## Troubleshooting

### Supabase Connection Issues

- Verify URL and anon key are correct
- Check if project is active in Supabase Dashboard
- Ensure RLS policies are properly configured

### Stripe Webhook Not Working

- Verify webhook URL is correct
- Check webhook signing secret matches
- Test webhook using Stripe CLI:
```bash
stripe listen --forward-to https://your-project.supabase.co/functions/v1/stripe-webhook
```

### Firebase Analytics Not Tracking

- Verify Measurement ID is correct
- Check browser console for errors
- Ensure cookies/tracking is not blocked
- Wait 24-48 hours for data to appear in Firebase Console

### Demo Mode vs Production Mode

The app supports two modes:

- **Demo Mode** (`VITE_APP_MODE=demo`): Uses localStorage, no backend required
- **Production Mode** (`VITE_APP_MODE=production`): Uses Supabase, Stripe, Firebase

To switch modes, update `VITE_APP_MODE` in your `.env.local` file.

---

## Support

For issues or questions:
- Supabase: https://supabase.com/docs
- Stripe: https://stripe.com/docs
- Firebase: https://firebase.google.com/docs

---

## Security Checklist

- [ ] Never commit `.env.local` to version control
- [ ] Use environment variables for all secrets
- [ ] Enable RLS on all Supabase tables
- [ ] Verify webhook signatures in Edge Functions
- [ ] Use HTTPS in production
- [ ] Regularly rotate API keys
- [ ] Monitor Stripe webhook logs for failures
- [ ] Set up Supabase database backups
- [ ] Configure Firebase security rules
- [ ] Enable 2FA on all service accounts