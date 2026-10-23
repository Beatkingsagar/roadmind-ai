import React from 'react';
import {
  ArrowUpDown,
  Navigation,
  MapPin,
  Play,
  AlertCircle,
  Globe,
  FlaskConical,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { useRoute } from '../../context/RouteContext';
import { SUPPORTED_NODES } from '../../utils/constants';
import { PlaceSearchInput } from './PlaceSearchInput';

export const RoutePlanner: React.FC = () => {
  const {
    mapMode,
    setMapMode,
    originNode,
    destinationNode,
    setOriginNode,
    setDestinationNode,
    swapNodes,
    isCalculating,
    calculateRoute,
    errorMessage,
    setErrorMessage,
    pickMode,
    setPickMode,
    realOrigin,
    realDestination,
    setRealOrigin,
    setRealDestination,
    swapRealPlaces,
  } = useRoute();

  const handleCalculateSynthetic = (e: React.FormEvent) => {
    e.preventDefault();
    calculateRoute();
  };

  const handlePickOrigin = () => {
    setPickMode(pickMode === 'origin' ? null : 'origin');
  };

  const handlePickDestination = () => {
    setPickMode(pickMode === 'destination' ? null : 'destination');
  };

  return (
    <div className="card" style={{ maxWidth: '640px', width: '100%', margin: '0 auto' }}>
      {/* Mode Switch Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '16px',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '12px',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Navigation size={18} color="var(--primary-500)" />
          <span style={{ fontWeight: 700, fontSize: '15px' }}>
            {mapMode === 'real_world'
              ? 'Real-World Journey Planner'
              : 'Synthetic Demo Network (Sector 7)'}
          </span>
        </div>

        {/* Mode Selector Toggle */}
        <div style={{ display: 'flex', background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-full)', padding: '2px' }}>
          <button
            type="button"
            id="tab-planner-mode-real"
            onClick={() => setMapMode('real_world')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: 'var(--radius-full)',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              background: mapMode === 'real_world' ? 'var(--primary-600)' : 'transparent',
              color: mapMode === 'real_world' ? '#ffffff' : 'var(--text-secondary)',
              transition: 'all 0.15s ease',
            }}
          >
            <Globe size={12} />
            <span>Real World</span>
          </button>
          <button
            type="button"
            id="tab-planner-mode-synthetic"
            onClick={() => setMapMode('synthetic_demo')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: 'var(--radius-full)',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              background: mapMode === 'synthetic_demo' ? 'var(--primary-600)' : 'transparent',
              color: mapMode === 'synthetic_demo' ? '#ffffff' : 'var(--text-secondary)',
              transition: 'all 0.15s ease',
            }}
          >
            <FlaskConical size={12} />
            <span>Sector 7</span>
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* MODE 1: REAL-WORLD JOURNEY PLANNER (PHASE 2 REAL-PLACE SEARCH)       */}
      {/* =================================================================== */}
      {mapMode === 'real_world' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            Search verified origin and destination places across Coastal Karnataka (e.g., Kundapura to Mangaluru).
            Places are validated with WGS84 geographic coordinates.
          </div>

          {/* Real Origin Input */}
          <PlaceSearchInput
            id="real-origin-search"
            label="Origin Location (From)"
            placeholder="Type place name (e.g., Kundapura, Udupi, Surathkal)..."
            selectedPlace={realOrigin}
            onSelectPlace={setRealOrigin}
            accentColor="#10b981"
            badgeLabel="A"
            exampleSuggestions={['Kundapura', 'Udupi', 'Surathkal']}
          />

          {/* Bidirectional Swap Button */}
          <div style={{ display: 'flex', justifyContent: 'center', margin: '-4px 0' }}>
            <button
              type="button"
              id="btn-swap-real-places"
              className="btn btn-ghost btn-icon"
              onClick={swapRealPlaces}
              title="Swap Origin and Destination"
              style={{
                borderRadius: '50%',
                border: '1px solid var(--border-medium)',
                background: 'var(--bg-surface)',
                boxShadow: 'var(--shadow-sm)',
                padding: '8px',
              }}
            >
              <ArrowUpDown size={16} />
            </button>
          </div>

          {/* Real Destination Input */}
          <PlaceSearchInput
            id="real-dest-search"
            label="Destination Location (To)"
            placeholder="Type place name (e.g., Mangaluru, SDIT Kenjar, Airport)..."
            selectedPlace={realDestination}
            onSelectPlace={setRealDestination}
            accentColor="#2563eb"
            badgeLabel="B"
            exampleSuggestions={['Mangaluru', 'SDIT Kenjar', 'Manipal']}
          />

          {/* Selected Corridor Status Summary Card */}
          {(realOrigin || realDestination) && (
            <div
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 16px',
                fontSize: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CheckCircle2 size={15} color="var(--status-emerald)" />
                <span>Geographic Selection Verified</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 10px', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, color: '#10b981' }}>Origin:</span>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {realOrigin ? (
                    <>
                      <strong>{realOrigin.name}</strong> ({realOrigin.lat.toFixed(4)}° N, {realOrigin.lon.toFixed(4)}° E)
                    </>
                  ) : (
                    <em style={{ color: 'var(--text-muted)' }}>Not selected</em>
                  )}
                </span>

                <span style={{ fontWeight: 600, color: '#3b82f6' }}>Destination:</span>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {realDestination ? (
                    <>
                      <strong>{realDestination.name}</strong> ({realDestination.lat.toFixed(4)}° N, {realDestination.lon.toFixed(4)}° E)
                    </>
                  ) : (
                    <em style={{ color: 'var(--text-muted)' }}>Not selected</em>
                  )}
                </span>
              </div>

              {realOrigin && realDestination && (
                <div
                  style={{
                    borderTop: '1px solid var(--border-subtle)',
                    paddingTop: '8px',
                    marginTop: '4px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    color: 'var(--primary-400)',
                    fontSize: '11px',
                  }}
                >
                  <Clock size={13} />
                  <span>Phase 2 Complete: Coordinates confirmed. Real road routing along NH 66 will be calculated in Phase 3.</span>
                </div>
              )}
            </div>
          )}

          {/* Action Row */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setRealOrigin(null);
                setRealDestination(null);
              }}
              disabled={!realOrigin && !realDestination}
              style={{ flex: 1, padding: '9px 14px', fontSize: '12px' }}
            >
              Clear Places
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!realOrigin || !realDestination}
              title={
                realOrigin && realDestination
                  ? 'Ready for Phase 3 Road Routing'
                  : 'Select both origin and destination places first'
              }
              style={{
                flex: 2,
                padding: '9px 14px',
                fontSize: '12px',
                fontWeight: 600,
                opacity: realOrigin && realDestination ? 1 : 0.6,
              }}
            >
              <span>{realOrigin && realDestination ? 'Ready for Phase 3 Route Engine' : 'Select Origin & Destination'}</span>
            </button>
          </div>
        </div>
      ) : (
        /* =================================================================== */
        /* MODE 2: SYNTHETIC DEMO NETWORK (SECTOR 7 BENCHMARK CORRIDOR)       */
        /* =================================================================== */
        <form onSubmit={handleCalculateSynthetic} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Origin Row */}
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="origin-select" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }} />
              <span>Origin Junction (From)</span>
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <select
                id="origin-select"
                className="input-select"
                value={originNode}
                onChange={(e) => {
                  setOriginNode(e.target.value);
                  setErrorMessage(null);
                }}
              >
                {SUPPORTED_NODES.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={`btn btn-secondary ${pickMode === 'origin' ? 'active' : ''}`}
                onClick={handlePickOrigin}
                title="Pick origin directly on the map"
                style={{ padding: '8px 12px' }}
              >
                <MapPin size={15} color={pickMode === 'origin' ? 'var(--primary-500)' : 'currentColor'} />
                <span>Map</span>
              </button>
            </div>
          </div>

          {/* Swap Button */}
          <div style={{ display: 'flex', justifyContent: 'center', margin: '-6px 0' }}>
            <button
              type="button"
              className="btn btn-ghost btn-icon"
              onClick={swapNodes}
              title="Swap Origin and Destination"
              style={{ borderRadius: '50%', border: '1px solid var(--border-medium)' }}
            >
              <ArrowUpDown size={16} />
            </button>
          </div>

          {/* Destination Row */}
          <div className="input-group" style={{ margin: 0 }}>
            <label className="input-label" htmlFor="dest-select" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#2563eb' }} />
              <span>Destination Junction (To)</span>
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <select
                id="dest-select"
                className="input-select"
                value={destinationNode}
                onChange={(e) => {
                  setDestinationNode(e.target.value);
                  setErrorMessage(null);
                }}
              >
                {SUPPORTED_NODES.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={`btn btn-secondary ${pickMode === 'destination' ? 'active' : ''}`}
                onClick={handlePickDestination}
                title="Pick destination directly on the map"
                style={{ padding: '8px 12px' }}
              >
                <MapPin size={15} color={pickMode === 'destination' ? 'var(--primary-500)' : 'currentColor'} />
                <span>Map</span>
              </button>
            </div>
          </div>

          {/* Quick Route Preset Pills */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Quick Presets:</span>
            <button
              type="button"
              className="badge badge-slate"
              style={{ cursor: 'pointer', border: '1px solid var(--border-medium)' }}
              onClick={() => {
                setOriginNode('node_origin');
                setDestinationNode('node_destination');
                setErrorMessage(null);
              }}
            >
              West Terminal ➔ Civic Center (Primary Corridor Decision)
            </button>
            <button
              type="button"
              className="badge badge-slate"
              style={{ cursor: 'pointer', border: '1px solid var(--border-medium)' }}
              onClick={() => {
                setOriginNode('node_hub_north');
                setDestinationNode('node_destination');
                setErrorMessage(null);
              }}
            >
              North Terminal ➔ Civic Center
            </button>
          </div>

          {/* Validation Error Banner */}
          {errorMessage && (
            <div className="alert alert-danger" style={{ margin: 0 }}>
              <AlertCircle size={16} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isCalculating}
              style={{ flex: 1, padding: '10px 16px', fontWeight: 600 }}
            >
              <Play size={16} />
              <span>{isCalculating ? 'Simulating Scenarios...' : 'Run Scenario Comparison'}</span>
            </button>
          </div>
        </form>
      )}
    </div>
  );
};
