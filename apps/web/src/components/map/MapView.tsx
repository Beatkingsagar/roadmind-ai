import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../../api/client';
import type {
  IncidentEpisodeResponse,
  NetworkGeoJSONResponse,
  RoadStateSnapshot,
} from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useRoute } from '../../context/RouteContext';
import {
  MAP_CENTER,
  MAP_DEFAULT_ZOOM,
  SUPPORTED_NODES,
  getCongestionColor,
} from '../../utils/constants';
import { formatSpeed } from '../../utils/formatters';
import { MapLegend } from './MapLegend';
import { SegmentDetailsPanel } from './SegmentDetailsPanel';

export const MapView: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const roadLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const markersLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const routeLayerGroupRef = useRef<L.LayerGroup | null>(null);

  const { replayTime } = useReplay();
  const {
    originNode,
    destinationNode,
    setOriginNode,
    setDestinationNode,
    activeSimulation,
    selectedSegmentId,
    setSelectedSegmentId,
    pickMode,
    setPickMode,
  } = useRoute();

  const [networkData, setNetworkData] = useState<NetworkGeoJSONResponse | null>(null);
  const [roadStates, setRoadStates] = useState<Record<string, RoadStateSnapshot>>({});
  const [incidents, setIncidents] = useState<IncidentEpisodeResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [tileError, setTileError] = useState<boolean>(false);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: MAP_CENTER,
      zoom: MAP_DEFAULT_ZOOM,
      zoomControl: true,
      attributionControl: true,
    });

    const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | RoadMind AI',
    });

    tileLayer.on('tileerror', () => {
      setTileError(true);
    });

    tileLayer.addTo(map);

    const roadGroup = L.layerGroup().addTo(map);
    const markersGroup = L.layerGroup().addTo(map);
    const routeGroup = L.layerGroup().addTo(map);

    roadLayerGroupRef.current = roadGroup;
    markersLayerGroupRef.current = markersGroup;
    routeLayerGroupRef.current = routeGroup;
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Fetch Network Topology once
  useEffect(() => {
    let mounted = true;
    api.getNetwork()
      .then((net) => {
        if (mounted) setNetworkData(net);
      })
      .catch((err) => {
        console.error('Failed to load network GeoJSON:', err);
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Fetch Road States & Incidents whenever replayTime changes
  useEffect(() => {
    let mounted = true;
    setLoading(true);

    Promise.all([
      api.getRoadState(replayTime || undefined),
      api.getIncidents(replayTime || undefined),
    ])
      .then(([states, incs]) => {
        if (!mounted) return;
        const stateMap: Record<string, RoadStateSnapshot> = {};
        for (const s of states) {
          stateMap[s.segment_id] = s;
        }
        setRoadStates(stateMap);
        setIncidents(incs);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load road state/incidents:', err);
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [replayTime]);

  // Render Roads, Markers, and Routes
  const renderLayers = useCallback(() => {
    const map = mapInstanceRef.current;
    const roadGroup = roadLayerGroupRef.current;
    const markersGroup = markersLayerGroupRef.current;
    const routeGroup = routeLayerGroupRef.current;

    if (!map || !roadGroup || !markersGroup || !routeGroup || !networkData) return;

    roadGroup.clearLayers();
    markersGroup.clearLayers();
    routeGroup.clearLayers();

    // 1. Draw Network Segments (Polylines)
    for (const feature of networkData.features) {
      const segId = feature.properties.id as string;
      const state = roadStates[segId];
      const speedRatio = state ? (state.congestion_ratio ?? 1.0) : 1.0;
      const color = getCongestionColor(speedRatio);
      const isSelected = selectedSegmentId === segId;

      // In GeoJSON coords are [lon, lat], Leaflet expects [lat, lon]
      const latlngs = feature.geometry.coordinates.map((coord) => [coord[1], coord[0]] as [number, number]);

      // Outer glow polyline if selected
      if (isSelected) {
        const glow = L.polyline(latlngs, {
          color: '#38bdf8',
          weight: 12,
          opacity: 0.5,
          lineCap: 'round',
        });
        glow.addTo(roadGroup);
      }

      // Base road polyline
      const poly = L.polyline(latlngs, {
        color,
        weight: isSelected ? 7 : 5,
        opacity: 0.9,
        lineCap: 'round',
        lineJoin: 'round',
      });

      poly.on('click', () => {
        setSelectedSegmentId(segId);
      });

      const speedText = state ? formatSpeed(state.current_speed_mps) : 'Unknown';
      const freeFlowText = formatSpeed(feature.properties.free_flow_speed_mps as number);

      poly.bindPopup(`
        <div style="font-family: inherit; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 2px;">${feature.properties.name}</div>
          <div style="color: #64748b; font-size: 11px; margin-bottom: 6px;">ID: ${segId}</div>
          <div style="display: flex; justify-content: space-between; gap: 8px; margin-bottom: 4px;">
            <span>Current Speed:</span>
            <strong style="color: ${color}">${speedText}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; gap: 8px; margin-bottom: 8px;">
            <span>Free-Flow Speed:</span>
            <strong>${freeFlowText}</strong>
          </div>
          <div style="font-size: 10px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 4px;">
            Click to open full telemetry history
          </div>
        </div>
      `);

      poly.addTo(roadGroup);
    }

    // 2. Draw Supported Node Markers
    for (const node of SUPPORTED_NODES) {
      const isOrigin = node.id === originNode;
      const isDestination = node.id === destinationNode;

      let markerClass = 'intermediate';
      let label = '•';
      if (isOrigin) {
        markerClass = 'origin';
        label = 'A';
      } else if (isDestination) {
        markerClass = 'destination';
        label = 'B';
      }

      const icon = L.divIcon({
        className: '',
        html: `<div class="custom-node-marker ${markerClass}" style="width: 28px; height: 28px; font-size: 12px;">${label}</div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker(node.coordinates, { icon });

      marker.on('click', () => {
        if (pickMode === 'origin') {
          setOriginNode(node.id);
          setPickMode(null);
        } else if (pickMode === 'destination') {
          setDestinationNode(node.id);
          setPickMode(null);
        }
      });

      marker.bindPopup(`
        <div style="font-family: inherit; font-size: 12px; min-width: 180px;">
          <div style="font-weight: 700;">${node.name}</div>
          <div style="color: #64748b; font-size: 11px; margin-bottom: 8px;">${node.description}</div>
          <div style="display: flex; gap: 6px;">
            <button
              id="btn-set-origin-${node.id}"
              style="flex: 1; padding: 4px 8px; background: #10b981; color: white; border: none; border-radius: 4px; font-size: 11px; cursor: pointer;"
            >
              Set Origin (A)
            </button>
            <button
              id="btn-set-dest-${node.id}"
              style="flex: 1; padding: 4px 8px; background: #2563eb; color: white; border: none; border-radius: 4px; font-size: 11px; cursor: pointer;"
            >
              Set Dest (B)
            </button>
          </div>
        </div>
      `);

      marker.on('popupopen', () => {
        const origBtn = document.getElementById(`btn-set-origin-${node.id}`);
        const destBtn = document.getElementById(`btn-set-dest-${node.id}`);
        if (origBtn) {
          origBtn.onclick = () => {
            setOriginNode(node.id);
            marker.closePopup();
          };
        }
        if (destBtn) {
          destBtn.onclick = () => {
            setDestinationNode(node.id);
            marker.closePopup();
          };
        }
      });

      marker.addTo(markersGroup);
    }

    // 3. Draw Active Incidents
    for (const inc of incidents) {
      // Find matching segment geometry to place incident marker along segment
      const segId = inc.primary_segment_id;
      const feature = networkData.features.find((f) => f.properties.id === segId);
      if (feature && feature.geometry.coordinates.length > 0) {
        // Place at midpoint
        const coords = feature.geometry.coordinates;
        const midIdx = Math.floor(coords.length / 2);
        const midPoint: [number, number] = [coords[midIdx][1], coords[midIdx][0]];

        const incIcon = L.divIcon({
          className: '',
          html: `<div class="custom-node-marker incident" style="width: 26px; height: 26px; font-size: 14px;">⚠️</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        });

        const incMarker = L.marker(midPoint, { icon: incIcon, zIndexOffset: 500 });
        incMarker.bindPopup(`
          <div style="font-family: inherit; font-size: 12px;">
            <div style="font-weight: 700; color: #ef4444; margin-bottom: 2px;">⚠️ ${inc.episode_type.toUpperCase()}</div>
            <div style="font-weight: 600;">${feature.properties.name}</div>
            <div style="color: #64748b; font-size: 11px; margin-bottom: 6px;">Severity: <strong>${inc.severity_level}</strong> &bull; Status: <strong>${inc.lifecycle_status}</strong></div>
            <div style="font-size: 11px;">Confidence: <strong>${Math.round(inc.heuristic_support_score * 100)}%</strong></div>
          </div>
        `);
        incMarker.addTo(markersGroup);
      }
    }

    // 4. Draw Route Overlays if Active Simulation
    if (activeSimulation && activeSimulation.scenarios) {
      const baselineEval = activeSimulation.scenarios['baseline'];
      const closureEval = activeSimulation.scenarios['closure'] || activeSimulation.scenarios['full_closure'];

      const baselineEdges = baselineEval?.candidate_routes?.[0]?.edge_ids || baselineEval?.reference_route?.edge_ids || [];
      const closureEdges = closureEval?.candidate_routes?.[0]?.edge_ids || closureEval?.reference_route?.edge_ids || [];

      // Draw Baseline route (cyan dashed)
      for (const edgeId of baselineEdges) {
        const feature = networkData.features.find((f) => f.properties.id === edgeId);
        if (feature) {
          const latlngs = feature.geometry.coordinates.map((c) => [c[1], c[0]] as [number, number]);
          L.polyline(latlngs, {
            color: '#38bdf8',
            weight: 6,
            dashArray: '8, 8',
            opacity: 0.85,
          }).addTo(routeGroup);
        }
      }

      // Draw Recommended / Bypass Route
      for (const edgeId of closureEdges) {
        const feature = networkData.features.find((f) => f.properties.id === edgeId);
        if (feature) {
          const latlngs = feature.geometry.coordinates.map((c) => [c[1], c[0]] as [number, number]);
          L.polyline(latlngs, {
            color: '#10b981',
            weight: 5,
            opacity: 0.95,
          }).addTo(routeGroup);
        }
      }
    }
  }, [
    networkData,
    roadStates,
    incidents,
    selectedSegmentId,
    originNode,
    destinationNode,
    activeSimulation,
    pickMode,
    setOriginNode,
    setDestinationNode,
    setPickMode,
    setSelectedSegmentId,
  ]);

  // Re-run layer updates when dependencies change
  useEffect(() => {
    renderLayers();
  }, [renderLayers]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', flex: 1, overflow: 'hidden' }}>
      {/* Pick Mode Banner */}
      {pickMode && (
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1000,
            background: 'var(--navy-900)',
            color: '#fff',
            padding: '8px 18px',
            borderRadius: 'var(--radius-full)',
            boxShadow: 'var(--shadow-lg)',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            border: '1px solid var(--primary-500)',
          }}
        >
          <span>Click a node marker on the map to select {pickMode === 'origin' ? 'Origin (A)' : 'Destination (B)'}</span>
          <button
            type="button"
            className="btn btn-ghost"
            style={{ padding: '2px 8px', fontSize: '11px', color: '#93c5fd' }}
            onClick={() => setPickMode(null)}
          >
            Cancel
          </button>
        </div>
      )}

      {/* Tile Fallback Notice */}
      {tileError && (
        <div
          style={{
            position: 'absolute',
            top: '16px',
            right: '20px',
            zIndex: 1000,
            background: 'var(--status-amber-bg)',
            border: '1px solid var(--status-amber-border)',
            color: 'var(--status-amber)',
            padding: '8px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '12px',
          }}
        >
          Offline map mode: tile server unreachable, displaying vector road network directly.
        </div>
      )}

      {/* Loading Overlay */}
      {loading && !networkData && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 999,
            background: 'var(--bg-app)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            fontSize: '14px',
          }}
        >
          <div className="pulse-dot" style={{ width: '12px', height: '12px' }} />
          <span>Synchronizing road network telemetry...</span>
        </div>
      )}

      {/* Leaflet DOM Node */}
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Map Legend */}
      <MapLegend />

      {/* Segment Details Inspector Drawer */}
      {selectedSegmentId && (
        <SegmentDetailsPanel
          segmentId={selectedSegmentId}
          onClose={() => setSelectedSegmentId(null)}
        />
      )}
    </div>
  );
};
