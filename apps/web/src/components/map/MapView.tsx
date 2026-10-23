import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Globe, FlaskConical, RotateCcw, RefreshCw } from 'lucide-react';
import { api } from '../../api/client';
import type {
  IncidentEpisodeResponse,
  NetworkGeoJSONResponse,
  RoadStateSnapshot,
} from '../../api/types';
import { useReplay } from '../../context/ReplayContext';
import { useRoute } from '../../context/RouteContext';
import { useTheme } from '../../context/ThemeContext';
import {
  MANGALURU_CENTER,
  MANGALURU_DEFAULT_ZOOM,
  SECTOR_7_CENTER,
  SECTOR_7_DEFAULT_ZOOM,
  MANGALURU_LANDMARKS,
  SUPPORTED_NODES,
  TILE_PROVIDERS,
  getCongestionColor,
} from '../../utils/constants';
import { formatSpeed } from '../../utils/formatters';
import { MapLegend } from './MapLegend';
import { SegmentDetailsPanel } from './SegmentDetailsPanel';

export const MapView: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const roadLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const markersLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const routeLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const landmarksLayerGroupRef = useRef<L.LayerGroup | null>(null);

  const { theme } = useTheme();
  const { replayTime } = useReplay();
  const {
    mapMode,
    setMapMode,
    originNode,
    destinationNode,
    setOriginNode,
    setDestinationNode,
    activeSimulation,
    selectedSegmentId,
    setSelectedSegmentId,
    pickMode,
    setPickMode,
    realOrigin,
    realDestination,
    realRouteResponse,
    selectedRealRouteIndex,
  } = useRoute();

  const [networkData, setNetworkData] = useState<NetworkGeoJSONResponse | null>(null);
  const [roadStates, setRoadStates] = useState<Record<string, RoadStateSnapshot>>({});
  const [incidents, setIncidents] = useState<IncidentEpisodeResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [tileError, setTileError] = useState<boolean>(false);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialCenter = mapMode === 'real_world' ? MANGALURU_CENTER : SECTOR_7_CENTER;
    const initialZoom = mapMode === 'real_world' ? MANGALURU_DEFAULT_ZOOM : SECTOR_7_DEFAULT_ZOOM;

    const map = L.map(mapContainerRef.current, {
      center: initialCenter,
      zoom: initialZoom,
      zoomControl: true,
      attributionControl: true,
    });

    const provider = theme === 'dark' ? TILE_PROVIDERS.cartoDarkMatter : TILE_PROVIDERS.cartoVoyager;
    const tileLayer = L.tileLayer(provider.url, {
      maxZoom: provider.maxZoom,
      attribution: provider.attribution,
      subdomains: provider.subdomains,
    });

    tileLayer.on('tileload', () => {
      setTileError(false);
    });

    tileLayer.on('tileerror', () => {
      setTileError(true);
    });

    tileLayer.addTo(map);
    tileLayerRef.current = tileLayer;

    const roadGroup = L.layerGroup().addTo(map);
    const markersGroup = L.layerGroup().addTo(map);
    const routeGroup = L.layerGroup().addTo(map);
    const landmarksGroup = L.layerGroup().addTo(map);

    roadLayerGroupRef.current = roadGroup;
    markersLayerGroupRef.current = markersGroup;
    routeLayerGroupRef.current = routeGroup;
    landmarksLayerGroupRef.current = landmarksGroup;
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      tileLayerRef.current = null;
    };
  }, []); // Run once on mount

  // Update Tile Layer URL when theme changes
  useEffect(() => {
    if (!tileLayerRef.current) return;
    const provider = theme === 'dark' ? TILE_PROVIDERS.cartoDarkMatter : TILE_PROVIDERS.cartoVoyager;
    tileLayerRef.current.setUrl(provider.url);
  }, [theme]);

  // Handle smooth flyTo and size invalidation when mapMode changes
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;
    if (mapMode === 'real_world') {
      map.flyTo(MANGALURU_CENTER, MANGALURU_DEFAULT_ZOOM, { duration: 1.2 });
    } else {
      map.flyTo(SECTOR_7_CENTER, SECTOR_7_DEFAULT_ZOOM, { duration: 1.2 });
    }
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 250);
    return () => clearTimeout(timer);
  }, [mapMode]);

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

  // Render Roads, Markers, Landmarks and Routes
  const renderLayers = useCallback(() => {
    const map = mapInstanceRef.current;
    const roadGroup = roadLayerGroupRef.current;
    const markersGroup = markersLayerGroupRef.current;
    const routeGroup = routeLayerGroupRef.current;
    const landmarksGroup = landmarksLayerGroupRef.current;

    if (!map || !roadGroup || !markersGroup || !routeGroup || !landmarksGroup) return;

    roadGroup.clearLayers();
    markersGroup.clearLayers();
    routeGroup.clearLayers();
    landmarksGroup.clearLayers();

    // ==========================================
    // MODE 1: Real-World Journey Planner Mode
    // ==========================================
    if (mapMode === 'real_world') {
      // Strictly isolate real geography: Never draw synthetic roads or simulated traffic here
      for (const landmark of MANGALURU_LANDMARKS) {
        let iconEmoji = '🏛️';
        let categoryClass = 'transit';

        if (landmark.category.includes('Highway') || landmark.category.includes('Intersection') || landmark.category.includes('Gateway')) {
          iconEmoji = '🛣️';
          categoryClass = 'highway';
        } else if (landmark.category.includes('Airport') || landmark.category.includes('Aviation')) {
          iconEmoji = '✈️';
          categoryClass = 'aviation';
        } else if (landmark.category.includes('Educational') || landmark.category.includes('Campus') || landmark.id.includes('sdit')) {
          iconEmoji = '🎓';
          categoryClass = 'academic';
        }

        const icon = L.divIcon({
          className: '',
          html: `<div class="custom-node-marker landmark ${categoryClass}" style="width: 32px; height: 32px; font-size: 14px;" title="${landmark.name}">${iconEmoji}</div>`,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        });

        const marker = L.marker(landmark.coordinates, { icon });
        marker.bindPopup(`
          <div style="font-family: inherit; font-size: 12px; min-width: 220px;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px;">
              <strong style="font-size: 13px; color: var(--text-primary);">${landmark.name}</strong>
            </div>
            <div style="display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; background: var(--bg-tertiary); color: var(--primary-500); margin-bottom: 8px;">
              ${landmark.category}
            </div>
            <div style="color: var(--text-secondary); font-size: 11px; margin-bottom: 8px; line-height: 1.4;">
              ${landmark.description}
            </div>
            <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 6px; display: flex; justify-content: space-between;">
              <span>Coordinates:</span>
              <code>${landmark.coordinates[0].toFixed(4)}, ${landmark.coordinates[1].toFixed(4)}</code>
            </div>
          </div>
        `);
        marker.addTo(landmarksGroup);
      }

      // Draw Selected Real Origin (A) Marker if present
      if (realOrigin) {
        const originIcon = L.divIcon({
          className: '',
          html: `<div class="custom-node-marker origin" style="width: 32px; height: 32px; font-size: 14px; font-weight: 800; border: 2px solid #ffffff; box-shadow: 0 0 14px rgba(16, 185, 129, 0.8);">A</div>`,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        });
        const originMarker = L.marker([realOrigin.lat, realOrigin.lon], { icon: originIcon, zIndexOffset: 1000 });
        originMarker.bindPopup(`
          <div style="font-family: inherit; font-size: 12px; min-width: 220px;">
            <div style="color: #10b981; font-weight: 700; margin-bottom: 2px;">📍 Selected Origin (A)</div>
            <strong style="font-size: 13px;">${realOrigin.name}</strong>
            <div style="color: var(--text-secondary); font-size: 11px; margin: 4px 0 6px 0;">${realOrigin.displayName}</div>
            <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 4px;">
              WGS84: <code>${realOrigin.lat.toFixed(4)}° N, ${realOrigin.lon.toFixed(4)}° E</code> (${realOrigin.source})
            </div>
          </div>
        `);
        originMarker.addTo(landmarksGroup);
      }

      // Draw Selected Real Destination (B) Marker if present
      if (realDestination) {
        const destIcon = L.divIcon({
          className: '',
          html: `<div class="custom-node-marker destination" style="width: 32px; height: 32px; font-size: 14px; font-weight: 800; border: 2px solid #ffffff; box-shadow: 0 0 14px rgba(37, 99, 235, 0.8);">B</div>`,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        });
        const destMarker = L.marker([realDestination.lat, realDestination.lon], { icon: destIcon, zIndexOffset: 1000 });
        destMarker.bindPopup(`
          <div style="font-family: inherit; font-size: 12px; min-width: 220px;">
            <div style="color: #2563eb; font-weight: 700; margin-bottom: 2px;">📍 Selected Destination (B)</div>
            <strong style="font-size: 13px;">${realDestination.name}</strong>
            <div style="color: var(--text-secondary); font-size: 11px; margin: 4px 0 6px 0;">${realDestination.displayName}</div>
            <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 4px;">
              WGS84: <code>${realDestination.lat.toFixed(4)}° N, ${realDestination.lon.toFixed(4)}° E</code> (${realDestination.source})
            </div>
          </div>
        `);
        destMarker.addTo(landmarksGroup);
      }

      // Draw Calculated Real Road Route Polyline (Phase 3)
      if (realRouteResponse) {
        const allRoutes = [realRouteResponse.primary_route, ...realRouteResponse.alternative_routes];
        const activeRoute = allRoutes[selectedRealRouteIndex] || realRouteResponse.primary_route;

        // Render alternative routes first (if any) as dashed secondary lines
        if (allRoutes.length > 1) {
          allRoutes.forEach((route, idx) => {
            if (idx === selectedRealRouteIndex) return;
            const altLatLngs: L.LatLngExpression[] = route.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
            const altPolyline = L.polyline(altLatLngs, {
              color: '#38bdf8',
              weight: 4,
              opacity: 0.5,
              dashArray: '6, 8',
            });
            altPolyline.bindPopup(`
              <div style="font-family: inherit; font-size: 12px; min-width: 200px;">
                <div style="color: #38bdf8; font-weight: 700; margin-bottom: 2px;">
                  🛣️ Alternative Route (${idx})
                </div>
                <strong>${route.summary || 'Alternative Corridor'}</strong>
                <div style="margin: 4px 0; color: var(--text-secondary); font-size: 11px;">
                  Distance: <strong>${route.distance_km} km</strong> • Duration: <strong>~${route.duration_minutes} min</strong>
                </div>
                <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 4px;">
                  Standard Routability (OSRM)
                </div>
              </div>
            `);
            altPolyline.addTo(routeGroup);
          });
        }

        // Render selected / primary route with high-contrast emerald stroke
        const activeLatLngs: L.LatLngExpression[] = activeRoute.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
        const activePolyline = L.polyline(activeLatLngs, {
          color: '#10b981',
          weight: 6,
          opacity: 0.9,
          lineJoin: 'round',
          lineCap: 'round',
        });
        activePolyline.bindPopup(`
          <div style="font-family: inherit; font-size: 12px; min-width: 220px;">
            <div style="color: #10b981; font-weight: 700; margin-bottom: 2px;">
              🛣️ ${selectedRealRouteIndex === 0 ? 'Primary Route' : `Alternative Route ${selectedRealRouteIndex}`}
            </div>
            <strong style="font-size: 13px;">${activeRoute.summary || 'Direct Road Route'}</strong>
            <div style="margin: 6px 0; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
              <div>
                <span style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">DISTANCE</span>
                <div style="font-weight: 700; color: #10b981; font-size: 14px;">${activeRoute.distance_km} km</div>
              </div>
              <div>
                <span style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">EST. DURATION</span>
                <div style="font-weight: 700; color: #38bdf8; font-size: 14px;">~${activeRoute.duration_minutes} min</div>
              </div>
            </div>
            <div style="font-size: 10px; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 4px;">
              Standard Routability (${realRouteResponse.provider.toUpperCase()} Driving)
            </div>
          </div>
        `);
        activePolyline.addTo(routeGroup);

        // Fit map viewport to encompass the calculated road route polyline
        map.fitBounds(activePolyline.getBounds(), { padding: [50, 50] });
      } else if (realOrigin && realDestination) {
        // Fit map viewport to encompass origin and destination points
        const bounds = L.latLngBounds(
          [realOrigin.lat, realOrigin.lon],
          [realDestination.lat, realDestination.lon]
        );
        map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });
      }

      return;
    }

    // ==========================================
    // MODE 2: Synthetic Demo Network Mode (Sector 7)
    // ==========================================
    if (!networkData) return;

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
      const segId = inc.primary_segment_id;
      const feature = networkData.features.find((f) => f.properties.id === segId);
      if (feature && feature.geometry.coordinates.length > 0) {
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
    mapMode,
    networkData,
    roadStates,
    incidents,
    selectedSegmentId,
    originNode,
    destinationNode,
    activeSimulation,
    pickMode,
    realOrigin,
    realDestination,
    realRouteResponse,
    selectedRealRouteIndex,
    setOriginNode,
    setDestinationNode,
    setPickMode,
    setSelectedSegmentId,
  ]);

  // Re-run layer updates when dependencies change
  useEffect(() => {
    renderLayers();
  }, [renderLayers]);

  // Recenter handler
  const handleRecenter = () => {
    if (!mapInstanceRef.current) return;
    if (mapMode === 'real_world') {
      mapInstanceRef.current.setView(MANGALURU_CENTER, MANGALURU_DEFAULT_ZOOM);
    } else {
      mapInstanceRef.current.setView(SECTOR_7_CENTER, SECTOR_7_DEFAULT_ZOOM);
    }
  };

  // Retry tile loading
  const handleRetryTiles = () => {
    if (!tileLayerRef.current) return;
    setTileError(false);
    const provider = theme === 'dark' ? TILE_PROVIDERS.cartoDarkMatter : TILE_PROVIDERS.cartoVoyager;
    tileLayerRef.current.setUrl(provider.url);
    tileLayerRef.current.redraw();
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', flex: 1, overflow: 'hidden' }}>
      {/* Top Floating Controls Bar */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'var(--bg-surface)',
          padding: '6px 10px',
          borderRadius: 'var(--radius-full)',
          boxShadow: 'var(--shadow-lg)',
          border: '1px solid var(--border-medium)',
          backdropFilter: 'blur(12px)',
        }}
      >
        {/* Real-World Journey Planner Toggle */}
        <button
          id="btn-mode-real-world"
          type="button"
          onClick={() => setMapMode('real_world')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 14px',
            borderRadius: 'var(--radius-full)',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            background: mapMode === 'real_world' ? 'var(--primary-600)' : 'transparent',
            color: mapMode === 'real_world' ? '#ffffff' : 'var(--text-secondary)',
            border: 'none',
          }}
        >
          <Globe size={14} />
          <span>Real-World Journey Planner</span>
          <span
            style={{
              fontSize: '10px',
              padding: '1px 6px',
              borderRadius: '4px',
              background: mapMode === 'real_world' ? 'rgba(255,255,255,0.25)' : 'var(--bg-tertiary)',
              color: mapMode === 'real_world' ? '#ffffff' : 'var(--text-muted)',
              fontWeight: 700,
            }}
          >
            Default
          </span>
        </button>

        {/* Synthetic Demo Network Toggle */}
        <button
          id="btn-mode-synthetic"
          type="button"
          onClick={() => setMapMode('synthetic_demo')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 14px',
            borderRadius: 'var(--radius-full)',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            background: mapMode === 'synthetic_demo' ? 'var(--primary-600)' : 'transparent',
            color: mapMode === 'synthetic_demo' ? '#ffffff' : 'var(--text-secondary)',
            border: 'none',
          }}
        >
          <FlaskConical size={14} />
          <span>Synthetic Demo Network</span>
          <span
            style={{
              fontSize: '10px',
              padding: '1px 6px',
              borderRadius: '4px',
              background: mapMode === 'synthetic_demo' ? 'rgba(255,255,255,0.25)' : 'var(--bg-tertiary)',
              color: mapMode === 'synthetic_demo' ? '#ffffff' : 'var(--text-muted)',
              fontWeight: 700,
            }}
          >
            Sector 7
          </span>
        </button>

        <div style={{ width: '1px', height: '18px', background: 'var(--border-medium)', margin: '0 2px' }} />

        {/* Recenter Button */}
        <button
          id="btn-recenter-map"
          type="button"
          onClick={handleRecenter}
          title={mapMode === 'real_world' ? 'Recenter on Mangaluru' : 'Recenter on Sector 7'}
          className="btn btn-ghost btn-icon"
          style={{ padding: '6px', borderRadius: '50%' }}
        >
          <RotateCcw size={14} />
        </button>
      </div>

      {/* Pick Mode Banner */}
      {pickMode && (
        <div
          style={{
            position: 'absolute',
            top: '70px',
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

      {/* Tile Fallback Notice with Retry Button */}
      {tileError && (
        <div
          style={{
            position: 'absolute',
            top: '70px',
            right: '20px',
            zIndex: 1000,
            background: 'var(--status-amber-bg)',
            border: '1px solid var(--status-amber-border)',
            color: 'var(--status-amber)',
            padding: '8px 14px',
            borderRadius: 'var(--radius-md)',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <span>Offline map mode: tile server unreachable, displaying vector road network directly.</span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleRetryTiles}
            style={{ padding: '2px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <RefreshCw size={11} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && mapMode === 'synthetic_demo' && !networkData && (
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

      {/* Segment Details Inspector Drawer (Synthetic Mode) */}
      {selectedSegmentId && mapMode === 'synthetic_demo' && (
        <SegmentDetailsPanel
          segmentId={selectedSegmentId}
          onClose={() => setSelectedSegmentId(null)}
        />
      )}
    </div>
  );
};
