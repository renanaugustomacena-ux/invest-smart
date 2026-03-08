import { create } from 'zustand';
import type { ServiceHealth, SystemStatus } from '../api/types';

interface SystemState {
  status: SystemStatus | null;
  services: ServiceHealth[];
  wsConnected: boolean;

  setStatus: (s: SystemStatus) => void;
  setServices: (s: ServiceHealth[]) => void;
  setWsConnected: (c: boolean) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  status: null,
  services: [],
  wsConnected: false,

  setStatus: (s) => set({ status: s, services: s.services }),
  setServices: (s) => set({ services: s }),
  setWsConnected: (c) => set({ wsConnected: c }),
}));
