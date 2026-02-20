export type PlanType = 'free' | 'premium';

export interface Plan {
  id: string;
  name: string;
  type: PlanType;
  price: number;
  features: string[];
  popular?: boolean;
}

export interface Subscription {
  id: string;
  userId: string;
  planType: PlanType;
  startDate: string;
  endDate?: string;
  status: 'active' | 'cancelled' | 'expired';
}