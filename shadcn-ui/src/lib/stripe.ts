import { loadStripe, Stripe } from '@stripe/stripe-js';

const stripePublishableKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '';

// Check if Stripe is configured
export const isStripeConfigured = () => {
  return Boolean(stripePublishableKey && stripePublishableKey !== 'pk_test_your_stripe_publishable_key_here');
};

// Initialize Stripe
let stripePromise: Promise<Stripe | null> | null = null;

export const getStripe = () => {
  if (!isStripeConfigured()) {
    console.warn('Stripe is not configured. Using demo mode.');
    return null;
  }
  
  if (!stripePromise) {
    stripePromise = loadStripe(stripePublishableKey);
  }
  
  return stripePromise;
};

// Stripe product/price IDs (these should match your Stripe dashboard)
export const STRIPE_PRICES = {
  PREMIUM_MONTHLY: 'price_premium_monthly', // Replace with actual price ID
  PREMIUM_YEARLY: 'price_premium_yearly',   // Replace with actual price ID
};

// Helper to create checkout session
export const createCheckoutSession = async (priceId: string, userId: string) => {
  if (!isStripeConfigured()) {
    console.log('[Demo Mode] Would create checkout session for:', priceId);
    return { url: '/subscription?demo=success' };
  }
  
  try {
    // Call your Supabase Edge Function to create checkout session
    const response = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/create-checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${import.meta.env.VITE_SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        priceId,
        userId,
        successUrl: `${window.location.origin}/subscription?success=true`,
        cancelUrl: `${window.location.origin}/subscription?canceled=true`,
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to create checkout session');
    }
    
    const { sessionId, url } = await response.json();
    return { sessionId, url };
  } catch (error) {
    console.error('Error creating checkout session:', error);
    throw error;
  }
};

// Helper to create customer portal session
export const createPortalSession = async (customerId: string) => {
  if (!isStripeConfigured()) {
    console.log('[Demo Mode] Would create portal session for:', customerId);
    return { url: '/subscription?demo=portal' };
  }
  
  try {
    // Call your Supabase Edge Function to create portal session
    const response = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/create-portal`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${import.meta.env.VITE_SUPABASE_ANON_KEY}`,
      },
      body: JSON.stringify({
        customerId,
        returnUrl: `${window.location.origin}/subscription`,
      }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to create portal session');
    }
    
    const { url } = await response.json();
    return { url };
  } catch (error) {
    console.error('Error creating portal session:', error);
    throw error;
  }
};