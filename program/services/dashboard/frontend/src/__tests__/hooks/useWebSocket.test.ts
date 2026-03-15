import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '../../hooks/useWebSocket';

describe('useWebSocket', () => {
  let mockWs: any;

  beforeEach(() => {
    mockWs = {
      onopen: null as any,
      onmessage: null as any,
      onclose: null as any,
      onerror: null as any,
      close: vi.fn(),
      readyState: 0,
    };
    vi.spyOn(globalThis, 'WebSocket').mockImplementation(() => mockWs as any);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('connects on mount', () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket('/ws/test', onMessage));
    expect(WebSocket).toHaveBeenCalledWith(expect.stringContaining('/ws/test'));
  });

  it('sets connected on open', () => {
    const onMessage = vi.fn();
    const { result } = renderHook(() => useWebSocket('/ws/test', onMessage));

    expect(result.current.connected).toBe(false);
    act(() => { mockWs.onopen?.(); });
    expect(result.current.connected).toBe(true);
  });

  it('parses messages and calls onMessage', () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket('/ws/test', onMessage));

    act(() => { mockWs.onopen?.(); });
    act(() => { mockWs.onmessage?.({ data: JSON.stringify({ type: 'data' }) }); });
    expect(onMessage).toHaveBeenCalledWith({ type: 'data' });
  });

  it('ignores malformed messages', () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket('/ws/test', onMessage));

    act(() => { mockWs.onmessage?.({ data: 'not json' }); });
    expect(onMessage).not.toHaveBeenCalled();
  });

  it('does not connect when enabled=false', () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket('/ws/test', onMessage, false));
    expect(WebSocket).not.toHaveBeenCalled();
  });

  it('cleans up on unmount', () => {
    const onMessage = vi.fn();
    const { unmount } = renderHook(() => useWebSocket('/ws/test', onMessage));
    unmount();
    expect(mockWs.close).toHaveBeenCalled();
  });

  it('reconnects on close with backoff', () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket('/ws/test', onMessage));

    // Simulate close
    act(() => { mockWs.onclose?.(); });

    // After reconnect delay, should create a new WebSocket
    act(() => { vi.advanceTimersByTime(1000); });
    // WebSocket called twice: initial + reconnect
    expect(WebSocket).toHaveBeenCalledTimes(2);
  });

  it('error triggers close which triggers reconnect', () => {
    const onMessage = vi.fn();
    renderHook(() => useWebSocket('/ws/test', onMessage));

    act(() => { mockWs.onerror?.(); });
    expect(mockWs.close).toHaveBeenCalled();
  });
});
