import React, { useEffect, useState } from 'react';
import {
  Menu,
  Sun,
  Moon,
  Clock,
  Radio,
  Wifi,
  WifiOff,
  RotateCcw,
} from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useReplay } from '../../context/ReplayContext';
import { DEMO_PRESETS } from '../../utils/constants';
import { formatTimeOnly } from '../../utils/formatters';
import { api } from '../../api/client';
import type { ActiveTab } from './Sidebar';

interface TopbarProps {
  activeTab: ActiveTab;
  onOpenMobile: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ activeTab, onOpenMobile }) => {
  const { theme, toggleTheme } = useTheme();
  const { replayTime, isReplay, activePresetIndex, applyPreset, resetToLive } = useReplay();
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);

  // Poll backend health once on mount and every 30s
  useEffect(() => {
    let mounted = true;
    const checkHealth = async () => {
      try {
        const res = await api.getHealth();
        if (mounted) setIsBackendOnline(res.status === 'healthy');
      } catch {
        if (mounted) setIsBackendOnline(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const getTabTitle = (tab: ActiveTab) => {
    switch (tab) {
      case 'dashboard':
        return 'System Overview';
      case 'map':
        return 'Live Road Network & Congestion Map';
      case 'planner':
        return 'Scenario Simulation & Route Planner';
      case 'report':
        return 'Citizen Incident Report';
      case 'incidents':
        return 'Incident Episodes & Operator Review';
      case 'forecasting':
        return 'Short-Horizon Traffic Speed Forecasting';
      case 'memory':
        return 'Road Memory & Inspection Priorities';
      case 'evaluations':
        return 'Empirical Forecast Evaluations';
      case 'settings':
        return 'System & API Settings';
    }
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="btn btn-ghost btn-icon mobile-only"
          onClick={onOpenMobile}
          style={{ display: 'none' }}
        >
          <Menu size={20} />
        </button>

        <div>
          <h1 style={{ fontSize: '16px', fontWeight: 600, margin: 0, letterSpacing: '-0.2px' }}>
            {getTabTitle(activeTab)}
          </h1>
        </div>
      </div>

      <div className="topbar-right">
        {/* Preset Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <select
            className="input-select"
            style={{ width: 'auto', padding: '6px 10px', fontSize: '12px' }}
            value={activePresetIndex !== null ? String(activePresetIndex) : 'custom'}
            onChange={(e) => {
              const val = e.target.value;
              if (val === 'live') {
                resetToLive();
              } else if (val !== 'custom') {
                applyPreset(Number(val));
              }
            }}
          >
            <option value="live">🔴 Live Real-Time</option>
            {DEMO_PRESETS.map((preset, idx) => (
              <option key={preset.name} value={String(idx)}>
                ⏱️ {preset.name} ({formatTimeOnly(preset.timestamp)})
              </option>
            ))}
          </select>

          {isReplay ? (
            <div className="status-pill replay" title={`Historical replay at ${replayTime}`}>
              <Clock size={12} />
              <span>REPLAY: {formatTimeOnly(replayTime)}</span>
              <button
                type="button"
                onClick={resetToLive}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'inherit',
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: 0,
                  marginLeft: 4,
                }}
                title="Reset to Live Mode"
              >
                <RotateCcw size={11} />
              </button>
            </div>
          ) : (
            <div className="status-pill live">
              <span className="pulse-dot" />
              <Radio size={12} />
              <span>LIVE</span>
            </div>
          )}
        </div>

        {/* Backend Online Pill */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '11px',
            color: isBackendOnline ? 'var(--status-emerald)' : 'var(--status-red)',
            padding: '4px 8px',
            background: 'var(--bg-surface-subtle)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}
          title={isBackendOnline ? 'Backend API connected' : 'Backend API disconnected'}
        >
          {isBackendOnline ? <Wifi size={13} /> : <WifiOff size={13} />}
          <span>{isBackendOnline === null ? 'Checking...' : isBackendOnline ? 'API Connected' : 'Offline'}</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          type="button"
          className="btn btn-secondary btn-icon"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} theme`}
        >
          {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>
      </div>
    </header>
  );
};
