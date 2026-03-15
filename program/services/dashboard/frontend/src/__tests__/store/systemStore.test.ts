import { describe, it, expect, beforeEach } from 'vitest';
import { useSystemStore } from '../../store/systemStore';
import type { SystemStatus, ServiceHealth } from '../../api/types';

describe('systemStore', () => {
  beforeEach(() => {
    useSystemStore.setState({
      status: null,
      services: [],
      wsConnected: false,
    });
  });

  it('setStatus updates status and services', () => {
    const status: SystemStatus = {
      database: { name: 'postgres', status: 'connected' },
      redis: { name: 'redis', status: 'connected' },
      services: [
        { name: 'brain', status: 'connected', latency_ms: 10 },
      ],
    };
    useSystemStore.getState().setStatus(status);
    const state = useSystemStore.getState();
    expect(state.status).toEqual(status);
    expect(state.services).toEqual(status.services);
  });

  it('setServices updates services list', () => {
    const services: ServiceHealth[] = [
      { name: 'mt5-bridge', status: 'disconnected' },
    ];
    useSystemStore.getState().setServices(services);
    expect(useSystemStore.getState().services).toEqual(services);
  });

  it('setWsConnected updates connection state', () => {
    useSystemStore.getState().setWsConnected(true);
    expect(useSystemStore.getState().wsConnected).toBe(true);
    useSystemStore.getState().setWsConnected(false);
    expect(useSystemStore.getState().wsConnected).toBe(false);
  });
});
