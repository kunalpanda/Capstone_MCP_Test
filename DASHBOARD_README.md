# Dashboard Architecture

This directory contains the real-time dashboard for the Agentic AI Core DevOps Automation system.

## Directory Structure

```
Capstone_MCP_Test/
├── backend/                      # WebSocket server
│   ├── websocket_server.py      # FastAPI WebSocket server
│   ├── event_emitter.py         # Event emitter for orchestrator
│   └── requirements.txt         # Backend dependencies
│
├── frontend/                     # React dashboard
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/          # React components
│   │   │   ├── Header.tsx
│   │   │   ├── OutputStream.tsx
│   │   │   ├── StatePanel.tsx
│   │   │   ├── DetailedView.tsx
│   │   │   └── shared/
│   │   │       ├── MessageCard.tsx
│   │   │       └── MetricCard.tsx
│   │   ├── hooks/               # Custom React hooks
│   │   │   ├── useWebSocket.ts
│   │   │   └── useOrchestratorState.ts
│   │   ├── services/            # Business logic
│   │   │   ├── websocket.ts
│   │   │   └── types.ts
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── index.tsx
│   │   └── index.css
│   ├── package.json
│   └── tsconfig.json
│
├── orchestrator/                 # Existing orchestrator (to be modified)
│   └── Orchestrator.py          # Will add EventEmitter integration
│
└── dashboard_mockup.html        # Static mockup for reference
```

## Component Responsibilities

### Backend
- **websocket_server.py**: Handles WebSocket connections and broadcasts events
- **event_emitter.py**: Sends events from orchestrator to WebSocket server

### Frontend
- **Header**: Status indicator, iteration counter, elapsed time
- **OutputStream**: Live feed of Claude's actions and tool calls
- **StatePanel**: Repository info, test metrics, build status, recent actions
- **DetailedView**: Tabbed view for logs, test results, file changes, summary

## Data Flow

```
Orchestrator → EventEmitter → WebSocket Server → React Dashboard
```

## Setup Instructions

### Backend
```bash
cd backend
pip install -r requirements.txt
python websocket_server.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Orchestrator
Run with event emission enabled (will be configured after implementation)

## Next Steps
1. Implement WebSocket server
2. Add event emission to orchestrator
3. Build React components
4. Connect frontend to WebSocket
5. Test end-to-end integration
