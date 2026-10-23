import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  BarChart3,
  Clock,
  Layers,
  RefreshCw,
} from 'lucide-react';
import { api } from '../../api/client';
import type { EvaluationsData } from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useTheme } from '../../context/ThemeContext';
import { formatDateTime } from '../../utils/formatters';

export const EvaluationView: React.FC = () => {
  const { replayTime } = useReplay();
  const { theme } = useTheme();
  const [data, setData] = useState<EvaluationsData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchEvaluations = async () => {
    setLoading(true);
    try {
      const res = await api.getEvaluations(replayTime || undefined);
      setData(res);
    } catch (err) {
      console.error('Failed to load evaluations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvaluations();
  }, [replayTime]);

  const isDark = theme === 'dark';
  const gridColor = isDark ? '#1e293b' : '#e2e8f0';
  const textColor = isDark ? '#94a3b8' : '#64748b';

  // Format chart data from horizon_summaries
  const chartData: Array<{
    horizon: string;
    maeKmph: number;
    rmseKmph: number;
    sampleCount: number;
  }> = [];

  if (data?.horizon_summaries) {
    for (const [key, metrics] of Object.entries(data.horizon_summaries)) {
      const maeKmph = Math.round(metrics.mae_mps * 3.6 * 10) / 10;
      const rmseKmph = Math.round(metrics.rmse_mps * 3.6 * 10) / 10;
      chartData.push({
        horizon: `${key}m Horizon`,
        maeKmph,
        rmseKmph,
        sampleCount: metrics.sample_count,
      });
    }
  }

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Header Card */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <BarChart3 size={20} color="var(--primary-500)" />
              <span>Forecast Evaluation & Empirical Accuracy Benchmarks</span>
            </div>
            <div className="card-subtitle">
              Ground-truth verification: comparing historical predictions against subsequent physical sensor observations
            </div>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-icon"
            onClick={fetchEvaluations}
            title="Refresh evaluations"
          >
            <RefreshCw size={15} />
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px', color: 'var(--text-muted)' }}>
          <span>Evaluated At: <strong>{formatDateTime(data?.evaluation_time)}</strong></span>
          <span>&bull;</span>
          <span>Temporal Matching Window: <strong>±{data?.tolerance_minutes ?? 5} minutes</strong></span>
        </div>
      </div>

      {loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '60px' }}>
          <div className="pulse-dot" style={{ width: '12px', height: '12px', margin: '0 auto 10px' }} />
          <p style={{ color: 'var(--text-muted)' }}>Calculating empirical forecast residuals...</p>
        </div>
      ) : !data || !data.horizon_summaries || Object.keys(data.horizon_summaries).length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <Clock size={32} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
          <h3>No Matched Observation Pairs Yet</h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '420px', margin: '6px auto' }}>
            Empirical evaluation requires matching past predictions with ground-truth observations recorded in subsequent time windows. Switch to a post-incident replay preset to inspect backtest metrics.
          </p>
        </div>
      ) : (
        <>
          {/* Horizon Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            {Object.entries(data.horizon_summaries).map(([key, metrics]) => {
              const maeKmph = Math.round(metrics.mae_mps * 3.6 * 10) / 10;
              const rmseKmph = Math.round(metrics.rmse_mps * 3.6 * 10) / 10;
              return (
                <div key={key} className="card" style={{ borderTop: '4px solid var(--primary-600)' }}>
                  <div className="card-header">
                    <div>
                      <div className="card-title" style={{ fontSize: '15px' }}>
                        <Clock size={16} />
                        <span>+{key} Minutes Horizon</span>
                      </div>
                      <div className="card-subtitle">{metrics.sample_count} Verified Observation Pairs</div>
                    </div>
                    <span className="badge badge-emerald">Verified</span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '6px' }}>
                    <div style={{ background: 'var(--bg-surface-subtle)', padding: '10px', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>MAE (Mean Absolute Error)</div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                        {maeKmph} km/h
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>({metrics.mae_mps.toFixed(2)} m/s)</div>
                    </div>

                    <div style={{ background: 'var(--bg-surface-subtle)', padding: '10px', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>RMSE (Root Mean Square)</div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                        {rmseKmph} km/h
                      </div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>({metrics.rmse_mps.toFixed(2)} m/s)</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Bar Chart comparing MAE and RMSE */}
          <div className="card">
            <div className="card-header">
              <div className="card-title" style={{ fontSize: '14px' }}>
                <Layers size={16} />
                <span>Forecast Error Metrics by Horizon (km/h)</span>
              </div>
            </div>

            <div style={{ width: '100%', height: '300px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="horizon" stroke={textColor} fontSize={12} />
                  <YAxis stroke={textColor} fontSize={12} />
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
                  <Bar dataKey="maeKmph" name="MAE (km/h)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="rmseKmph" name="RMSE (km/h)" fill="#0284c7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
