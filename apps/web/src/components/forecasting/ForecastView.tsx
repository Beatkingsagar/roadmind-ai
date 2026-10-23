import React, { useEffect, useState } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  ComposedChart,
  Line,
} from 'recharts';
import {
  TrendingUp,
  AlertTriangle,
  Gauge,
  Activity,
} from 'lucide-react';
import { api } from '../../api/client';
import type { PredictionResponse, RoadSegmentResponse, SegmentHistoryResponse } from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useTheme } from '../../context/ThemeContext';
import { formatDateTime, formatSpeed, formatTimeOnly } from '../../utils/formatters';

export const ForecastView: React.FC = () => {
  const { replayTime } = useReplay();
  const { theme } = useTheme();

  const [segments, setSegments] = useState<RoadSegmentResponse[]>([]);
  const [selectedSegmentId, setSelectedSegmentId] = useState<string>('seg_corridor_e');
  const [modelType, setModelType] = useState<'persistence' | 'historical_median'>('persistence');
  const [horizonMinutes, setHorizonMinutes] = useState<number>(15);

  const [forecast, setForecast] = useState<PredictionResponse | null>(null);
  const [history, setHistory] = useState<SegmentHistoryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load segments once
  useEffect(() => {
    let mounted = true;
    api.getSegments()
      .then((segs) => {
        if (mounted) setSegments(segs);
      })
      .catch((err) => console.error('Failed to load segments:', err));
    return () => {
      mounted = false;
    };
  }, []);

  // Fetch forecast and segment history
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.getForecast(selectedSegmentId, replayTime || undefined, horizonMinutes, modelType),
      api.getSegmentHistory(selectedSegmentId, replayTime || undefined),
    ])
      .then(([fc, hist]) => {
        if (!mounted) return;
        setForecast(fc);
        setHistory(hist);
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || 'Failed to generate forecast.');
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [selectedSegmentId, replayTime, horizonMinutes, modelType]);

  // Prepare chart data combining recent observations + predicted point
  const chartData: Array<{
    timeLabel: string;
    actualSpeed?: number;
    predictedSpeed?: number;
    upperBound?: number;
    lowerBound?: number;
    isForecast?: boolean;
  }> = [];

  if (history?.recent_observations) {
    const sorted = [...history.recent_observations].reverse();
    for (const obs of sorted) {
      chartData.push({
        timeLabel: formatTimeOnly(obs.observed_at),
        actualSpeed: Math.round(obs.speed_mps * 3.6 * 10) / 10, // km/h
      });
    }
  }

  // Add the forecast point if available and not abstained
  if (forecast && !forecast.is_abstained && forecast.predicted_speed_mps !== null) {
    const predictedKmph = Math.round(forecast.predicted_speed_mps * 3.6 * 10) / 10;
    const lowerKmph = forecast.interval_lower_mps !== null && forecast.interval_lower_mps !== undefined
      ? Math.round(forecast.interval_lower_mps * 3.6 * 10) / 10
      : undefined;
    const upperKmph = forecast.interval_upper_mps !== null && forecast.interval_upper_mps !== undefined
      ? Math.round(forecast.interval_upper_mps * 3.6 * 10) / 10
      : undefined;

    chartData.push({
      timeLabel: `+${horizonMinutes}m Target`,
      predictedSpeed: predictedKmph,
      lowerBound: lowerKmph,
      upperBound: upperKmph,
      isForecast: true,
    });
  }

  const isDark = theme === 'dark';
  const gridColor = isDark ? '#1e293b' : '#e2e8f0';
  const textColor = isDark ? '#94a3b8' : '#64748b';

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Controls Card */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <TrendingUp size={20} color="var(--primary-500)" />
              <span>Traffic Speed Forecasting & Prediction Uncertainty</span>
            </div>
            <div className="card-subtitle">
              Short-horizon road speed estimates with empirical uncertainty bounds and abstention guardrails
            </div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          {/* Segment Selector */}
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="fc-segment">Target Road Segment</label>
            <select
              id="fc-segment"
              className="input-select"
              value={selectedSegmentId}
              onChange={(e) => setSelectedSegmentId(e.target.value)}
            >
              {segments.map((seg) => (
                <option key={seg.id} value={seg.id}>
                  {seg.name} ({seg.id})
                </option>
              ))}
            </select>
          </div>

          {/* Model Type */}
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="fc-model">Forecasting Model</label>
            <select
              id="fc-model"
              className="input-select"
              value={modelType}
              onChange={(e) => setModelType(e.target.value as 'persistence' | 'historical_median')}
            >
              <option value="persistence">Lagged Persistence Model</option>
              <option value="historical_median">Historical Median (Hour-of-Day Profile)</option>
            </select>
          </div>

          {/* Horizon Selector */}
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="fc-horizon">Forecast Horizon</label>
            <select
              id="fc-horizon"
              className="input-select"
              value={horizonMinutes}
              onChange={(e) => setHorizonMinutes(Number(e.target.value))}
            >
              <option value={15}>+15 Minutes Horizon</option>
              <option value={30}>+30 Minutes Horizon</option>
              <option value={60}>+60 Minutes Horizon</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
          <Activity className="animate-spin" size={24} style={{ margin: '0 auto 10px' }} />
          <p style={{ color: 'var(--text-muted)' }}>Calculating speed forecast and bounds...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger">
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      ) : (
        <>
          {/* Abstention Explanation Notice if model abstained */}
          {forecast?.is_abstained ? (
            <div className="alert alert-warning" style={{ margin: 0 }}>
              <AlertTriangle size={20} />
              <div>
                <strong>Model Abstained from Generating Prediction</strong>
                <p style={{ marginTop: '4px', fontSize: '13px' }}>
                  {forecast.abstention_reason || 'Insufficient recent observations or observation staleness exceeded maximum confidence threshold.'}
                </p>
                <div style={{ fontSize: '11px', marginTop: '6px', opacity: 0.9 }}>
                  RoadMind AI explicitly avoids generating ungrounded synthetic numbers when sensor telemetry is missing or untrustworthy.
                </div>
              </div>
            </div>
          ) : (
            /* Forecast Summary Cards */
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
              <div className="card" style={{ borderLeft: '4px solid var(--primary-500)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Predicted Speed (+{horizonMinutes}m)</div>
                <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--primary-500)', margin: '4px 0' }}>
                  {formatSpeed(forecast?.predicted_speed_mps)}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Target: {formatDateTime(forecast?.target_time)}
                </div>
              </div>

              <div className="card" style={{ borderLeft: '4px solid var(--accent-cyan)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Empirical Uncertainty Bound</div>
                <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: '4px 0' }}>
                  {formatSpeed(forecast?.interval_lower_mps)} – {formatSpeed(forecast?.interval_upper_mps)}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  ±1.96 standard deviation confidence interval
                </div>
              </div>

              <div className="card" style={{ borderLeft: '4px solid var(--status-emerald)' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Sensor Data Freshness</div>
                <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: '4px 0' }}>
                  {history?.recent_observations?.length ?? 0} Observations
                </div>
                <div style={{ fontSize: '11px', color: 'var(--status-emerald)' }}>
                  Telemetry active within sliding window
                </div>
              </div>
            </div>
          )}

          {/* Speed Trajectory Chart */}
          <div className="card">
            <div className="card-header">
              <div className="card-title" style={{ fontSize: '14px' }}>
                <Gauge size={16} />
                <span>Observed Speed Trajectory vs Forecast (km/h)</span>
              </div>
              <span className="badge badge-slate">{modelType.replace('_', ' ').toUpperCase()}</span>
            </div>

            <div style={{ width: '100%', height: '320px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="timeLabel" stroke={textColor} fontSize={11} />
                  <YAxis stroke={textColor} fontSize={11} domain={[0, 'auto']} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-surface)',
                      borderColor: 'var(--border-medium)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Line
                    type="monotone"
                    dataKey="actualSpeed"
                    name="Observed Speed (km/h)"
                    stroke="#38bdf8"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: '#38bdf8' }}
                    activeDot={{ r: 6 }}
                  />
                  {forecast && !forecast.is_abstained && (
                    <Line
                      type="monotone"
                      dataKey="predictedSpeed"
                      name="Forecast Speed (km/h)"
                      stroke="#2563eb"
                      strokeWidth={3}
                      strokeDasharray="5 5"
                      dot={{ r: 6, fill: '#2563eb' }}
                    />
                  )}
                  {forecast && !forecast.is_abstained && (
                    <Area
                      type="monotone"
                      dataKey="upperBound"
                      name="Upper Bound (km/h)"
                      stroke="transparent"
                      fill="#3b82f6"
                      fillOpacity={0.15}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
