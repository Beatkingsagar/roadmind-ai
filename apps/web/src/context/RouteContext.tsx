import React, { createContext, useContext, useState, useCallback } from 'react';
import { api, ApiError } from '../api/client';
import type { RealPlace, RealRouteResponse, SimulationRunResponse } from '../api/types';
import type { MapMode } from '../utils/constants';

interface RouteContextType {
  mapMode: MapMode;
  setMapMode: (mode: MapMode) => void;
  originNode: string;
  destinationNode: string;
  setOriginNode: (id: string) => void;
  setDestinationNode: (id: string) => void;
  swapNodes: () => void;
  activeSimulation: SimulationRunResponse | null;
  setActiveSimulation: (sim: SimulationRunResponse | null) => void;
  selectedSegmentId: string | null;
  setSelectedSegmentId: (id: string | null) => void;
  isCalculating: boolean;
  calculateRoute: () => Promise<void>;
  errorMessage: string | null;
  setErrorMessage: (msg: string | null) => void;
  pickMode: 'origin' | 'destination' | null;
  setPickMode: (mode: 'origin' | 'destination' | null) => void;

  // Real-World Journey Planner State (Phase 2 & Phase 3)
  realOrigin: RealPlace | null;
  realDestination: RealPlace | null;
  setRealOrigin: (place: RealPlace | null) => void;
  setRealDestination: (place: RealPlace | null) => void;
  swapRealPlaces: () => void;

  // Real-World Road Routing State (Phase 3)
  realRouteResponse: RealRouteResponse | null;
  selectedRealRouteIndex: number;
  setSelectedRealRouteIndex: (index: number) => void;
  isCalculatingRealRoute: boolean;
  realRouteError: string | null;
  calculateRealRoute: () => Promise<void>;
  clearRealRoute: () => void;
}

const RouteContext = createContext<RouteContextType | undefined>(undefined);

export const RouteProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mapMode, setMapMode] = useState<MapMode>('real_world');
  const [originNode, setOriginNode] = useState<string>('node_origin');
  const [destinationNode, setDestinationNode] = useState<string>('node_destination');
  const [activeSimulation, setActiveSimulation] = useState<SimulationRunResponse | null>(null);
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
  const [isCalculating, setIsCalculating] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pickMode, setPickMode] = useState<'origin' | 'destination' | null>(null);

  // Real-World Journey Planner state: Kundapura & Mangaluru ready
  const [realOrigin, setRealOrigin] = useState<RealPlace | null>(null);
  const [realDestination, setRealDestination] = useState<RealPlace | null>(null);

  // Real-World Road Routing state (Phase 3)
  const [realRouteResponse, setRealRouteResponse] = useState<RealRouteResponse | null>(null);
  const [selectedRealRouteIndex, setSelectedRealRouteIndex] = useState<number>(0);
  const [isCalculatingRealRoute, setIsCalculatingRealRoute] = useState<boolean>(false);
  const [realRouteError, setRealRouteError] = useState<string | null>(null);

  const swapNodes = () => {
    setOriginNode(destinationNode);
    setDestinationNode(originNode);
  };

  const swapRealPlaces = () => {
    const prevOrigin = realOrigin;
    setRealOrigin(realDestination);
    setRealDestination(prevOrigin);
    setRealRouteResponse(null);
    setRealRouteError(null);
  };

  const clearRealRoute = useCallback(() => {
    setRealRouteResponse(null);
    setSelectedRealRouteIndex(0);
    setRealRouteError(null);
  }, []);

  const calculateRoute = useCallback(async () => {
    if (!originNode || !destinationNode) {
      setErrorMessage('Both Origin and Destination must be selected.');
      return;
    }
    if (originNode === destinationNode) {
      setErrorMessage('Origin and Destination cannot be the exact same node.');
      return;
    }

    setIsCalculating(true);
    setErrorMessage(null);

    try {
      // Call compare scenarios: compares baseline, partial slowdown, and full closure
      const result = await api.compareScenarios({
        origin_node: originNode,
        destination_node: destinationNode,
      });
      setActiveSimulation(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to calculate route comparison. Please ensure backend is reachable.');
      }
    } finally {
      setIsCalculating(false);
    }
  }, [originNode, destinationNode]);

  const calculateRealRoute = useCallback(async () => {
    if (!realOrigin || !realDestination) {
      setRealRouteError('Both Origin and Destination places must be selected.');
      return;
    }

    setIsCalculatingRealRoute(true);
    setRealRouteError(null);

    try {
      const res = await api.calculateRealRoute({
        origin_lat: realOrigin.lat,
        origin_lon: realOrigin.lon,
        destination_lat: realDestination.lat,
        destination_lon: realDestination.lon,
        origin_name: realOrigin.name,
        destination_name: realDestination.name,
        alternatives: true,
      });
      setRealRouteResponse(res);
      setSelectedRealRouteIndex(0);
    } catch (err) {
      if (err instanceof ApiError) {
        setRealRouteError(err.message);
      } else {
        setRealRouteError('Failed to calculate road route. Please verify routing provider availability.');
      }
    } finally {
      setIsCalculatingRealRoute(false);
    }
  }, [realOrigin, realDestination]);

  return (
    <RouteContext.Provider
      value={{
        mapMode,
        setMapMode,
        originNode,
        destinationNode,
        setOriginNode,
        setDestinationNode,
        swapNodes,
        activeSimulation,
        setActiveSimulation,
        selectedSegmentId,
        setSelectedSegmentId,
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
      }}
    >
      {children}
    </RouteContext.Provider>
  );
};

export function useRoute(): RouteContextType {
  const context = useContext(RouteContext);
  if (!context) {
    throw new Error('useRoute must be used within a RouteProvider');
  }
  return context;
}
