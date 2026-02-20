import { User } from '@/types/user';

export function isTrialExpired(user: User): boolean {
  if (user.planCode !== 0) return false; // Premium users never expire
  
  const registrationDate = new Date(user.registrationDate);
  const now = new Date();
  const daysSinceRegistration = Math.floor((now.getTime() - registrationDate.getTime()) / (1000 * 60 * 60 * 24));
  
  return daysSinceRegistration > 14;
}

export function getDaysSinceRegistration(user: User): number {
  const registrationDate = new Date(user.registrationDate);
  const now = new Date();
  return Math.floor((now.getTime() - registrationDate.getTime()) / (1000 * 60 * 60 * 24));
}

export function getTrialDaysRemaining(user: User): number {
  const daysSince = getDaysSinceRegistration(user);
  return Math.max(0, 14 - daysSince);
}

export function canAccessRestrictedFeature(user: User | null): boolean {
  if (!user) return false;
  if (user.planCode === 1) return true; // Premium
  return !isTrialExpired(user);
}