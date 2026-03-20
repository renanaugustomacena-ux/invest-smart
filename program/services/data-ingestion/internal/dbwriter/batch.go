// Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
// Licensed under Proprietary License. See LICENSE file in the project root.

// Package dbwriter - batch.go
//
// Implementa inserimenti bulk efficienti usando il protocollo COPY di PostgreSQL.
// Il protocollo COPY è significativamente più veloce rispetto a INSERT multipli
// per grandi volumi di dati.
package dbwriter

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
	"go.uber.org/zap"
)

// insertTicks inserisce un batch di tick usando COPY.
func (w *DBWriter) insertTicks(ctx context.Context, records []TickRecord) error {
	if len(records) == 0 {
		return nil
	}

	// Prepara le righe per COPY
	rows := make([][]interface{}, len(records))
	for i, r := range records {
		rows[i] = []interface{}{
			r.Time,
			r.Symbol,
			r.Bid.String(),
			r.Ask.String(),
			r.LastPrice.String(),
			r.Volume.String(),
			r.Spread.String(),
			r.Source,
			r.Flags,
		}
	}

	// Esegue COPY FROM
	copyCount, err := w.pool.CopyFrom(
		ctx,
		pgx.Identifier{w.config.TicksTable},
		[]string{"time", "symbol", "bid", "ask", "last_price", "volume", "spread", "source", "flags"},
		pgx.CopyFromRows(rows),
	)
	if err != nil {
		return fmt.Errorf("copy ticks failed: %w", err)
	}

	if copyCount != int64(len(records)) {
		w.logger.Warn("tick copy count mismatch",
			zap.Int64("expected", int64(len(records))),
			zap.Int64("actual", copyCount),
		)
	}

	return nil
}

// insertBars inserisce un batch di bar usando COPY.
func (w *DBWriter) insertBars(ctx context.Context, records []BarRecord) error {
	if len(records) == 0 {
		return nil
	}

	// Prepara le righe per COPY
	rows := make([][]interface{}, len(records))
	for i, r := range records {
		rows[i] = []interface{}{
			r.Time,
			r.Symbol,
			r.Timeframe,
			r.Open.String(),
			r.High.String(),
			r.Low.String(),
			r.Close.String(),
			r.Volume.String(),
			r.TickCount,
			r.SpreadAvg.String(),
			r.Source,
		}
	}

	// Esegue COPY FROM
	copyCount, err := w.pool.CopyFrom(
		ctx,
		pgx.Identifier{w.config.BarsTable},
		[]string{"time", "symbol", "timeframe", "open", "high", "low", "close", "volume", "tick_count", "spread_avg", "source"},
		pgx.CopyFromRows(rows),
	)
	if err != nil {
		return fmt.Errorf("copy bars failed: %w", err)
	}

	if copyCount != int64(len(records)) {
		w.logger.Warn("bar copy count mismatch",
			zap.Int64("expected", int64(len(records))),
			zap.Int64("actual", copyCount),
		)
	}

	return nil
}

// InsertTicksBatch inserisce tick usando INSERT batch come fallback.
// Meno efficiente di COPY ma più resiliente a errori parziali.
func (w *DBWriter) InsertTicksBatch(ctx context.Context, records []TickRecord) error {
	if len(records) == 0 {
		return nil
	}

	batch := &pgx.Batch{}
	sql := fmt.Sprintf(`
		INSERT INTO %s (time, symbol, bid, ask, last_price, volume, spread, source, flags)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		ON CONFLICT DO NOTHING
	`, pgx.Identifier{w.config.TicksTable}.Sanitize())

	for _, r := range records {
		batch.Queue(sql,
			r.Time,
			r.Symbol,
			r.Bid.String(),
			r.Ask.String(),
			r.LastPrice.String(),
			r.Volume.String(),
			r.Spread.String(),
			r.Source,
			r.Flags,
		)
	}

	br := w.pool.SendBatch(ctx, batch)
	defer br.Close()

	for range records {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("batch insert tick failed: %w", err)
		}
	}

	return nil
}

// InsertBarsBatch inserisce bar usando INSERT batch come fallback.
func (w *DBWriter) InsertBarsBatch(ctx context.Context, records []BarRecord) error {
	if len(records) == 0 {
		return nil
	}

	batch := &pgx.Batch{}
	sql := fmt.Sprintf(`
		INSERT INTO %s (time, symbol, timeframe, open, high, low, close, volume, tick_count, spread_avg, source)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
		ON CONFLICT DO NOTHING
	`, pgx.Identifier{w.config.BarsTable}.Sanitize())

	for _, r := range records {
		batch.Queue(sql,
			r.Time,
			r.Symbol,
			r.Timeframe,
			r.Open.String(),
			r.High.String(),
			r.Low.String(),
			r.Close.String(),
			r.Volume.String(),
			r.TickCount,
			r.SpreadAvg.String(),
			r.Source,
		)
	}

	br := w.pool.SendBatch(ctx, batch)
	defer br.Close()

	for range records {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("batch insert bar failed: %w", err)
		}
	}

	return nil
}
