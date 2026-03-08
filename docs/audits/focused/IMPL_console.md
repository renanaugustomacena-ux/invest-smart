# IMPL_console: Task Aperte

**Ultimo aggiornamento:** 2026-02-28
**Console:** `program/services/console/moneymaker_console.py` (1,539 LOC, 65 comandi) — COMPLETATO

---

## Blocking: Proto Definitions per gRPC

I 30+ comandi console che interagiscono con i servizi hanno fallback placeholder.
Per funzionare realmente servono le definizioni RPC nei proto file:

### algo-engine (`program/shared/proto/algo_engine.proto`)
- `StartTraining`, `StopTraining`, `PauseTraining`, `ResumeTraining`
- `GetStatus`, `RunEvaluation`, `SaveCheckpoint`, `GetModelInfo`

### data-ingestion (`program/shared/proto/data_ingestion.proto`)
- `Start`, `Stop`, `GetStatus`
- `ListSymbols`, `AddSymbol`, `RemoveSymbol`, `Backfill`

### mt5-bridge (`program/shared/proto/mt5_bridge.proto`)
- `Connect`, `Disconnect`, `GetStatus`
- `GetPositions`, `GetHistory`, `CloseAll`, `GetSpread`

## Blocking: gRPC Health Check Standard

Implementare `grpc.health.v1.Health` su tutti e 3 i servizi per StatusPoller.
