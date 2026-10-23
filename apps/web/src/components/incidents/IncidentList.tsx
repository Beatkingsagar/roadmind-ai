import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  Filter,
  Plus,
  RefreshCw,
  Clock,
  MapPin,
  CheckCircle,
} from 'lucide-react';
import { api } from '../../api/client';
import type { IncidentEpisodeResponse } from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useRoute } from '../../context/RouteContext';
import { formatDateTime } from '../../utils/formatters';
import { OperatorReviewModal } from './OperatorReviewModal';

interface IncidentListProps {
  onOpenReportForm?: () => void;
  onNavigateToMap?: () => void;
}

export const IncidentList: React.FC<IncidentListProps> = ({
  onOpenReportForm,
  onNavigateToMap,
}) => {
  const { replayTime } = useReplay();
  const { setSelectedSegmentId } = useRoute();
  const [incidents, setIncidents] = useState<IncidentEpisodeResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedIncidentForReview, setSelectedIncidentForReview] = useState<IncidentEpisodeResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      const data = await api.getIncidents(
        replayTime || undefined,
        undefined,
        statusFilter === 'ALL' ? undefined : statusFilter
      );
      setIncidents(data);
    } catch (err) {
      console.error('Failed to fetch incidents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [replayTime, statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'VERIFIED':
        return <span className="badge badge-emerald">VERIFIED</span>;
      case 'INVESTIGATING':
        return <span className="badge badge-amber">INVESTIGATING</span>;
      case 'REPORTED':
        return <span className="badge badge-orange">REPORTED</span>;
      case 'RESOLVED':
        return <span className="badge badge-slate">RESOLVED</span>;
      case 'REJECTED':
        return <span className="badge badge-red">REJECTED</span>;
      default:
        return <span className="badge badge-slate">{status}</span>;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <span className="badge badge-red">CRITICAL</span>;
      case 'high':
        return <span className="badge badge-orange">HIGH</span>;
      case 'medium':
        return <span className="badge badge-amber">MEDIUM</span>;
      case 'low':
      default:
        return <span className="badge badge-slate">LOW</span>;
    }
  };

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header with Filters & Actions */}
      <div className="card" style={{ padding: '14px 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={20} color="var(--primary-500)" />
              <span>Incident Episodes & Operator Audit</span>
            </h2>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Algorithmic incident clustering, duplicate detection, and authoritative human-in-the-loop verification
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Status Filter */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Filter size={14} color="var(--text-muted)" />
              <select
                className="input-select"
                style={{ width: 'auto', padding: '6px 10px', fontSize: '12px' }}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="REPORTED">Reported</option>
                <option value="INVESTIGATING">Investigating</option>
                <option value="VERIFIED">Verified</option>
                <option value="RESOLVED">Resolved</option>
                <option value="REJECTED">Rejected</option>
              </select>
            </div>

            <button
              type="button"
              className="btn btn-secondary btn-icon"
              onClick={fetchIncidents}
              title="Refresh incident list"
            >
              <RefreshCw size={15} />
            </button>

            {onOpenReportForm && (
              <button
                type="button"
                className="btn btn-primary"
                onClick={onOpenReportForm}
                style={{ padding: '7px 12px', fontSize: '12px' }}
              >
                <Plus size={15} />
                <span>Report Incident</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Incident List Body */}
      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <div className="pulse-dot" style={{ width: '12px', height: '12px', margin: '0 auto 10px' }} />
          <p style={{ color: 'var(--text-muted)' }}>Querying incident episodes for current temporal window...</p>
        </div>
      ) : incidents.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <CheckCircle size={32} color="var(--status-emerald)" style={{ margin: '0 auto 12px' }} />
          <h3>No Active Incident Episodes</h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '420px', margin: '6px auto 16px' }}>
            No incident episodes match the selected criteria for this replay timestamp. Roads are currently operating in free-flow or steady state.
          </p>
          {onOpenReportForm && (
            <button type="button" className="btn btn-secondary" onClick={onOpenReportForm}>
              Report an Incident
            </button>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {incidents.map((episode) => (
            <div key={episode.id} className="card" style={{ borderLeft: '4px solid var(--status-red)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '10px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span className="badge badge-slate" style={{ fontFamily: 'monospace' }}>
                      {episode.id}
                    </span>
                    {getStatusBadge(episode.lifecycle_status)}
                    {getSeverityBadge(episode.severity_level)}
                  </div>

                  <h3 style={{ fontSize: '15px', fontWeight: 700, margin: '4px 0', textTransform: 'capitalize' }}>
                    {episode.episode_type} on {episode.primary_segment_id}
                  </h3>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={13} />
                      <span>Started: {formatDateTime(episode.first_reported_at)}</span>
                    </span>
                    <span>
                      Confidence: <strong>{Math.round(episode.heuristic_support_score * 100)}%</strong>
                    </span>
                    <span>
                      Reports: <strong>{episode.report_count}</strong>
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '12px', padding: '6px 10px' }}
                    onClick={() => {
                      setSelectedSegmentId(episode.primary_segment_id);
                      if (onNavigateToMap) onNavigateToMap();
                    }}
                  >
                    <MapPin size={13} />
                    <span>View on Map</span>
                  </button>

                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ fontSize: '12px', padding: '6px 12px' }}
                    onClick={() => setSelectedIncidentForReview(episode)}
                  >
                    <ShieldCheck size={14} />
                    <span>Review as Operator</span>
                  </button>
                </div>
              </div>

              {/* Confidence Progress Bar */}
              <div style={{ marginTop: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '3px' }}>
                  <span>Evidence Confidence Metric</span>
                  <span>{Math.round(episode.heuristic_support_score * 100)}%</span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'var(--bg-surface-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${Math.min(100, Math.round(episode.heuristic_support_score * 100))}%`,
                      height: '100%',
                      background: episode.heuristic_support_score >= 0.7 ? 'var(--status-emerald)' : 'var(--status-amber)',
                      borderRadius: '3px',
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Operator Review Modal */}
      {selectedIncidentForReview && (
        <OperatorReviewModal
          incident={selectedIncidentForReview}
          onClose={() => setSelectedIncidentForReview(null)}
          onReviewed={fetchIncidents}
        />
      )}
    </div>
  );
};
