/**
 * LeadNotes — notes list + add-note form inside Lead Details.
 *
 * Rules:
 *   - Notes are append-only (no edit endpoint).
 *   - Admin can delete any note.
 *   - Sales can delete only their own notes (user_id == currentUserId).
 *   - Backend is authoritative; 403 shown if deletion is rejected.
 */
import { type FormEvent, useCallback, useEffect, useState } from 'react';
import type { LeadNote } from '../../api/leadsApi';
import { createNote, deleteNote, listNotes } from '../../api/leadsApi';
import { parseApiError } from '../../hooks/useApiError';

interface LeadNotesProps {
  leadId: number;
  currentUserId: number;
  isAdmin: boolean;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

export default function LeadNotes({ leadId, currentUserId, isAdmin }: LeadNotesProps) {
  const [notes, setNotes]     = useState<LeadNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [text, setText]       = useState('');
  const [saving, setSaving]   = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError]     = useState('');

  const fetchNotes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listNotes(leadId);
      setNotes(res.items);
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setLoading(false);
    }
  }, [leadId]);

  useEffect(() => { fetchNotes(); }, [fetchNotes]);

  async function handleAddNote(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    try {
      await createNote(leadId, { note: text.trim() });
      setText('');
      await fetchNotes();
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(noteId: number) {
    setDeletingId(noteId);
    try {
      await deleteNote(leadId, noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch (err) {
      setError(parseApiError(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div>
      <h6 className="fw-semibold mb-3 d-flex align-items-center gap-2">
        <i className="bi bi-chat-left-text-fill text-primary" aria-hidden="true" />
        Notes
        <span className="badge bg-secondary rounded-pill ms-1">{notes.length}</span>
      </h6>

      {error && (
        <div className="alert alert-warning small py-2">{error}</div>
      )}

      {/* Note list */}
      {loading ? (
        <div className="py-3 text-center">
          <div className="spinner-border spinner-border-sm text-primary" role="status">
            <span className="visually-hidden">Loading notes…</span>
          </div>
        </div>
      ) : notes.length === 0 ? (
        <p className="text-muted small">No notes yet.</p>
      ) : (
        <div className="d-flex flex-column gap-2 mb-3">
          {notes.map((note) => {
            const canDelete = isAdmin || note.user_id === currentUserId;
            return (
              <div key={note.id} className="p-3 rounded-3 bg-light border position-relative">
                <p className="mb-1 small">{note.note}</p>
                <div className="d-flex justify-content-between align-items-center">
                  <span className="text-muted" style={{ fontSize: 11 }}>
                    {formatDate(note.created_at)}
                  </span>
                  {canDelete && (
                    <button
                      type="button"
                      className="btn btn-link btn-sm p-0 text-danger"
                      onClick={() => handleDelete(note.id)}
                      disabled={deletingId === note.id}
                      aria-label="Delete note"
                    >
                      {deletingId === note.id
                        ? <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                        : <i className="bi bi-trash3" aria-hidden="true" />}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add note form */}
      <form onSubmit={handleAddNote}>
        <div className="mb-2">
          <label htmlFor="note-input" className="form-label small fw-medium">Add a note</label>
          <textarea
            id="note-input"
            className="form-control form-control-sm"
            rows={2}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter note…"
            disabled={saving}
          />
        </div>
        <button
          type="submit"
          className="btn btn-sm btn-primary"
          disabled={saving || !text.trim()}
        >
          {saving
            ? <><span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" />Saving…</>
            : 'Add Note'}
        </button>
      </form>
    </div>
  );
}
