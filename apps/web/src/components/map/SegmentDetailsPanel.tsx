import React, { useEffect, useState } from 'react';
import { X, Activity, AlertTriangle, Clock, Gauge } from 'lucide-react';
import { api } from '../../api/client';
import type { SegmentHistoryResponse } from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useRoute } from '../../context/RouteContext';
import { formatDateTime, formatDistance, formatSpeed, getCongestionColor, getCongestionLabel } from '../../utils/formatters';

interface SegmentDetailsPanelProps {
  segmentId: string;
  onClose: () => void;
}

export const SegmentDetailsPanel: React.FC<SegmentDetailsPanelProps> = ({ segmentId, onClose }) => {
  const { replayTime } = useReplay();
  const { setOriginNode, setDestinationNode } = useRoute();
  const [data, setData] = useState<SegmentHistoryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    api.getSegmentHistory(segmentId, replayTime || undefined)
      .then((res) => {
        if (mounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to fetch segment history');
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [segmentId, replayTime]);

  if (loading) {
    return (
      <div
        style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          zIndex: 1000,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px',
          boxShadow: 'var(--shadow-lg)',
          width: '360px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Activity className="animate-spin" size={18} />
          <span>Loading segment telemetry...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          zIndex: 1000,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-lg)',
          padding: '20px',
          boxShadow: 'var(--shadow-lg)',
          width: '360px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h4 style={{ color: 'var(--status-red)' }}>Error Loading Telemetry</h4>
          <button type="button" className="btn btn-ghost btn-icon" onClick={onClose}><X size={16} /></button>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{error || 'No telemetry available'}</p>
      </div>
    );
  }

  const { segment, recent_observations, memory_summary } = data;
  const latestObs = recent_observations && recent_observations.length > 0 ? recent_observations[0] : null;
  const currentSpeed = latestObs ? latestObs.speed_mps : segment.free_flow_speed_mps;
  const speedRatio = segment.free_flow_speed_mps > 0 ? Math.min(1.0, currentSpeed / segment.free_flow_speed_mps) : 1.0;
  const congestionColor = getCongestionColor(speedRatio);
  const activeEpisodes = memory_summary?.episodes || [];

  return (
    <div
      style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        bottom: '24px',
        zIndex: 1000,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-medium)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px',
        boxShadow: 'var(--shadow-lg)',
        width: '380px',
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
        <div>
          <span className="badge badge-slate" style={{ marginBottom: '4px' }}>{segment.id}</span>
          <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '2px 0' }}>{segment.name}</h3>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Class: <strong style={{ textTransform: 'capitalize' }}>{segment.functional_class}</strong> &bull; {segment.is_one_way ? 'One-Way' : 'Two-Way'} &bull; {formatDistance(segment.length_meters)}
          </div>
        </div>
        <button type="button" className="btn btn-ghost btn-icon" onClick={onClose} title="Close panel">
          <X size={18} />
        </button>
      </div>

      {/* Speed & Congestion Gauge */}
      <div
        style={{
          background: 'var(--bg-surface-subtle)',
          border: `1px solid ${congestionColor}40`,
          borderLeft: `4px solid ${congestionColor}`,
          borderRadius: 'var(--radius-md)',
          padding: '12px',
          marginBottom: '16px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Gauge size={12} />
              <span>Current Observed Speed</span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: congestionColor }}>
              {latestObs ? formatSpeed(latestObs.speed_mps) : formatSpeed(segment.free_flow_speed_mps)}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Free-Flow Limit</div>
            <div style={{ fontSize: '14px', fontWeight: 600 }}>{formatSpeed(segment.free_flow_speed_mps)}</div>
            <span className="badge" style={{ background: `${congestionColor}20`, color: congestionColor, marginTop: '4px' }}>
              {getCongestionLabel(speedRatio)} ({Math.round(speedRatio * 100)}%)
            </span>
          </div>
        </div>
      </div>

      {/* Connected Nodes & Quick Route Setting */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-secondary)' }}>
          Junction Connectivity
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ flex: 1, fontSize: '11px', padding: '6px' }}
            onClick={() => setOriginNode(segment.source_node)}
          >
            Set Origin: {segment.source_node.replace('node_', '')}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ flex: 1, fontSize: '11px', padding: '6px' }}
            onClick={() => setDestinationNode(segment.target_node)}
          >
            Set Dest: {segment.target_node.replace('node_', '')}
          </button>
        </div>
      </div>

      {/* Active Incidents on this segment */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <AlertTriangle size={13} color="var(--status-red)" />
          <span>Incident Clusters ({activeEpisodes.length})</span>
        </div>
        {activeEpisodes.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {activeEpisodes.map((ep) => (
              <div
                key={ep.id}
                style={{
                  background: 'var(--status-red-bg)',
                  border: '1px solid var(--status-red-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '8px 10px',
                  fontSize: '11px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600 }}>
                  <span style={{ textTransform: 'capitalize' }}>{ep.episode_type}</span>
                  <span className="badge badge-red">{ep.severity_level}</span>
                </div>
                <div style={{ marginTop: '4px', color: 'var(--text-secondary)' }}>
                  Duration: <strong>{ep.duration_minutes}m</strong> &bull; Aggregated Reports: <strong>{ep.report_count}</strong>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Started: {formatDateTime(ep.first_reported_at)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            No incident clusters recorded on this segment.
          </div>
        )}
      </div>

      {/* Recent Observations */}
      <div>
        <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '6px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Clock size={13} />
          <span>Recent Sensor Telemetry ({recent_observations?.length || 0})</span>
        </div>
        {recent_observations && recent_observations.length > 0 ? (
          <div className="table-container" style={{ maxHeight: '180px', overflowY: 'auto' }}>
            <table className="data-table" style={{ fontSize: '11px' }}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Observed Speed</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {recent_observations.slice(0, 8).map((obs) => (
                  <tr key={obs.id}>
                    <td>{formatDateTime(obs.observed_at)}</td>
                    <td style={{ fontWeight: 600 }}>{formatSpeed(obs.speed_mps)}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{Math.round(obs.quality_score * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            No recent sensor observations found for this replay window.
          </div>
        )}
      </div>
    </div>
  );
};
