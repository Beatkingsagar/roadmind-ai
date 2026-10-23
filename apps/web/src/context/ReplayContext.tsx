import React, { createContext, useContext, useState } from 'react';
import { DEMO_PRESETS } from '../utils/constants';

interface ReplayContextType {
  replayTime: string | null;
  isReplay: boolean;
  activePresetIndex: number | null;
  setReplayTime: (time: string | null) => void;
  applyPreset: (index: number) => void;
  resetToLive: () => void;
}

const ReplayContext = createContext<ReplayContextType | undefined>(undefined);

export const ReplayProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Default to the first demo preset (Corridor Peak Incident) so the evaluator immediately sees real traffic data
  const [replayTime, setReplayTimeState] = useState<string | null>(DEMO_PRESETS[0].timestamp);
  const [activePresetIndex, setActivePresetIndex] = useState<number | null>(0);

  const setReplayTime = (time: string | null) => {
    setReplayTimeState(time);
    if (!time) {
      setActivePresetIndex(null);
    } else {
      const matchIdx = DEMO_PRESETS.findIndex((p) => p.timestamp === time);
      setActivePresetIndex(matchIdx >= 0 ? matchIdx : null);
    }
  };

  const applyPreset = (index: number) => {
    if (index >= 0 && index < DEMO_PRESETS.length) {
      const preset = DEMO_PRESETS[index];
      setReplayTimeState(preset.timestamp);
      setActivePresetIndex(index);
    }
  };

  const resetToLive = () => {
    setReplayTimeState(null);
    setActivePresetIndex(null);
  };

  return (
    <ReplayContext.Provider
      value={{
        replayTime,
        isReplay: replayTime !== null,
        activePresetIndex,
        setReplayTime,
        applyPreset,
        resetToLive,
      }}
    >
      {children}
    </ReplayContext.Provider>
  );
};

export function useReplay(): ReplayContextType {
  const context = useContext(ReplayContext);
  if (!context) {
    throw new Error('useReplay must be used within a ReplayProvider');
  }
  return context;
}
