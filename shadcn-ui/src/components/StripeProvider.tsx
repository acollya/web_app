import { Elements } from '@stripe/react-stripe-js';
import { getStripe } from '@/lib/stripe';

interface StripeProviderProps {
  children: React.ReactNode;
}

export const StripeProvider = ({ children }: StripeProviderProps) => {
  const stripePromise = getStripe();

  if (!stripePromise) {
    // If Stripe is not configured, just render children without Stripe context
    return <>{children}</>;
  }

  return <Elements stripe={stripePromise}>{children}</Elements>;
};