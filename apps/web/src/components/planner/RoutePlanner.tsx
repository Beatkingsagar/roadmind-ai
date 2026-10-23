import React from 'react';
import { ArrowUpDown, Navigation, MapPin, Play, AlertCircle } from 'lucide-react';
import { useRoute } from '../../context/RouteContext';
import { SUPPORTED_NODES } from '../../utils/constants';

export const RoutePlanner: React.FC = () => {
  const {
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
  } = useRoute();

  const handleCalculate = (e: React.FormEvent) => {
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
      <div className="card-header">
        <div>
          <div className="card-title">
            <Navigation size={18} color="var(--primary-500)" />
            <span>Interactive Route Planner & Scenario Simulator</span>
          </div>
          <div className="card-subtitle">
            Routes across Sector 7 Corridor with real-time counterfactual scenario comparison
          </div>
        </div>
      </div>

      <form onSubmit={handleCalculate} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
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
    </div>
  );
};
