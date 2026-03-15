import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchApi, createWebSocket } from '../../api/client';

describe('fetchApi', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returns parsed JSON on success', async () => {
    const data = { foo: 'bar' };
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(data),
    } as Response);

    const result = await fetchApi('/api/test');
    expect(result).toEqual(data);
    expect(fetch).toHaveBeenCalledWith('/api/test');
  });

  it('throws on non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    } as Response);

    await expect(fetchApi('/api/missing')).rejects.toThrow('API error: 404 Not Found');
  });
});

describe('createWebSocket', () => {
  it('constructs websocket URL and parses messages', () => {
    const onMessage = vi.fn();
    const mockWs = {
      onmessage: null as any,
      onerror: null as any,
    };

    vi.spyOn(globalThis, 'WebSocket').mockImplementation(() => mockWs as any);

    // jsdom sets location.protocol to 'http:' by default
    const ws = createWebSocket('/ws/test', onMessage);

    expect(ws).toBe(mockWs);
    expect(WebSocket).toHaveBeenCalledWith(expect.stringContaining('/ws/test'));

    // Simulate message
    mockWs.onmessage({ data: JSON.stringify({ type: 'ping' }) } as MessageEvent);
    expect(onMessage).toHaveBeenCalledWith({ type: 'ping' });
  });

  it('handles malformed messages without throwing', () => {
    const onMessage = vi.fn();
    const mockWs = { onmessage: null as any, onerror: null as any };
    vi.spyOn(globalThis, 'WebSocket').mockImplementation(() => mockWs as any);

    createWebSocket('/ws/test', onMessage);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    // Simulate malformed message
    mockWs.onmessage({ data: 'not json' } as MessageEvent);
    expect(onMessage).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalledWith('Failed to parse WebSocket message');
  });

  it('logs warning on websocket error', () => {
    const mockWs = { onmessage: null as any, onerror: null as any };
    vi.spyOn(globalThis, 'WebSocket').mockImplementation(() => mockWs as any);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    createWebSocket('/ws/test', vi.fn());
    mockWs.onerror();
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('WebSocket error'));
  });
});
