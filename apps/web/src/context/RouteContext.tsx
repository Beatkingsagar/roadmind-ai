import React, { createContext, useContext, useState, useCallback } from 'react';
import { api, ApiError } from '../api/client';
import type { RealPlace, SimulationRunResponse } from '../api/types';
import type { MapMode } from '../utils/constants';
import { useReplay } from './ReplayContext';

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

  // Real-World Journey Planner State (Phase 2)
  realOrigin: RealPlace | null;
  realDestination: RealPlace | null;
  setRealOrigin: (place: RealPlace | null) => void;
  setRealDestination: (place: RealPlace | null) => void;
  swapRealPlaces: () => void;
}

const RouteContext = createContext<RouteContextType | undefined>(undefined);

export const RouteProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { replayTime } = useReplay();
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

  const swapNodes = () => {
    setOriginNode(destinationNode);
    setDestinationNode(originNode);
  };

  const swapRealPlaces = () => {
    const prevOrigin = realOrigin;
    setRealOrigin(realDestination);
    setRealDestination(prevOrigin);
  };

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
  }, [originNode, destinationNode, replayTime]);

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
