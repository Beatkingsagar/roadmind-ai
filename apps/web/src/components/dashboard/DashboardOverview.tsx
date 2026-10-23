import React, { useEffect, useState } from 'react';
import {
  Navigation,
  AlertTriangle,
  BrainCircuit,
  Map as MapIcon,
  Activity,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { api } from '../../api/client';
import type { IncidentEpisodeResponse, InspectionPriority, RoadStateSnapshot } from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useRoute } from '../../context/RouteContext';
import { formatTimeOnly } from '../../utils/formatters';
import type { ActiveTab } from '../layout/Sidebar';

interface DashboardOverviewProps {
  onNavigate: (tab: ActiveTab) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({ onNavigate }) => {
  const { replayTime, applyPreset, isReplay } = useReplay();
  const { setOriginNode, setDestinationNode } = useRoute();

  const [roadStates, setRoadStates] = useState<RoadStateSnapshot[]>([]);
  const [incidents, setIncidents] = useState<IncidentEpisodeResponse[]>([]);
  const [priorities, setPriorities] = useState<InspectionPriority[]>([]);

  useEffect(() => {
    let mounted = true;

    Promise.all([
      api.getRoadState(replayTime || undefined),
      api.getIncidents(replayTime || undefined),
      api.getInspectionPriorities(replayTime || undefined),
    ])
      .then(([states, incs, pris]) => {
        if (!mounted) return;
        setRoadStates(states);
        setIncidents(incs);
        setPriorities(pris);
      })
      .catch((err) => {
        console.error('Failed to load dashboard metrics:', err);
      });

    return () => {
      mounted = false;
    };
  }, [replayTime]);

  // Compute average network congestion ratio
  const avgSpeedRatio = roadStates.length > 0
    ? roadStates.reduce((acc, curr) => acc + (curr.congestion_ratio ?? 1.0), 0) / roadStates.length
    : 1.0;

  const topPriority = priorities.length > 0 ? priorities[0] : null;

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Banner Card */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, var(--navy-900) 0%, var(--navy-800) 100%)',
          color: '#ffffff',
          border: '1px solid var(--primary-700)',
          padding: '24px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '1px',
                textTransform: 'uppercase',
                color: 'var(--accent-cyan)',
              }}
            >
              NEXATHON 2026 &bull; Traffic Intelligence Track
            </span>
            <h2 style={{ fontSize: '24px', fontWeight: 700, color: '#ffffff', margin: '6px 0 8px' }}>
              Sector 7 Traffic Decision Support System
            </h2>
            <p style={{ fontSize: '13px', color: '#94a3b8', maxWidth: '580px', lineHeight: 1.5 }}>
              Evidence-aware routing engine comparing real-time incident reports, short-horizon speed forecasts, and counterfactual scenario simulations across the Grand Corridor & South Bypass network.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                applyPreset(0); // Peak incident preset
                setOriginNode('node_origin');
                setDestinationNode('node_destination');
                onNavigate('planner');
              }}
              style={{ background: 'var(--primary-500)', border: 'none', fontWeight: 600 }}
            >
              <Zap size={16} />
              <span>Launch Peak Incident Demo</span>
            </button>
            <div style={{ fontSize: '11px', color: '#94a3b8', textAlign: 'center' }}>
              Loads Grand Corridor East accident & compares bypass
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        {/* Active Incidents */}
        <div className="card" style={{ borderLeft: '4px solid var(--status-red)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Active Incidents</div>
            <AlertTriangle size={18} color="var(--status-red)" />
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, margin: '6px 0 2px' }}>
            {incidents.length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
            <span>{incidents.filter((i) => i.lifecycle_status === 'VERIFIED').length} Verified</span>
            <button
              type="button"
              style={{ background: 'none', border: 'none', color: 'var(--primary-500)', cursor: 'pointer', fontSize: '11px' }}
              onClick={() => onNavigate('incidents')}
            >
              View list &rarr;
            </button>
          </div>
        </div>

        {/* Network Speed Ratio */}
        <div className="card" style={{ borderLeft: '4px solid var(--primary-500)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Network Speed Ratio</div>
            <Activity size={18} color="var(--primary-500)" />
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, margin: '6px 0 2px' }}>
            {Math.round(avgSpeedRatio * 100)}%
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
            <span>{roadStates.length} Monitored Segments</span>
            <button
              type="button"
              style={{ background: 'none', border: 'none', color: 'var(--primary-500)', cursor: 'pointer', fontSize: '11px' }}
              onClick={() => onNavigate('map')}
            >
              Live map &rarr;
            </button>
          </div>
        </div>

        {/* Highest Priority Segment */}
        <div className="card" style={{ borderLeft: '4px solid var(--status-amber)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Highest Inspection Priority</div>
            <BrainCircuit size={18} color="var(--status-amber)" />
          </div>
          <div style={{ fontSize: '28px', fontWeight: 700, margin: '6px 0 2px' }}>
            {topPriority ? `${topPriority.priority_score}/100` : '—'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
            <span>{topPriority?.segment_name || topPriority?.segment_id || 'All nominal'}</span>
            <button
              type="button"
              style={{ background: 'none', border: 'none', color: 'var(--primary-500)', cursor: 'pointer', fontSize: '11px' }}
              onClick={() => onNavigate('memory')}
            >
              Priority table &rarr;
            </button>
          </div>
        </div>

        {/* Replay State */}
        <div className="card" style={{ borderLeft: '4px solid var(--accent-cyan)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Temporal Simulation Mode</div>
            <Zap size={18} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, margin: '10px 0 4px' }}>
            {isReplay ? 'Historical Replay' : 'Real-Time Live'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {replayTime ? `As of ${formatTimeOnly(replayTime)}` : 'Streaming current wall-clock'}
          </div>
        </div>
      </div>

      {/* Quick Launch Cards Grid */}
      <div>
        <h3 style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px', color: 'var(--text-primary)' }}>
          Operational Workspaces
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div
            className="card"
            style={{ cursor: 'pointer', transition: 'transform 0.15s ease, box-shadow 0.15s ease' }}
            onClick={() => onNavigate('planner')}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ padding: '10px', background: 'var(--primary-50)', color: 'var(--primary-600)', borderRadius: 'var(--radius-md)' }}>
                <Navigation size={22} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '14px' }}>Route Planner & Scenario Simulation</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Evaluate Baseline vs Partial Slowdown vs Full Closure routes with automatic Robust Alternative detection.
                </div>
              </div>
              <ArrowRight size={16} color="var(--text-muted)" />
            </div>
          </div>

          <div
            className="card"
            style={{ cursor: 'pointer', transition: 'transform 0.15s ease, box-shadow 0.15s ease' }}
            onClick={() => onNavigate('map')}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ padding: '10px', background: 'var(--status-emerald-bg)', color: 'var(--status-emerald)', borderRadius: 'var(--radius-md)' }}>
                <MapIcon size={22} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '14px' }}>Live Network & Congestion Map</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Interactive Leaflet map showing real-time road conditions, incident pins, and telemetry inspector.
                </div>
              </div>
              <ArrowRight size={16} color="var(--text-muted)" />
            </div>
          </div>

          <div
            className="card"
            style={{ cursor: 'pointer', transition: 'transform 0.15s ease, box-shadow 0.15s ease' }}
            onClick={() => onNavigate('report')}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ padding: '10px', background: 'var(--status-amber-bg)', color: 'var(--status-amber)', borderRadius: 'var(--radius-md)' }}>
                <AlertTriangle size={22} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '14px' }}>Report Incident with Evidence</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Ingest citizen incident reports and upload photo evidence to update confidence scores in real time.
                </div>
              </div>
              <ArrowRight size={16} color="var(--text-muted)" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
