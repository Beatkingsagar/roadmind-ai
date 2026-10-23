import React, { useState } from 'react';
import { X, ShieldCheck, Check, Ban, HelpCircle, AlertCircle } from 'lucide-react';
import { api, ApiError } from '../../api/client';
import type { IncidentEpisodeResponse } from '../../api/types';

interface OperatorReviewModalProps {
  incident: IncidentEpisodeResponse;
  onClose: () => void;
  onReviewed: () => void;
}

export const OperatorReviewModal: React.FC<OperatorReviewModalProps> = ({
  incident,
  onClose,
  onReviewed,
}) => {
  const [decision, setDecision] = useState<'VERIFIED' | 'REJECTED' | 'INCONCLUSIVE'>('VERIFIED');
  const [actionTaken, setActionTaken] = useState<string>('DISPATCH_PATROL');
  const [notes, setNotes] = useState<string>('Visual verification confirmed collision blocking two lanes. Dispatching response unit and updating routing engine.');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);

    try {
      const decisionLower = decision === 'VERIFIED' ? 'verified' : decision === 'REJECTED' ? 'rejected' : 'needs_investigation';
      await api.submitReview(incident.id, {
        reviewer_reference: 'operator_console',
        decision: decisionLower,
        reason: `${actionTaken}: ${notes.trim()}`,
      });
      onReviewed();
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401 || err.status === 403) {
          setErrorMessage('Access Denied: Operator token is missing or invalid. Configure authorized credentials in Settings.');
        } else {
          setErrorMessage(err.message);
        }
      } else {
        setErrorMessage('Failed to submit review. Backend may be offline.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={20} color="var(--primary-500)" />
            <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>
              Operator Review & Verification
            </h3>
          </div>
          <button type="button" className="btn btn-ghost btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {/* Episode Context Card */}
            <div
              style={{
                background: 'var(--bg-surface-subtle)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                padding: '12px',
                fontSize: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span>Episode: <strong>{incident.id}</strong></span>
                <span className="badge badge-amber">{incident.lifecycle_status}</span>
              </div>
              <div>Segment: <strong>{incident.primary_segment_id}</strong> &bull; Type: <strong style={{ textTransform: 'capitalize' }}>{incident.episode_type}</strong></div>
              <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
                Algorithmic Confidence: <strong>{Math.round(incident.heuristic_support_score * 100)}%</strong> &bull; Severity: <strong>{incident.severity_level}</strong>
              </div>
            </div>

            {errorMessage && (
              <div className="alert alert-danger" style={{ margin: 0 }}>
                <AlertCircle size={16} />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Decision Radio/Buttons */}
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label">Operator Verification Decision *</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
                <button
                  type="button"
                  className={`btn ${decision === 'VERIFIED' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ fontSize: '12px', padding: '8px' }}
                  onClick={() => setDecision('VERIFIED')}
                >
                  <Check size={14} />
                  <span>Verify Incident</span>
                </button>
                <button
                  type="button"
                  className={`btn ${decision === 'REJECTED' ? 'btn-danger' : 'btn-secondary'}`}
                  style={{ fontSize: '12px', padding: '8px' }}
                  onClick={() => setDecision('REJECTED')}
                >
                  <Ban size={14} />
                  <span>Reject (False)</span>
                </button>
                <button
                  type="button"
                  className={`btn ${decision === 'INCONCLUSIVE' ? 'btn-secondary active' : 'btn-secondary'}`}
                  style={{ fontSize: '12px', padding: '8px' }}
                  onClick={() => setDecision('INCONCLUSIVE')}
                >
                  <HelpCircle size={14} />
                  <span>Inconclusive</span>
                </button>
              </div>
            </div>

            {/* Action Taken */}
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label" htmlFor="action-select">Dispatch / Operational Action</label>
              <select
                id="action-select"
                className="input-select"
                value={actionTaken}
                onChange={(e) => setActionTaken(e.target.value)}
              >
                <option value="DISPATCH_PATROL">Dispatch Highway Patrol / Responders</option>
                <option value="VARIABLE_MESSAGE_SIGN">Update Variable Message Signs (VMS)</option>
                <option value="ROUTE_DIVERSION">Trigger Traffic Diversion to South Bypass</option>
                <option value="MONITOR_CAMERA">Request CCTV Visual Confirmation</option>
                <option value="CLOSE_EPISODE">Close & Resolve Incident</option>
              </select>
            </div>

            {/* Operator Notes */}
            <div className="input-group" style={{ margin: 0 }}>
              <label className="input-label" htmlFor="notes-input">Verification & Audit Log Notes *</label>
              <textarea
                id="notes-input"
                className="input-textarea"
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Enter justification for the audit trail..."
                required
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Submitting Review...' : 'Confirm Operator Decision'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
