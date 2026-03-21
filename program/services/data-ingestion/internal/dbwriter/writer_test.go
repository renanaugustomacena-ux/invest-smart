package dbwriter

import (
	"context"
	"testing"
	"time"

	"github.com/moneymaker-v1/services/data-ingestion/internal/normalizer"
	"github.com/shopspring/decimal"
	"go.uber.org/zap"
)

// ---------------------------------------------------------------------------
// redactDSN
// ---------------------------------------------------------------------------

func TestRedactDSNMasksPassword(t *testing.T) {
	dsn := "postgres://user:secretpwd@localhost:5432/mydb"
	result := redactDSN(dsn)
	if result == dsn {
		t.Error("redactDSN should mask the password")
	}
	if containsString(result, "secretpwd") {
		t.Error("redacted DSN still contains the password")
	}
	// url.UserPassword URL-encodes * to %2A, so check for either form
	if !containsString(result, "***") && !containsString(result, "%2A%2A%2A") {
		t.Errorf("redacted DSN should contain *** or %%2A%%2A%%2A, got %q", result)
	}
	if !containsString(result, "user") {
		t.Error("redacted DSN should preserve the username")
	}
}

func TestRedactDSNNoPassword(t *testing.T) {
	dsn := "postgres://user@localhost:5432/mydb"
	result := redactDSN(dsn)
	if !containsString(result, "user") {
		t.Error("redacted DSN should preserve the username")
	}
}

func TestRedactDSNInvalidURL(t *testing.T) {
	result := redactDSN("://not-a-valid-url")
	if result != "[unparseable DSN]" {
		t.Errorf("expected [unparseable DSN], got %q", result)
	}
}

func TestRedactDSNEmptyString(t *testing.T) {
	// Empty string is still a valid URL (relative reference)
	result := redactDSN("")
	// Should not panic
	_ = result
}

// ---------------------------------------------------------------------------
// DefaultConfig
// ---------------------------------------------------------------------------

func TestDefaultConfigValues(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.BatchSize != 1000 {
		t.Errorf("BatchSize = %d, want 1000", cfg.BatchSize)
	}
	if cfg.FlushInterval != 5*time.Second {
		t.Errorf("FlushInterval = %v, want 5s", cfg.FlushInterval)
	}
	if cfg.WorkerCount != 2 {
		t.Errorf("WorkerCount = %d, want 2", cfg.WorkerCount)
	}
	if cfg.TicksTable != "market_ticks" {
		t.Errorf("TicksTable = %q, want market_ticks", cfg.TicksTable)
	}
	if cfg.BarsTable != "ohlcv_bars" {
		t.Errorf("BarsTable = %q, want ohlcv_bars", cfg.BarsTable)
	}
	if !cfg.Enabled {
		t.Error("Enabled should be true by default")
	}
}

// ---------------------------------------------------------------------------
// New — disabled mode
// ---------------------------------------------------------------------------

func TestNewDisabledReturnsWriter(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Enabled = false
	logger := zap.NewNop()

	w, err := New(context.Background(), cfg, logger)
	if err != nil {
		t.Fatalf("New with disabled config should not error: %v", err)
	}
	if w == nil {
		t.Fatal("New should return non-nil writer even when disabled")
	}
	if w.metrics == nil {
		t.Error("disabled writer should still have metrics initialized")
	}
}

func TestNewEnabledEmptyDSNErrors(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Enabled = true
	cfg.DSN = ""
	logger := zap.NewNop()

	_, err := New(context.Background(), cfg, logger)
	if err == nil {
		t.Fatal("New with empty DSN should error")
	}
	if !containsString(err.Error(), "DSN is required") {
		t.Errorf("error should mention DSN: %v", err)
	}
}

func TestNewEnabledInvalidDSNErrors(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Enabled = true
	cfg.DSN = "not-a-valid-postgres-dsn"
	logger := zap.NewNop()

	_, err := New(context.Background(), cfg, logger)
	if err == nil {
		t.Fatal("New with invalid DSN should error")
	}
}

// ---------------------------------------------------------------------------
// Disabled writer methods — no-op behavior
// ---------------------------------------------------------------------------

func TestDisabledWriterPingReturnsNil(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: false},
		metrics: NewMetrics(),
	}
	if err := w.Ping(); err != nil {
		t.Errorf("Ping on disabled writer should return nil, got %v", err)
	}
}

func TestDisabledWriterCloseReturnsNil(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: false},
		metrics: NewMetrics(),
	}
	if err := w.Close(); err != nil {
		t.Errorf("Close on disabled writer should return nil, got %v", err)
	}
}

func TestDisabledWriterFlushTicksNoOp(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: false},
		metrics: NewMetrics(),
	}
	// Should not panic
	w.FlushTicks()
}

func TestDisabledWriterFlushBarsNoOp(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: false},
		metrics: NewMetrics(),
	}
	// Should not panic
	w.FlushBars()
}

func TestDisabledWriterWriteTickNoOp(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: false},
		metrics: NewMetrics(),
	}
	tick := &normalizer.NormalizedTick{
		Symbol:   "BTC/USDT",
		Price:    decimal.NewFromFloat(50000.0),
		Quantity: decimal.NewFromFloat(0.1),
	}
	// Should not panic or record metrics
	w.WriteTick(tick)
	if w.metrics.TicksReceived() != 0 {
		t.Error("disabled writer should not record tick metrics")
	}
}

func TestDisabledWriterWriteTickNilNoOp(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: true},
		metrics: NewMetrics(),
	}
	// nil tick should be a no-op even when enabled
	w.WriteTick(nil)
	if w.metrics.TicksReceived() != 0 {
		t.Error("nil tick should not record metrics")
	}
}

func TestDisabledWriterWriteBarNoOp(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: false},
		metrics: NewMetrics(),
	}
	// Should not panic
	w.WriteBar("BTC/USDT", "M5", time.Now(),
		decimal.NewFromFloat(50000), decimal.NewFromFloat(50100),
		decimal.NewFromFloat(49900), decimal.NewFromFloat(50050),
		decimal.NewFromFloat(100), 42, "test",
	)
	if w.metrics.BarsReceived() != 0 {
		t.Error("disabled writer should not record bar metrics")
	}
}

func TestDisabledWriterStatsReturnsMap(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: false},
		metrics: NewMetrics(),
	}
	stats := w.Stats()
	if stats == nil {
		t.Error("Stats should return non-nil map even when disabled")
	}
}

func TestPingNilPoolReturnsNil(t *testing.T) {
	w := &DBWriter{
		config:  Config{Enabled: true},
		pool:    nil,
		metrics: NewMetrics(),
	}
	if err := w.Ping(); err != nil {
		t.Errorf("Ping with nil pool should return nil, got %v", err)
	}
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func containsString(s, substr string) bool {
	return len(s) >= len(substr) && searchString(s, substr)
}

func searchString(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
