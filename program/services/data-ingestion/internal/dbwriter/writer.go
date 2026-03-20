// Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
// Licensed under Proprietary License. See LICENSE file in the project root.

// Package dbwriter persiste i dati di mercato su TimescaleDB.
//
// Il DBWriter implementa un pattern di batch writing con buffer circolare
// per massimizzare il throughput e minimizzare la latenza delle query.
// Utilizza il protocollo COPY di PostgreSQL per inserimenti bulk efficienti.
//
// Architettura:
//   - TickBuffer: Ring buffer thread-safe per accumulare tick
//   - BarBuffer: Buffer per candele OHLCV aggregate
//   - Worker pool: Goroutine dedicate per flush asincrono
//   - Connection pool: pgxpool per connessioni riutilizzabili
package dbwriter

import (
	"context"
	"fmt"
	"net/url"
	"sync"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/moneymaker-v1/services/data-ingestion/internal/normalizer"
	"github.com/shopspring/decimal"
	"go.uber.org/zap"
)

// redactDSN masks the password in a PostgreSQL connection string for safe logging.
func redactDSN(dsn string) string {
	u, err := url.Parse(dsn)
	if err != nil {
		return "[unparseable DSN]"
	}
	if u.User != nil {
		u.User = url.UserPassword(u.User.Username(), "***")
	}
	return u.String()
}

// Config contiene i parametri di configurazione per il DBWriter.
type Config struct {
	// DSN è la stringa di connessione PostgreSQL.
	// Formato: postgres://user:password@host:port/database
	DSN string

	// BatchSize è il numero di record da accumulare prima del flush.
	BatchSize int

	// FlushInterval è l'intervallo massimo tra i flush.
	FlushInterval time.Duration

	// WorkerCount è il numero di goroutine writer.
	WorkerCount int

	// TicksTable è il nome della tabella per i tick.
	TicksTable string

	// BarsTable è il nome della tabella per le candele OHLCV.
	BarsTable string

	// Enabled abilita/disabilita la persistenza.
	Enabled bool
}

// DefaultConfig restituisce la configurazione di default.
func DefaultConfig() Config {
	return Config{
		BatchSize:     1000,
		FlushInterval: 5 * time.Second,
		WorkerCount:   2,
		TicksTable:    "market_ticks",
		BarsTable:     "ohlcv_bars",
		Enabled:       true,
	}
}

// TickRecord rappresenta un tick pronto per l'inserimento nel database.
type TickRecord struct {
	Time      time.Time
	Symbol    string
	Bid       decimal.Decimal
	Ask       decimal.Decimal
	LastPrice decimal.Decimal
	Volume    decimal.Decimal
	Spread    decimal.Decimal
	Source    string
	Flags     int
}

// BarRecord rappresenta una candela pronta per l'inserimento nel database.
type BarRecord struct {
	Time      time.Time
	Symbol    string
	Timeframe string
	Open      decimal.Decimal
	High      decimal.Decimal
	Low       decimal.Decimal
	Close     decimal.Decimal
	Volume    decimal.Decimal
	TickCount int
	SpreadAvg decimal.Decimal
	Source    string
}

// DBWriter gestisce la persistenza dei dati di mercato su TimescaleDB.
type DBWriter struct {
	pool   *pgxpool.Pool
	config Config
	logger *zap.Logger

	tickBuffer *TickBuffer
	barBuffer  *BarBuffer

	// Canali per coordinazione worker
	tickFlushCh chan []TickRecord
	barFlushCh  chan []BarRecord
	stopCh      chan struct{}
	wg          sync.WaitGroup

	// Metriche
	metrics *Metrics
}

// New crea un nuovo DBWriter con la configurazione specificata.
func New(ctx context.Context, cfg Config, logger *zap.Logger) (*DBWriter, error) {
	if !cfg.Enabled {
		logger.Info("DBWriter disabled by configuration")
		return &DBWriter{
			config:  cfg,
			logger:  logger,
			metrics: NewMetrics(),
		}, nil
	}

	if cfg.DSN == "" {
		return nil, fmt.Errorf("dbwriter: DSN is required")
	}

	// Configura il pool di connessioni
	poolConfig, err := pgxpool.ParseConfig(cfg.DSN)
	if err != nil {
		return nil, fmt.Errorf("dbwriter: invalid DSN (%s): %w", redactDSN(cfg.DSN), err)
	}

	// Ottimizzazioni per bulk insert
	poolConfig.MaxConns = int32(cfg.WorkerCount * 2)
	poolConfig.MinConns = int32(cfg.WorkerCount)
	poolConfig.MaxConnLifetime = 30 * time.Minute
	poolConfig.MaxConnIdleTime = 5 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, poolConfig)
	if err != nil {
		return nil, fmt.Errorf("dbwriter: failed to create connection pool: %w", err)
	}

	// Verifica la connessione
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("dbwriter: failed to ping database: %w", err)
	}

	w := &DBWriter{
		pool:        pool,
		config:      cfg,
		logger:      logger,
		tickBuffer:  NewTickBuffer(cfg.BatchSize),
		barBuffer:   NewBarBuffer(cfg.BatchSize),
		tickFlushCh: make(chan []TickRecord, cfg.WorkerCount),
		barFlushCh:  make(chan []BarRecord, cfg.WorkerCount),
		stopCh:      make(chan struct{}),
		metrics:     NewMetrics(),
	}

	// Avvia i worker
	w.startWorkers()

	// Avvia il timer per il flush periodico
	w.startFlushTimer()

	logger.Info("DBWriter initialized",
		zap.Int("batch_size", cfg.BatchSize),
		zap.Duration("flush_interval", cfg.FlushInterval),
		zap.Int("workers", cfg.WorkerCount),
	)

	return w, nil
}

// startWorkers avvia le goroutine worker per il flush asincrono.
func (w *DBWriter) startWorkers() {
	for i := 0; i < w.config.WorkerCount; i++ {
		w.wg.Add(1)
		go w.tickWorker(i)

		w.wg.Add(1)
		go w.barWorker(i)
	}
}

// tickWorker processa i batch di tick dal canale.
func (w *DBWriter) tickWorker(id int) {
	defer w.wg.Done()

	for {
		select {
		case <-w.stopCh:
			return
		case batch := <-w.tickFlushCh:
			if len(batch) == 0 {
				continue
			}
			start := time.Now()
			if err := w.insertTicks(context.Background(), batch); err != nil {
				w.logger.Error("failed to insert ticks",
					zap.Int("worker", id),
					zap.Int("count", len(batch)),
					zap.Error(err),
				)
				w.metrics.RecordError("tick_insert")
			} else {
				w.metrics.RecordFlush("tick", len(batch), time.Since(start))
				w.logger.Debug("ticks flushed",
					zap.Int("worker", id),
					zap.Int("count", len(batch)),
					zap.Duration("duration", time.Since(start)),
				)
			}
		}
	}
}

// barWorker processa i batch di bar dal canale.
func (w *DBWriter) barWorker(id int) {
	defer w.wg.Done()

	for {
		select {
		case <-w.stopCh:
			return
		case batch := <-w.barFlushCh:
			if len(batch) == 0 {
				continue
			}
			start := time.Now()
			if err := w.insertBars(context.Background(), batch); err != nil {
				w.logger.Error("failed to insert bars",
					zap.Int("worker", id),
					zap.Int("count", len(batch)),
					zap.Error(err),
				)
				w.metrics.RecordError("bar_insert")
			} else {
				w.metrics.RecordFlush("bar", len(batch), time.Since(start))
				w.logger.Debug("bars flushed",
					zap.Int("worker", id),
					zap.Int("count", len(batch)),
					zap.Duration("duration", time.Since(start)),
				)
			}
		}
	}
}

// startFlushTimer avvia il timer per il flush periodico dei buffer.
func (w *DBWriter) startFlushTimer() {
	w.wg.Add(1)
	go func() {
		defer w.wg.Done()
		ticker := time.NewTicker(w.config.FlushInterval)
		defer ticker.Stop()

		for {
			select {
			case <-w.stopCh:
				return
			case <-ticker.C:
				w.FlushTicks()
				w.FlushBars()
			}
		}
	}()
}

// WriteTick converte un NormalizedTick e lo aggiunge al buffer.
// Quando il buffer raggiunge BatchSize, viene automaticamente flushato.
func (w *DBWriter) WriteTick(tick *normalizer.NormalizedTick) {
	if !w.config.Enabled || tick == nil {
		return
	}

	// Estrai bid/ask da Extra se presenti
	bid := decimal.Zero
	ask := decimal.Zero
	if tick.Extra != nil {
		if bidStr, ok := tick.Extra["bid"].(string); ok {
			bid, _ = decimal.NewFromString(bidStr)
		}
		if askStr, ok := tick.Extra["ask"].(string); ok {
			ask, _ = decimal.NewFromString(askStr)
		}
	}

	spread := ask.Sub(bid)

	record := TickRecord{
		Time:      time.Unix(0, tick.NormalizeTimestamp).UTC(),
		Symbol:    tick.Symbol,
		Bid:       bid,
		Ask:       ask,
		LastPrice: tick.Price,
		Volume:    tick.Quantity,
		Spread:    spread,
		Source:    tick.Exchange,
		Flags:     0,
	}

	w.metrics.RecordTick()

	if batch := w.tickBuffer.Add(record); batch != nil {
		select {
		case w.tickFlushCh <- batch:
		default:
			// Canale pieno, flush sincrono come fallback
			w.logger.Warn("tick flush channel full, performing sync flush")
			if err := w.insertTicks(context.Background(), batch); err != nil {
				w.logger.Error("sync tick flush failed", zap.Error(err))
			}
		}
	}
}

// WriteBar aggiunge una candela OHLCV al buffer.
func (w *DBWriter) WriteBar(symbol string, timeframe string, openTime time.Time,
	open, high, low, close, volume decimal.Decimal, tickCount int, source string) {

	if !w.config.Enabled {
		return
	}

	record := BarRecord{
		Time:      openTime.UTC(),
		Symbol:    symbol,
		Timeframe: timeframe,
		Open:      open,
		High:      high,
		Low:       low,
		Close:     close,
		Volume:    volume,
		TickCount: tickCount,
		SpreadAvg: decimal.Zero, // TODO: requires bid/ask data from connector
		Source:    source,
	}

	w.metrics.RecordBar()

	if batch := w.barBuffer.Add(record); batch != nil {
		select {
		case w.barFlushCh <- batch:
		default:
			w.logger.Warn("bar flush channel full, performing sync flush")
			if err := w.insertBars(context.Background(), batch); err != nil {
				w.logger.Error("sync bar flush failed", zap.Error(err))
			}
		}
	}
}

// FlushTicks forza il flush del buffer dei tick.
func (w *DBWriter) FlushTicks() {
	if !w.config.Enabled {
		return
	}

	batch := w.tickBuffer.Flush()
	if len(batch) > 0 {
		select {
		case w.tickFlushCh <- batch:
		default:
			if err := w.insertTicks(context.Background(), batch); err != nil {
				w.logger.Error("forced tick flush failed", zap.Error(err))
			}
		}
	}
}

// FlushBars forza il flush del buffer delle bar.
func (w *DBWriter) FlushBars() {
	if !w.config.Enabled {
		return
	}

	batch := w.barBuffer.Flush()
	if len(batch) > 0 {
		select {
		case w.barFlushCh <- batch:
		default:
			if err := w.insertBars(context.Background(), batch); err != nil {
				w.logger.Error("forced bar flush failed", zap.Error(err))
			}
		}
	}
}

// Ping verifica che la connessione al database sia attiva.
func (w *DBWriter) Ping() error {
	if !w.config.Enabled || w.pool == nil {
		return nil
	}
	return w.pool.Ping(context.Background())
}

// Close chiude il DBWriter, flushando tutti i buffer pendenti.
func (w *DBWriter) Close() error {
	if !w.config.Enabled {
		return nil
	}

	w.logger.Info("DBWriter shutting down, flushing remaining data...")

	// Segnala lo stop ai worker
	close(w.stopCh)

	// Flush finale sincrono
	tickBatch := w.tickBuffer.Flush()
	if len(tickBatch) > 0 {
		if err := w.insertTicks(context.Background(), tickBatch); err != nil {
			w.logger.Error("final tick flush failed", zap.Error(err))
		}
	}

	barBatch := w.barBuffer.Flush()
	if len(barBatch) > 0 {
		if err := w.insertBars(context.Background(), barBatch); err != nil {
			w.logger.Error("final bar flush failed", zap.Error(err))
		}
	}

	// Attendi che i worker terminino
	w.wg.Wait()

	// Chiudi il pool
	if w.pool != nil {
		w.pool.Close()
	}

	w.logger.Info("DBWriter shutdown complete",
		zap.Int("final_ticks", len(tickBatch)),
		zap.Int("final_bars", len(barBatch)),
	)

	return nil
}

// Stats restituisce le statistiche correnti del DBWriter.
func (w *DBWriter) Stats() map[string]interface{} {
	return w.metrics.Stats()
}
