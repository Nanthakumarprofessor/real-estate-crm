/**
 * Leads API module.
 *
 * Wraps all lead-related backend endpoints:
 *   POST   /api/leads
 *   GET    /api/leads
 *   GET    /api/leads/{id}
 *   PUT    /api/leads/{id}
 *   DELETE /api/leads/{id}
 *   POST   /api/leads/{id}/notes
 *   GET    /api/leads/{id}/notes
 *   DELETE /api/leads/{id}/notes/{note_id}
 *   POST   /api/leads/{id}/follow-ups
 *   GET    /api/leads/{id}/follow-ups
 *   PUT    /api/follow-ups/{id}
 *
 * Also exports GET /api/users (for assignee dropdown — Admin only).
 */
import apiClient from './axios';
import type { LeadSource, LeadStage, FollowUpStatus } from './types';

// ── Lead types ────────────────────────────────────────────────────────────────

export interface Lead {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  source: LeadSource | null;
  stage: LeadStage;
  assigned_to: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeadListResponse {
  items: Lead[];
  total: number;
  page: number;
  size: number;
}

export interface LeadCreateRequest {
  name: string;
  email?: string;
  phone?: string;
  source?: LeadSource;
  stage?: LeadStage;
  assigned_to?: number | null;
}

export interface LeadUpdateRequest {
  name?: string;
  email?: string | null;
  phone?: string | null;
  source?: LeadSource | null;
  stage?: LeadStage;
  assigned_to?: number | null;
}

// ── Note types ────────────────────────────────────────────────────────────────

export interface LeadNote {
  id: number;
  lead_id: number;
  user_id: number;
  note: string;
  created_at: string;
}

export interface LeadNoteListResponse {
  items: LeadNote[];
  total: number;
}

export interface NoteCreateRequest {
  note: string;
}

// ── Follow-up types ───────────────────────────────────────────────────────────

export interface FollowUp {
  id: number;
  lead_id: number;
  assigned_to: number;
  follow_up_at: string;
  notes: string | null;
  status: FollowUpStatus;
  created_at: string;
  updated_at: string;
}

export interface FollowUpListResponse {
  items: FollowUp[];
  total: number;
  page: number;
  size: number;
}

export interface FollowUpCreateRequest {
  follow_up_at: string;   // ISO-8601 datetime string
  notes?: string;
  status?: FollowUpStatus;
}

export interface FollowUpUpdateRequest {
  follow_up_at?: string;
  notes?: string;
  status?: FollowUpStatus;
}

// ── User type (for assignee dropdown) ────────────────────────────────────────

export interface UserOption {
  id: number;
  name: string;
  email: string;
  role: 'ADMIN' | 'SALES';
  is_active: boolean;
}

interface UserListResponse {
  items: UserOption[];
  total: number;
  page: number;
  size: number;
}

// ── Lead query params ─────────────────────────────────────────────────────────

export interface LeadListParams {
  page?: number;
  size?: number;
  search?: string;
  stage?: LeadStage | '';
  assigned_to?: number | null;
  is_active?: boolean;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listLeads(params: LeadListParams = {}): Promise<LeadListResponse> {
  const { data } = await apiClient.get<LeadListResponse>('/leads', {
    params: {
      page: params.page ?? 1,
      size: params.size ?? 10,
      ...(params.search    ? { search: params.search }          : {}),
      ...(params.stage     ? { stage: params.stage }            : {}),
      ...(params.assigned_to != null ? { assigned_to: params.assigned_to } : {}),
      ...(params.is_active != null   ? { is_active: params.is_active }     : {}),
    },
  });
  return data;
}

export async function getLead(id: number): Promise<Lead> {
  const { data } = await apiClient.get<Lead>(`/leads/${id}`);
  return data;
}

export async function createLead(payload: LeadCreateRequest): Promise<Lead> {
  const { data } = await apiClient.post<Lead>('/leads', payload);
  return data;
}

export async function updateLead(id: number, payload: LeadUpdateRequest): Promise<Lead> {
  const { data } = await apiClient.put<Lead>(`/leads/${id}`, payload);
  return data;
}

export async function deleteLead(id: number): Promise<Lead> {
  const { data } = await apiClient.delete<Lead>(`/leads/${id}`);
  return data;
}

// ── Notes ─────────────────────────────────────────────────────────────────────

export async function listNotes(leadId: number): Promise<LeadNoteListResponse> {
  const { data } = await apiClient.get<LeadNoteListResponse>(`/leads/${leadId}/notes`);
  return data;
}

export async function createNote(leadId: number, payload: NoteCreateRequest): Promise<LeadNote> {
  const { data } = await apiClient.post<LeadNote>(`/leads/${leadId}/notes`, payload);
  return data;
}

export async function deleteNote(leadId: number, noteId: number): Promise<void> {
  await apiClient.delete(`/leads/${leadId}/notes/${noteId}`);
}

// ── Follow-ups ────────────────────────────────────────────────────────────────

export async function listFollowUps(leadId: number): Promise<FollowUpListResponse> {
  const { data } = await apiClient.get<FollowUpListResponse>(`/leads/${leadId}/follow-ups`);
  return data;
}

export async function createFollowUp(
  leadId: number,
  payload: FollowUpCreateRequest,
): Promise<FollowUp> {
  const { data } = await apiClient.post<FollowUp>(`/leads/${leadId}/follow-ups`, payload);
  return data;
}

export async function updateFollowUp(
  followUpId: number,
  payload: FollowUpUpdateRequest,
): Promise<FollowUp> {
  const { data } = await apiClient.put<FollowUp>(`/follow-ups/${followUpId}`, payload);
  return data;
}

// ── Users (for assignee dropdown — Admin only) ────────────────────────────────

export async function listUsers(): Promise<UserOption[]> {
  const { data } = await apiClient.get<UserListResponse>('/users', {
    params: { is_active: true, size: 100 },
  });
  return data.items;
}
