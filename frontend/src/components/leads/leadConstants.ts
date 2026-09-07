/**
 * Shared display constants for lead-related UI.
 * Centralises stage/source/follow-up display logic so every component uses
 * the same labels and colours.
 */
import type { LeadStage, LeadSource, FollowUpStatus } from '../../api/types';

// ── Stage ─────────────────────────────────────────────────────────────────────

export const STAGE_LABEL: Record<LeadStage, string> = {
  NEW:         'New',
  CONTACTED:   'Contacted',
  SITE_VISIT:  'Site Visit',
  INTERESTED:  'Interested',
  NEGOTIATION: 'Negotiation',
  BOOKED:      'Booked',
  LOST:        'Lost',
};

// Bootstrap badge bg class for each stage
export const STAGE_BADGE: Record<LeadStage, string> = {
  NEW:         'bg-secondary',
  CONTACTED:   'bg-info text-dark',
  SITE_VISIT:  'bg-primary',
  INTERESTED:  'bg-warning text-dark',
  NEGOTIATION: 'bg-orange',   // custom — see crm.css
  BOOKED:      'bg-success',
  LOST:        'bg-danger',
};

export const STAGE_OPTIONS: { value: LeadStage; label: string }[] = [
  { value: 'NEW',         label: 'New' },
  { value: 'CONTACTED',   label: 'Contacted' },
  { value: 'SITE_VISIT',  label: 'Site Visit' },
  { value: 'INTERESTED',  label: 'Interested' },
  { value: 'NEGOTIATION', label: 'Negotiation' },
  { value: 'BOOKED',      label: 'Booked' },
  { value: 'LOST',        label: 'Lost' },
];

// ── Source ────────────────────────────────────────────────────────────────────

export const SOURCE_LABEL: Record<LeadSource, string> = {
  WEBSITE:       'Website',
  REFERRAL:      'Referral',
  ADVERTISEMENT: 'Advertisement',
  WALK_IN:       'Walk-in',
  SOCIAL_MEDIA:  'Social Media',
  OTHER:         'Other',
};

export const SOURCE_OPTIONS: { value: LeadSource; label: string }[] = [
  { value: 'WEBSITE',       label: 'Website' },
  { value: 'REFERRAL',      label: 'Referral' },
  { value: 'ADVERTISEMENT', label: 'Advertisement' },
  { value: 'WALK_IN',       label: 'Walk-in' },
  { value: 'SOCIAL_MEDIA',  label: 'Social Media' },
  { value: 'OTHER',         label: 'Other' },
];

// ── Follow-up status ──────────────────────────────────────────────────────────

export const FOLLOW_UP_STATUS_LABEL: Record<FollowUpStatus, string> = {
  PENDING:   'Pending',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
};

export const FOLLOW_UP_STATUS_BADGE: Record<FollowUpStatus, string> = {
  PENDING:   'bg-warning text-dark',
  COMPLETED: 'bg-success',
  CANCELLED: 'bg-secondary',
};
