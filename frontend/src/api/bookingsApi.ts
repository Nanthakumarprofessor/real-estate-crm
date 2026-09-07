/**
 * Bookings API module.
 *
 * Wraps:
 *   POST  /api/bookings
 *   GET   /api/bookings
 *   GET   /api/bookings/{id}
 *   PATCH /api/bookings/{id}/cancel
 *
 * The backend response only contains IDs (lead_id, unit_id, booked_by).
 * Enriched display information is looked up separately by the UI.
 */
import apiClient from './axios';

export type BookingStatus = 'CONFIRMED' | 'CANCELLED';

export interface Booking {
  id: number;
  lead_id: number;
  unit_id: number;
  booked_by: number;
  booking_date: string;   // ISO datetime (server-generated)
  amount: number | null;
  status: BookingStatus;
  created_at: string;
  updated_at: string;
}

export interface BookingListResponse {
  items: Booking[];
  total: number;
  page: number;
  size: number;
}

export interface BookingCreateRequest {
  lead_id: number;
  unit_id: number;
  amount?: number;
}

export interface BookingListParams {
  page?: number;
  size?: number;
  status?: BookingStatus | '';
  lead_id?: number;
  unit_id?: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listBookings(params: BookingListParams = {}): Promise<BookingListResponse> {
  const { data } = await apiClient.get<BookingListResponse>('/bookings', {
    params: {
      page: params.page ?? 1,
      size: params.size ?? 10,
      ...(params.status  ? { status:  params.status  } : {}),
      ...(params.lead_id ? { lead_id: params.lead_id } : {}),
      ...(params.unit_id ? { unit_id: params.unit_id } : {}),
    },
  });
  return data;
}

export async function getBooking(id: number): Promise<Booking> {
  const { data } = await apiClient.get<Booking>(`/bookings/${id}`);
  return data;
}

export async function createBooking(payload: BookingCreateRequest): Promise<Booking> {
  const { data } = await apiClient.post<Booking>('/bookings', payload);
  return data;
}

export async function cancelBooking(id: number): Promise<Booking> {
  const { data } = await apiClient.patch<Booking>(`/bookings/${id}/cancel`);
  return data;
}
