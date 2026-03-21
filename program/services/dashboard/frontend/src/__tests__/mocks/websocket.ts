/**
 * FakeWebSocket — a real implementation of the WebSocket interface for testing.
 *
 * This is NOT a mock — it's a purpose-built test double that implements the
 * WebSocket API contract. The useWebSocket hook runs its real code against this.
 *
 * Usage:
 *   const wsManager = installFakeWebSocket();
 *   renderPage();
 *   wsManager.simulateMessage({ type: 'overview', data: {...} });
 *   wsManager.simulateOpen();
 */

export class FakeWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readonly CONNECTING = 0;
  readonly OPEN = 1;
  readonly CLOSING = 2;
  readonly CLOSED = 3;

  url: string;
  readyState: number = FakeWebSocket.CONNECTING;
  protocol = '';
  extensions = '';
  bufferedAmount = 0;
  binaryType: BinaryType = 'blob';

  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  private _closed = false;

  constructor(url: string, _protocols?: string | string[]) {
    this.url = url;
  }

  send(_data: string | ArrayBufferLike | Blob | ArrayBufferView): void {
    // No-op — server doesn't need to receive test data
  }

  close(_code?: number, _reason?: string): void {
    if (this._closed) return;
    this._closed = true;
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code: _code ?? 1000, reason: _reason ?? '', wasClean: true } as CloseEvent);
  }

  addEventListener(_type: string, _listener: EventListener): void {}
  removeEventListener(_type: string, _listener: EventListener): void {}
  dispatchEvent(_event: Event): boolean { return true; }

  // ─── Test helpers ──────────────────────────────────────────────────

  /** Simulate the server opening the connection */
  triggerOpen(): void {
    this.readyState = FakeWebSocket.OPEN;
    this.onopen?.({} as Event);
  }

  /** Simulate a message from the server */
  triggerMessage(data: unknown): void {
    const json = typeof data === 'string' ? data : JSON.stringify(data);
    this.onmessage?.({ data: json } as MessageEvent);
  }

  /** Simulate an error */
  triggerError(): void {
    this.onerror?.({} as Event);
  }

  /** Simulate the server closing the connection */
  triggerClose(code = 1000, reason = ''): void {
    this.readyState = FakeWebSocket.CLOSED;
    this.onclose?.({ code, reason, wasClean: true } as CloseEvent);
  }
}

/**
 * WebSocket manager — tracks all FakeWebSocket instances created during a test.
 */
export interface WebSocketManager {
  /** All WebSocket instances created so far */
  instances: FakeWebSocket[];
  /** The most recent WebSocket instance */
  latest: () => FakeWebSocket | undefined;
  /** Simulate open on the latest instance */
  simulateOpen: () => void;
  /** Simulate a JSON message on the latest instance */
  simulateMessage: (data: unknown) => void;
  /** Clean up and restore globalThis.WebSocket */
  cleanup: () => void;
}

/**
 * Install FakeWebSocket as the global WebSocket constructor.
 * Returns a manager for controlling WebSocket behavior in tests.
 */
export function installFakeWebSocket(): WebSocketManager {
  const instances: FakeWebSocket[] = [];
  const originalWS = globalThis.WebSocket;

  // Replace globalThis.WebSocket with a constructor that tracks instances.
  // Use Object.defineProperty because jsdom marks WebSocket as non-writable.
  const fakeConstructor = function (url: string, protocols?: string | string[]) {
    const ws = new FakeWebSocket(url, protocols);
    instances.push(ws);
    return ws;
  } as unknown as typeof WebSocket;

  // Copy static properties
  (fakeConstructor as any).CONNECTING = 0;
  (fakeConstructor as any).OPEN = 1;
  (fakeConstructor as any).CLOSING = 2;
  (fakeConstructor as any).CLOSED = 3;

  Object.defineProperty(globalThis, 'WebSocket', {
    value: fakeConstructor,
    writable: true,
    configurable: true,
  });

  return {
    instances,
    latest: () => instances[instances.length - 1],
    simulateOpen: () => {
      const ws = instances[instances.length - 1];
      ws?.triggerOpen();
    },
    simulateMessage: (data: unknown) => {
      const ws = instances[instances.length - 1];
      ws?.triggerMessage(data);
    },
    cleanup: () => {
      Object.defineProperty(globalThis, 'WebSocket', {
        value: originalWS,
        writable: true,
        configurable: true,
      });
      instances.length = 0;
    },
  };
}
