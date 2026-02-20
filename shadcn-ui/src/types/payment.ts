export type PaymentPlatform = 'google' | 'apple' | 'web';

export interface PaymentRequest {
  planType: 'premium';
  amount: number;
  currency: string;
  userId: string;
}

export interface PaymentResponse {
  success: boolean;
  transactionId?: string;
  subscriptionId?: string;
  message: string;
}

export interface SubscriptionStatus {
  isActive: boolean;
  planCode: number;
  expiresAt?: string;
  autoRenew: boolean;
}