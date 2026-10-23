import React, { useEffect, useState } from 'react';
import {
  BrainCircuit,
  RefreshCw,
  Search,
  MapPin,
} from 'lucide-react';
import { api } from '../../api/client';
import type { InspectionPriority } from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useRoute } from '../../context/RouteContext';

interface MemoryPriorityViewProps {
  onNavigateToMap?: () => void;
}

export const MemoryPriorityView: React.FC<MemoryPriorityViewProps> = ({ onNavigateToMap }) => {
  const { replayTime } = useReplay();
  const { setSelectedSegmentId } = useRoute();
  const [priorities, setPriorities] = useState<InspectionPriority[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const fetchPriorities = async () => {
    setLoading(true);
    try {
      const data = await api.getInspectionPriorities(replayTime || undefined);
      setPriorities(data);
    } catch (err) {
      console.error('Failed to load inspection priorities:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPriorities();
  }, [replayTime]);

  const filtered = priorities.filter(
    (p) =>
      p.segment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.segment_name && p.segment_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'var(--status-red)';
    if (score >= 40) return 'var(--status-amber)';
    return 'var(--status-emerald)';
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header and Rubric Explanation */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <BrainCircuit size={20} color="var(--primary-500)" />
              <span>Road Memory & Infrastructure Inspection Priority</span>
            </div>
            <div className="card-subtitle">
              Long-term chronic road health tracking based on a deterministic 100-point inspection rubric
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-icon"
            onClick={fetchPriorities}
            title="Refresh priority rankings"
          >
            <RefreshCw size={15} />
          </button>
        </div>

        {/* 4-Pillar Rubric Breakdown Pills */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', marginTop: '6px' }}>
          <div style={{ background: 'var(--bg-surface-subtle)', padding: '10px 12px', borderRadius: 'var(--radius-md)', fontSize: '12px' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>1. Recurrence (0–35 pts)</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '2px' }}>Historical incident clustering & frequency</div>
          </div>
          <div style={{ background: 'var(--bg-surface-subtle)', padding: '10px 12px', borderRadius: 'var(--radius-md)', fontSize: '12px' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>2. Severity (0–30 pts)</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '2px' }}>Maximum incident impairment level</div>
          </div>
          <div style={{ background: 'var(--bg-surface-subtle)', padding: '10px 12px', borderRadius: 'var(--radius-md)', fontSize: '12px' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>3. Duration (0–20 pts)</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '2px' }}>Persistence & clearance latency of disruptions</div>
          </div>
          <div style={{ background: 'var(--bg-surface-subtle)', padding: '10px 12px', borderRadius: 'var(--radius-md)', fontSize: '12px' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>4. Coverage Uncertainty (0–15 pts)</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '2px' }}>Sensor blindspots & observation gaps</div>
          </div>
        </div>
      </div>

      {/* Search Input */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            className="input-text"
            style={{ paddingLeft: '36px' }}
            placeholder="Search segments by name or ID (e.g. Corridor, Spur, Bypass)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Priority Rankings Table */}
      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
          <div className="pulse-dot" style={{ width: '12px', height: '12px', margin: '0 auto 10px' }} />
          <p style={{ color: 'var(--text-muted)' }}>Calculating road memory priority scores...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <p style={{ color: 'var(--text-muted)' }}>No segments match your search.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '50px' }}>Rank</th>
                <th>Road Segment</th>
                <th style={{ width: '160px' }}>Priority Score (0–100)</th>
                <th>Rubric Breakdown</th>
                <th>Explanation</th>
                <th style={{ width: '80px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const scoreColor = getScoreColor(item.priority_score);
                return (
                  <tr key={item.segment_id}>
                    <td style={{ fontWeight: 700, color: 'var(--text-muted)' }}>#{item.priority_rank}</td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{item.segment_name || item.segment_id}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        <code>{item.segment_id}</code>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, fontSize: '15px', color: scoreColor, minWidth: '28px' }}>
                          {item.priority_score}
                        </span>
                        <div style={{ flex: 1, height: '6px', background: 'var(--bg-surface-subtle)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${Math.min(100, item.priority_score)}%`,
                              height: '100%',
                              background: scoreColor,
                              borderRadius: '3px',
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', fontSize: '10px' }}>
                        <span className="badge badge-slate" title="Observed Recurrence Score">
                          Recurr: {item.observed_recurrence_score}/35
                        </span>
                        <span className="badge badge-slate" title="Severity Score">
                          Sever: {item.severity_score}/30
                        </span>
                        <span className="badge badge-slate" title="Duration Score">
                          Dur: {item.duration_score}/20
                        </span>
                        <span className="badge badge-slate" title="Coverage Uncertainty Score">
                          Gap: {item.coverage_uncertainty_score}/15
                        </span>
                      </div>
                    </td>
                    <td style={{ fontSize: '11px', color: 'var(--text-secondary)', maxWidth: '280px' }}>
                      {item.explanation}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '11px' }}
                        onClick={() => {
                          setSelectedSegmentId(item.segment_id);
                          if (onNavigateToMap) onNavigateToMap();
                        }}
                        title="Inspect on map"
                      >
                        <MapPin size={12} />
                        <span>Map</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
