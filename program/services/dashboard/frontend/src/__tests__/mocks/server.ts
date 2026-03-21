/**
 * MSW test server — intercepts fetch() at the network layer.
 *
 * Usage in tests:
 *   import { server } from '../mocks/server';
 *   import { http, HttpResponse } from 'msw';
 *
 *   // Override a handler for one test:
 *   server.use(
 *     http.get('/api/risk/metrics', () => HttpResponse.json({ error: true }))
 *   );
 */
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
