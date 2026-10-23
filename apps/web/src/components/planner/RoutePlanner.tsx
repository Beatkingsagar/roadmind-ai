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
  RefreshCw,
} from 'lucide-react';
import { useRoute } from '../../context/RouteContext';
import { SUPPORTED_NODES } from '../../utils/constants';
import { formatDistance, formatHoursAndMinutes } from '../../utils/formatters';
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
    realRouteResponse,
    selectedRealRouteIndex,
    setSelectedRealRouteIndex,
    isCalculatingRealRoute,
    realRouteError,
    calculateRealRoute,
    clearRealRoute,
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

          {/* Action & Status Row */}
          {realRouteError && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid var(--status-red)',
                color: 'var(--status-red)',
                fontSize: '12px',
              }}
            >
              <AlertCircle size={16} />
              <span>{realRouteError}</span>
            </div>
          )}

          {/* Quick Corridor Selection Chips if neither is selected */}
          {!realOrigin && !realDestination && !realRouteResponse && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
                QUICK CORRIDOR DEMOS:
              </span>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  id="btn-quick-kundapura-mangaluru"
                  className="btn btn-secondary"
                  onClick={() => {
                    setRealOrigin({
                      id: 'cache_kundapura',
                      name: 'Kundapura',
                      displayName: 'Kundapura, Udupi District, Karnataka, India',
                      lat: 13.6268,
                      lon: 74.6917,
                      source: 'verified_cache',
                    });
                    setRealDestination({
                      id: 'cache_mangaluru',
                      name: 'Mangaluru',
                      displayName: 'Mangaluru, Dakshina Kannada, Karnataka, India',
                      lat: 12.9141,
                      lon: 74.8560,
                      source: 'verified_cache',
                    });
                  }}
                  style={{ fontSize: '11px', padding: '4px 10px', borderRadius: 'var(--radius-full)' }}
                >
                  Kundapura ➔ Mangaluru (NH 66)
                </button>
                <button
                  type="button"
                  id="btn-quick-udupi-surathkal"
                  className="btn btn-secondary"
                  onClick={() => {
                    setRealOrigin({
                      id: 'cache_udupi',
                      name: 'Udupi',
                      displayName: 'Udupi, Udupi District, Karnataka, India',
                      lat: 13.3409,
                      lon: 74.7421,
                      source: 'verified_cache',
                    });
                    setRealDestination({
                      id: 'cache_surathkal',
                      name: 'Surathkal',
                      displayName: 'Surathkal, Mangaluru, Dakshina Kannada, Karnataka, India',
                      lat: 13.0119,
                      lon: 74.7943,
                      source: 'verified_cache',
                    });
                  }}
                  style={{ fontSize: '11px', padding: '4px 10px', borderRadius: 'var(--radius-full)' }}
                >
                  Udupi ➔ Surathkal
                </button>
              </div>
            </div>
          )}

          {/* Action Row */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <button
              type="button"
              id="btn-clear-real-places"
              className="btn btn-secondary"
              onClick={() => {
                setRealOrigin(null);
                setRealDestination(null);
                clearRealRoute();
              }}
              disabled={!realOrigin && !realDestination && !realRouteResponse}
              style={{ flex: 1, padding: '9px 14px', fontSize: '12px' }}
            >
              Clear
            </button>
            <button
              type="button"
              id="btn-calculate-real-route"
              className="btn btn-primary"
              onClick={calculateRealRoute}
              disabled={!realOrigin || !realDestination || isCalculatingRealRoute}
              style={{
                flex: 2,
                padding: '9px 14px',
                fontSize: '12px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              {isCalculatingRealRoute ? (
                <>
                  <RefreshCw size={14} className="spin" />
                  <span>Calculating Route via OSRM...</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Calculate Road Route</span>
                </>
              )}
            </button>
          </div>

          {/* ================================================================= */}
          {/* CALCULATED ROAD ROUTE METRICS & ALTERNATIVES (PHASE 3)             */}
          {/* ================================================================= */}
          {realRouteResponse && (
            <div
              id="real-route-results-card"
              style={{
                marginTop: '8px',
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              {/* Header & Status */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CheckCircle2 size={16} color="var(--status-emerald)" />
                  <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
                    Verified Road Route ({realRouteResponse.profile})
                  </strong>
                </div>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    fontSize: '10px',
                    fontWeight: 600,
                    background: 'rgba(16, 185, 129, 0.15)',
                    color: '#10b981',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                  }}
                >
                  Provider: {realRouteResponse.provider.toUpperCase()}
                </span>
              </div>

              {/* Alternative Route Tabs (if provider returned alternatives) */}
              {realRouteResponse.alternative_routes.length > 0 && (
                <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-surface)', padding: '4px', borderRadius: 'var(--radius-sm)' }}>
                  <button
                    type="button"
                    onClick={() => setSelectedRealRouteIndex(0)}
                    style={{
                      flex: 1,
                      padding: '6px 8px',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: 'none',
                      background: selectedRealRouteIndex === 0 ? 'var(--primary-600)' : 'transparent',
                      color: selectedRealRouteIndex === 0 ? '#ffffff' : 'var(--text-secondary)',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    Primary: {realRouteResponse.primary_route.summary || 'Main Route'}
                  </button>
                  {realRouteResponse.alternative_routes.map((alt, idx) => {
                    const altIdx = idx + 1;
                    return (
                      <button
                        key={alt.route_index}
                        type="button"
                        onClick={() => setSelectedRealRouteIndex(altIdx)}
                        style={{
                          flex: 1,
                          padding: '6px 8px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          border: 'none',
                          background: selectedRealRouteIndex === altIdx ? 'var(--primary-600)' : 'transparent',
                          color: selectedRealRouteIndex === altIdx ? '#ffffff' : 'var(--text-secondary)',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        Alt {altIdx}: {alt.summary || `Route ${altIdx}`}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Active Route Details */}
              {(() => {
                const activeRoute =
                  selectedRealRouteIndex === 0
                    ? realRouteResponse.primary_route
                    : realRouteResponse.alternative_routes[selectedRealRouteIndex - 1] ||
                      realRouteResponse.primary_route;

                return (
                  <>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                        gap: '10px',
                      }}
                    >
                      <div
                        style={{
                          background: 'var(--bg-surface)',
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Road Distance
                        </span>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                          {activeRoute.distance_km} km
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          {formatDistance(activeRoute.distance_meters)}
                        </span>
                      </div>

                      <div
                        style={{
                          background: 'var(--bg-surface)',
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Est. Duration
                        </span>
                        <div style={{ fontSize: '18px', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>
                          {formatHoursAndMinutes(activeRoute.duration_seconds)}
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          ~{activeRoute.duration_minutes} mins
                        </span>
                      </div>

                      <div
                        style={{
                          background: 'var(--bg-surface)',
                          padding: '10px 12px',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Corridor
                        </span>
                        <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }} title={activeRoute.summary}>
                          {activeRoute.summary || 'Direct Highway'}
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                          {activeRoute.geometry.coordinates.length} waypoints
                        </span>
                      </div>
                    </div>

                    {/* Standard Routability Notice */}
                    <div
                      style={{
                        padding: '8px 10px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'rgba(56, 189, 248, 0.08)',
                        border: '1px solid rgba(56, 189, 248, 0.2)',
                        fontSize: '11px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.4,
                      }}
                    >
                      <strong style={{ color: '#38bdf8' }}>Notice:</strong> Standard road network routability estimate ({realRouteResponse.traffic_model}). Does not reflect live traffic conditions or synthetic scenario overrides.
                    </div>

                    {/* Attribution */}
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'right' }}>
                      {realRouteResponse.attribution}
                    </div>
                  </>
                );
              })()}
            </div>
          )}
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
