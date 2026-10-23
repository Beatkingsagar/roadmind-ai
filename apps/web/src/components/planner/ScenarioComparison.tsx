import React from 'react';
import {
  CheckCircle,
  AlertTriangle,
  Clock,
  Zap,
  ShieldAlert,
} from 'lucide-react';
import type { SimulationRunResponse, RouteAlternative } from '../../api/types';
import {
  formatDuration,
  formatDistance,
  getOutcomeBadgeProps,
} from '../../utils/formatters';

interface ScenarioComparisonProps {
  simulation: SimulationRunResponse;
}

export const ScenarioComparison: React.FC<ScenarioComparisonProps> = ({ simulation }) => {
  const { scenarios, recommendation, sensitivity_summary } = simulation;

  if (!scenarios || Object.keys(scenarios).length === 0) {
    return (
      <div className="card" style={{ marginTop: '20px' }}>
        <p style={{ color: 'var(--text-muted)' }}>
          Simulation completed, but scenario metrics are unavailable.
        </p>
      </div>
    );
  }

  const baselineEval = scenarios['baseline'];
  const slowdownEval = scenarios['slowdown'] || scenarios['partial_slowdown'];
  const closureEval = scenarios['closure'] || scenarios['full_closure'];

  const outcomeBadge = getOutcomeBadgeProps(recommendation?.sensitivity_outcome);

  const getPrimaryRoute = (scenEval: typeof baselineEval): RouteAlternative | undefined => {
    if (!scenEval) return undefined;
    if (scenEval.preferred_route_name && scenEval.candidate_routes) {
      const match = scenEval.candidate_routes.find((r) => r.route_name === scenEval.preferred_route_name);
      if (match) return match;
    }
    return scenEval.candidate_routes?.[0] || scenEval.reference_route || undefined;
  };

  const baselineRoute = getPrimaryRoute(baselineEval);
  const slowdownRoute = getPrimaryRoute(slowdownEval);
  const closureRoute = getPrimaryRoute(closureEval);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>
      {/* Recommendation Banner */}
      {recommendation && (
        <div
          className="card"
          style={{
            background:
              outcomeBadge.variant === 'emerald'
                ? 'var(--status-emerald-bg)'
                : outcomeBadge.variant === 'amber'
                ? 'var(--status-amber-bg)'
                : 'var(--bg-surface-subtle)',
            border:
              outcomeBadge.variant === 'emerald'
                ? '1px solid var(--status-emerald-border)'
                : outcomeBadge.variant === 'amber'
                ? '1px solid var(--status-amber-border)'
                : '1px solid var(--border-medium)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: 'var(--radius-md)',
                background:
                  outcomeBadge.variant === 'emerald'
                    ? 'var(--status-emerald)'
                    : outcomeBadge.variant === 'amber'
                    ? 'var(--status-amber)'
                    : 'var(--text-muted)',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {outcomeBadge.variant === 'emerald' ? <CheckCircle size={22} /> : <AlertTriangle size={22} />}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '4px' }}>
                <span className={`badge badge-${outcomeBadge.variant}`} style={{ fontSize: '12px' }}>
                  {outcomeBadge.label}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {outcomeBadge.description}
                </span>
              </div>

              <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginTop: '6px' }}>
                {recommendation.explanation}
              </p>

              {sensitivity_summary && (
                <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                  <strong>Sensitivity Analysis:</strong> {sensitivity_summary}
                </div>
              )}

              {/* Preferred Route Pills */}
              {closureRoute && closureRoute.edge_ids && closureRoute.edge_ids.length > 0 && (
                <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    Recommended Edges:
                  </span>
                  {closureRoute.edge_ids.map((segId, idx) => (
                    <React.Fragment key={segId}>
                      <span className="badge badge-emerald" style={{ fontSize: '11px' }}>
                        {segId}
                      </span>
                      {idx < closureRoute.edge_ids.length - 1 && (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>➔</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 3-Card Scenario Comparison Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
        {/* Scenario 1: Baseline */}
        <div className="card" style={{ borderTop: '4px solid #38bdf8' }}>
          <div className="card-header">
            <div>
              <div className="card-title" style={{ fontSize: '14px' }}>
                <Clock size={16} color="#38bdf8" />
                <span>1. Baseline Scenario</span>
              </div>
              <div className="card-subtitle">Normal conditions without incidents</div>
            </div>
            <span className={`badge ${baselineRoute?.is_reachable ? 'badge-emerald' : 'badge-red'}`}>
              {baselineRoute?.is_reachable ? 'Available' : 'Unreachable'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Estimated Travel Time</div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
                {formatDuration(baselineRoute?.estimated_travel_time_seconds)}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '4px', fontSize: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Distance:</span>{' '}
                <strong>{formatDistance(baselineRoute?.total_length_meters)}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Route Name:</span>{' '}
                <strong>{baselineRoute?.route_name || 'Direct Corridor'}</strong>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Path Segments</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {baselineRoute?.edge_ids?.map((s) => (
                  <span key={s} className="badge badge-slate" style={{ fontSize: '10px' }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Scenario 2: Partial Slowdown */}
        <div className="card" style={{ borderTop: '4px solid #f59e0b' }}>
          <div className="card-header">
            <div>
              <div className="card-title" style={{ fontSize: '14px' }}>
                <Zap size={16} color="#f59e0b" />
                <span>2. Partial Slowdown</span>
              </div>
              <div className="card-subtitle">50% speed degradation on incident link</div>
            </div>
            <span className={`badge ${slowdownRoute?.is_reachable ? 'badge-emerald' : 'badge-red'}`}>
              {slowdownRoute?.is_reachable ? 'Available' : 'Unreachable'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Estimated Travel Time</div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
                {formatDuration(slowdownRoute?.estimated_travel_time_seconds)}
              </div>
              {baselineRoute && slowdownRoute && (
                <div style={{ fontSize: '11px', color: 'var(--status-amber)' }}>
                  +{formatDuration(slowdownRoute.estimated_travel_time_seconds - baselineRoute.estimated_travel_time_seconds)} vs baseline
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '4px', fontSize: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Distance:</span>{' '}
                <strong>{formatDistance(slowdownRoute?.total_length_meters)}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Preferred:</span>{' '}
                <strong>{slowdownEval?.preferred_route_name || slowdownRoute?.route_name}</strong>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Path Segments</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {slowdownRoute?.edge_ids?.map((s) => (
                  <span key={s} className="badge badge-slate" style={{ fontSize: '10px' }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Scenario 3: Full Closure */}
        <div className="card" style={{ borderTop: '4px solid #ef4444' }}>
          <div className="card-header">
            <div>
              <div className="card-title" style={{ fontSize: '14px' }}>
                <ShieldAlert size={16} color="#ef4444" />
                <span>3. Full Link Closure</span>
              </div>
              <div className="card-subtitle">Incident link fully closed / blocked</div>
            </div>
            <span className={`badge ${closureRoute?.is_reachable ? 'badge-emerald' : 'badge-red'}`}>
              {closureRoute?.is_reachable ? 'Alternative Found' : 'Unreachable'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Estimated Travel Time</div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
                {formatDuration(closureRoute?.estimated_travel_time_seconds)}
              </div>
              {closureEval && closureEval.time_saved_seconds > 0 && (
                <div style={{ fontSize: '11px', color: 'var(--status-emerald)' }}>
                  Saves {formatDuration(closureEval.time_saved_seconds)} over impaired route
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '4px', fontSize: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Distance:</span>{' '}
                <strong>{formatDistance(closureRoute?.total_length_meters)}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Route:</span>{' '}
                <strong>{closureRoute?.route_name || 'South Bypass Route'}</strong>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Path Segments</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {closureRoute?.edge_ids?.map((s) => (
                  <span key={s} className="badge badge-slate" style={{ fontSize: '10px' }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
