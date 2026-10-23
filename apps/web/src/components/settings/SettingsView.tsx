import React, { useState } from 'react';
import {
  Server,
  Key,
  Database,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  Eye,
  EyeOff,
  Info,
} from 'lucide-react';
import { api, DEFAULT_API_BASE, DEFAULT_OPERATOR_TOKEN } from '../../api/client';

export const SettingsView: React.FC = () => {
  const [apiUrl, setApiUrl] = useState<string>(() => {
    return localStorage.getItem('roadmind_api_url') || DEFAULT_API_BASE;
  });

  const [operatorToken, setOperatorToken] = useState<string>(() => {
    return localStorage.getItem('roadmind_operator_token') || DEFAULT_OPERATOR_TOKEN;
  });

  const [showToken, setShowToken] = useState<boolean>(false);
  const [testingConnection, setTestingConnection] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<{ ok: boolean; message: string } | null>(null);

  const [seeding, setSeeding] = useState<boolean>(false);
  const [seedResult, setSeedResult] = useState<{ status: string; counts: Record<string, number> } | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  const handleSaveApi = () => {
    localStorage.setItem('roadmind_api_url', apiUrl.trim());
    localStorage.setItem('roadmind_operator_token', operatorToken.trim());
    setConnectionStatus({ ok: true, message: 'Settings saved to browser local storage.' });
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setConnectionStatus(null);
    try {
      const res = await api.getHealth();
      setConnectionStatus({
        ok: res.status === 'healthy',
        message: `Connected successfully! Version: ${res.version}, Environment: ${res.environment}, Database: ${res.database}`,
      });
    } catch (err: any) {
      setConnectionStatus({
        ok: false,
        message: `Connection failed: ${err.message || 'Make sure the FastAPI backend is running.'}`,
      });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSeedDatabase = async () => {
    if (!window.confirm('Reset and re-seed the benchmark synthetic database? This will restore initial conditions.')) {
      return;
    }
    setSeeding(true);
    setSeedResult(null);
    setSeedError(null);
    try {
      const res = await api.seedDatabase(true);
      setSeedResult(res);
    } catch (err: any) {
      setSeedError(err.message || 'Failed to re-seed database. Verify operator token credentials.');
    } finally {
      setSeeding(false);
    }
  };

  return (
    <div style={{ maxWidth: '840px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Backend API Configuration */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Server size={18} color="var(--primary-500)" />
              <span>Backend API Configuration</span>
            </div>
            <div className="card-subtitle">
              Configure target FastAPI server address and connection parameters
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="api-base-url">API Base URL</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                id="api-base-url"
                type="text"
                className="input-text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000"
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleTestConnection}
                disabled={testingConnection}
              >
                {testingConnection ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Default development URL is <code>http://127.0.0.1:8000</code>.
            </span>
          </div>

          {connectionStatus && (
            <div className={`alert ${connectionStatus.ok ? 'alert-success' : 'alert-danger'}`} style={{ margin: 0 }}>
              {connectionStatus.ok ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
              <span>{connectionStatus.message}</span>
            </div>
          )}
        </div>
      </div>

      {/* Operator Authorization Credentials */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Key size={18} color="var(--status-amber)" />
              <span>Operator Authorization & Security</span>
            </div>
            <div className="card-subtitle">
              Configure credentials for protected operator endpoints (incident review, admin seed)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="operator-token">Operator Secret Token</label>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                id="operator-token"
                type={showToken ? 'text' : 'password'}
                className="input-text"
                value={operatorToken}
                onChange={(e) => setOperatorToken(e.target.value)}
                placeholder="Enter authorized token..."
              />
              <button
                type="button"
                className="btn btn-secondary btn-icon"
                onClick={() => setShowToken(!showToken)}
                title={showToken ? 'Hide token' : 'Show token'}
              >
                {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Sent as <code>X-Reviewer-Token</code> header for privileged operations. Never logged or committed to source control.
            </span>
          </div>

          <div>
            <button type="button" className="btn btn-primary" onClick={handleSaveApi}>
              Save Settings to Browser
            </button>
          </div>
        </div>
      </div>

      {/* Database Management & Re-seeder */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Database size={18} color="var(--accent-cyan)" />
              <span>Benchmark Network & Synthetic Database Re-seeder</span>
            </div>
            <div className="card-subtitle">
              Reset Sector 7 Corridor database to verified benchmark state
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Restores the deterministic 7-node network, initial sensor telemetry observations, historical incident episodes, and empirical ground-truth outcomes.
          </p>

          <div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleSeedDatabase}
              disabled={seeding}
              style={{ color: 'var(--status-red)' }}
            >
              <RotateCcw size={16} />
              <span>{seeding ? 'Re-seeding Database...' : 'Reset & Re-seed Benchmark Data'}</span>
            </button>
          </div>

          {seedResult && (
            <div className="alert alert-success" style={{ margin: 0 }}>
              <CheckCircle size={16} />
              <div>
                <strong>Database re-seeded successfully!</strong>
                <div style={{ fontSize: '11px', marginTop: '4px' }}>
                  {Object.entries(seedResult.counts).map(([k, v]) => `${k}: ${v}`).join(' | ')}
                </div>
              </div>
            </div>
          )}

          {seedError && (
            <div className="alert alert-danger" style={{ margin: 0 }}>
              <AlertTriangle size={16} />
              <span>{seedError}</span>
            </div>
          )}
        </div>
      </div>

      {/* Architecture & Hackathon Info */}
      <div className="card">
        <div className="card-header">
          <div className="card-title" style={{ fontSize: '14px' }}>
            <Info size={16} />
            <span>NEXATHON 2026 Project Architecture</span>
          </div>
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          <div><strong>Track:</strong> Traffic Intelligence</div>
          <div><strong>Venue:</strong> SDIT, Mangaluru</div>
          <div><strong>Geographic Bounds:</strong> Sector 7 Corridor, New York (lat [40.745, 40.760], lon [-73.985, -73.960])</div>
          <div><strong>Network Topology:</strong> 7 Junction Nodes, 9 Directed Segments, 2 Alternative Arterials</div>
          <div><strong>Core Innovations:</strong> Evidence-Aware Clustering, Abstention Guardrails, Counterfactual Scenario Comparison (Robust Alternative vs Evidence Sensitive)</div>
        </div>
      </div>
    </div>
  );
};
