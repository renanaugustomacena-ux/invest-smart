# MONEYMAKER Dashboard (Frontend)

The **Dashboard Frontend** is the real-time monitoring and visualization interface for the MONEYMAKER trading ecosystem. Built with React, TypeScript, and Vite, it provides live views of system health, trading performance, risk metrics, and market data.

---

## Features

- **System Overview**: Service status, uptime, active positions
- **Trading Monitor**: Signal history, open/closed trades, P&L tracking
- **Risk Dashboard**: Drawdown gauges, kill switch status, spiral protection state
- **Market Data**: Live prices, regime classification, indicator values
- **Strategy Performance**: Per-strategy win rates, attribution charts
- **WebSocket Streams**: Real-time updates without polling

---

## Source Layout

```
src/
├── api/            # Backend API client and WebSocket handlers
├── components/     # Reusable UI components (charts, gauges, tables)
├── pages/          # Route-level page components
├── hooks/          # Custom React hooks
├── types/          # TypeScript type definitions
├── utils/          # Helper functions
├── App.tsx         # Root component and router
└── main.tsx        # Entry point
```

---

## Development

### Prerequisites

- Node.js 18+ and npm

### Setup

```bash
cd program/services/dashboard/frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:5173` with hot module replacement.

### Build

```bash
npm run build
```

Output goes to `dist/` and is served by the backend FastAPI application in production.

### Lint

```bash
npm run lint
```

---

## Backend Integration

The frontend communicates with the Dashboard backend (FastAPI) at the configured API base URL. In Docker, the backend serves the built frontend as static files on port 8888.

API routes: `/api/overview`, `/api/trading`, `/api/risk`, `/api/market-data`, `/api/strategy`, `/api/system`

WebSocket: `/ws/stream` for real-time metric updates.
