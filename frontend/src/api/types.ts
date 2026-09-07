/**
 * Shared domain types used across multiple API modules.
 * Mirrors backend enums so TypeScript catches mismatches at compile time.
 */

export type LeadStage =
  | 'NEW'
  | 'CONTACTED'
  | 'SITE_VISIT'
  | 'INTERESTED'
  | 'NEGOTIATION'
  | 'BOOKED'
  | 'LOST';

export type LeadSource =
  | 'WEBSITE'
  | 'REFERRAL'
  | 'ADVERTISEMENT'
  | 'WALK_IN'
  | 'SOCIAL_MEDIA'
  | 'OTHER';

export type FollowUpStatus = 'PENDING' | 'COMPLETED' | 'CANCELLED';

export type UserRole = 'ADMIN' | 'SALES';
