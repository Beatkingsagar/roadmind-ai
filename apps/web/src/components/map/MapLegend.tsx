import React from 'react';
import { useRoute } from '../../context/RouteContext';
import { CONGESTION_COLORS } from '../../utils/constants';

export const MapLegend: React.FC = () => {
  const { mapMode } = useRoute();

  if (mapMode === 'real_world') {
    return (
      <div
        style={{
          position: 'absolute',
          bottom: '24px',
          left: '20px',
          zIndex: 1000,
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 16px',
          boxShadow: 'var(--shadow-md)',
          fontSize: '11px',
          maxWidth: '300px',
          pointerEvents: 'auto',
        }}
      >
        <div style={{ fontWeight: 700, marginBottom: '6px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: 'var(--primary-500)' }} />
          <span>Real-World Geography Mode</span>
        </div>

        <div style={{ color: 'var(--text-secondary)', fontSize: '10px', marginBottom: '8px' }}>
          Mangaluru & Coastal Karnataka Corridor &bull; Verified CARTO / OpenStreetMap Basemap
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#3b82f6', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '8px', fontWeight: 700 }}>●</span>
            <span>Commercial & Transit Hubs (Hampankatta, Lalbagh)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10b981', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '8px', fontWeight: 700 }}>●</span>
            <span>Highway Arterials (NH 66 / NH 73 Interchanges)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#a855f7', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '8px', fontWeight: 700 }}>●</span>
            <span>Aviation Terminal (Mangaluru Intl Airport IXE)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f59e0b', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '8px', fontWeight: 700 }}>●</span>
            <span>Academic Corridor (SDIT Kenjar, NITK)</span>
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '8px', paddingTop: '6px', fontSize: '10px', color: 'var(--text-muted)' }}>
          Phase 1 Real Geography &bull; Synthetic data isolated from real map
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '24px',
        left: '20px',
        zIndex: 1000,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-medium)',
        borderRadius: 'var(--radius-md)',
        padding: '12px 16px',
        boxShadow: 'var(--shadow-md)',
        fontSize: '11px',
        maxWidth: '280px',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: '8px', color: 'var(--text-primary)' }}>
        Road Condition & Legend
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '16px', height: '4px', background: CONGESTION_COLORS.freeFlow, borderRadius: '2px' }} />
          <span>Free-Flow (≥85% speed)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '16px', height: '4px', background: CONGESTION_COLORS.moderate, borderRadius: '2px' }} />
          <span>Moderate Slowdown (60–84%)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '16px', height: '4px', background: CONGESTION_COLORS.heavy, borderRadius: '2px' }} />
          <span>Heavy Congestion (30–59%)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '16px', height: '4px', background: CONGESTION_COLORS.severe, borderRadius: '2px' }} />
          <span>Severe Delay / Blocked (&lt;30%)</span>
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '8px', paddingTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10b981', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '8px', fontWeight: 700 }}>A</span>
          <span>Origin Junction</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#2563eb', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '8px', fontWeight: 700 }}>B</span>
          <span>Destination Junction</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#ef4444', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '9px', fontWeight: 700 }}>!</span>
          <span>Active Incident Episode</span>
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '8px', paddingTop: '6px', fontSize: '10px', color: 'var(--text-muted)' }}>
        Deterministic Synthetic Benchmark Network (Sector 7 Corridor)
      </div>
    </div>
  );
};
