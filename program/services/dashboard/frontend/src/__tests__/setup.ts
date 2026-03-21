import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { server } from './mocks/server';

// Start MSW server before all tests — intercepts fetch() at the network layer.
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));

// Reset any per-test handler overrides after each test.
afterEach(() => server.resetHandlers());

// Clean up after all tests.
afterAll(() => server.close());
