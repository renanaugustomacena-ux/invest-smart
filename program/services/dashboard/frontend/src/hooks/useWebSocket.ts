import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Auto-reconnecting WebSocket hook with exponential backoff.
 *
 * @param path     - WebSocket path (e.g. "/ws/overview")
 * @param onMessage - Callback receiving parsed JSON data
 * @param enabled  - Whether to connect (default true)
 */
export function useWebSocket<T>(
  path: string,
  onMessage: (data: T) => void,
  enabled = true,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelay = useRef(1000);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const onMessageRef = useRef(onMessage);
  const connectRef = useRef<() => void>(() => {});
  const [connected, setConnected] = useState(false);

  // Keep callback ref up-to-date without re-connecting
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (!enabled || !mountedRef.current) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}${path}`);

    ws.onopen = () => {
      if (!mountedRef.current) { ws.close(); return; }
      setConnected(true);
      reconnectDelay.current = 1000; // reset backoff
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        onMessageRef.current(parsed);
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      reconnectTimer.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30_000);
        connectRef.current();
      }, reconnectDelay.current);
    };

    ws.onerror = () => {
      ws.close(); // triggers onclose → reconnect
    };

    wsRef.current = ws;
  }, [path, enabled]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled) connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect, enabled]);

  return { connected };
}
