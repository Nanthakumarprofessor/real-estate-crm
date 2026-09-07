/**
 * Dashboard API module.
 *
 * Wraps GET /api/dashboard/summary.
 * The authenticated Axios instance automatically attaches the JWT.
 */
import apiClient from './axios';
import type { LeadStage } from './types';

// ── Response types (mirror backend DashboardSummaryResponse) ──────────────────

export interface LeadStatistics {
  total: number;
  by_stage: Record<LeadStage, number>;
}

export interface FollowUpStatistics {
  upcoming: number;
  overdue: number;
}

export interface PropertyStatistics {
  total_units: number;
  available_units: number;
  booked_units: number;
}

export interface BookingStatistics {
  confirmed: number;
  cancelled: number;
}

export interface DashboardSummary {
  leads: LeadStatistics;
  follow_ups: FollowUpStatistics;
  properties: PropertyStatistics;
  bookings: BookingStatistics;
}

// ── API call ──────────────────────────────────────────────────────────────────

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await apiClient.get<DashboardSummary>('/dashboard/summary');
  return data;
}
