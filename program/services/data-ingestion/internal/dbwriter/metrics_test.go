package dbwriter

import (
	"sync"
	"testing"
	"time"
)

// ---------------------------------------------------------------------------
// NewMetrics
// ---------------------------------------------------------------------------

func TestNewMetricsInitialCounters(t *testing.T) {
	m := NewMetrics()
	if m.TicksReceived() != 0 {
		t.Errorf("TicksReceived = %d, want 0", m.TicksReceived())
	}
	if m.BarsReceived() != 0 {
		t.Errorf("BarsReceived = %d, want 0", m.BarsReceived())
	}
	if m.TicksFlushed() != 0 {
		t.Errorf("TicksFlushed = %d, want 0", m.TicksFlushed())
	}
	if m.BarsFlushed() != 0 {
		t.Errorf("BarsFlushed = %d, want 0", m.BarsFlushed())
	}
	if m.FlushErrors() != 0 {
		t.Errorf("FlushErrors = %d, want 0", m.FlushErrors())
	}
}

func TestNewMetricsErrorMapInitialized(t *testing.T) {
	m := NewMetrics()
	if m.errorCounts == nil {
		t.Error("errorCounts map should be initialized")
	}
}

// ---------------------------------------------------------------------------
// RecordTick / RecordBar
// ---------------------------------------------------------------------------

func TestRecordTickIncrements(t *testing.T) {
	m := NewMetrics()
	m.RecordTick()
	m.RecordTick()
	m.RecordTick()
	if m.TicksReceived() != 3 {
		t.Errorf("TicksReceived = %d, want 3", m.TicksReceived())
	}
}

func TestRecordBarIncrements(t *testing.T) {
	m := NewMetrics()
	m.RecordBar()
	m.RecordBar()
	if m.BarsReceived() != 2 {
		t.Errorf("BarsReceived = %d, want 2", m.BarsReceived())
	}
}

func TestRecordTickDoesNotAffectBars(t *testing.T) {
	m := NewMetrics()
	m.RecordTick()
	if m.BarsReceived() != 0 {
		t.Errorf("BarsReceived = %d after RecordTick, want 0", m.BarsReceived())
	}
}

func TestRecordBarDoesNotAffectTicks(t *testing.T) {
	m := NewMetrics()
	m.RecordBar()
	if m.TicksReceived() != 0 {
		t.Errorf("TicksReceived = %d after RecordBar, want 0", m.TicksReceived())
	}
}

// ---------------------------------------------------------------------------
// RecordFlush
// ---------------------------------------------------------------------------

func TestRecordFlushTickType(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("tick", 50, 10*time.Millisecond)
	if m.TicksFlushed() != 50 {
		t.Errorf("TicksFlushed = %d, want 50", m.TicksFlushed())
	}
	if m.BarsFlushed() != 0 {
		t.Errorf("BarsFlushed = %d, want 0", m.BarsFlushed())
	}
}

func TestRecordFlushBarType(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("bar", 25, 5*time.Millisecond)
	if m.BarsFlushed() != 25 {
		t.Errorf("BarsFlushed = %d, want 25", m.BarsFlushed())
	}
	if m.TicksFlushed() != 0 {
		t.Errorf("TicksFlushed = %d, want 0", m.TicksFlushed())
	}
}

func TestRecordFlushUnknownType(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("unknown", 10, time.Millisecond)
	// Unknown type should not increment tick or bar flushed counters
	if m.TicksFlushed() != 0 {
		t.Errorf("TicksFlushed = %d after unknown type, want 0", m.TicksFlushed())
	}
	if m.BarsFlushed() != 0 {
		t.Errorf("BarsFlushed = %d after unknown type, want 0", m.BarsFlushed())
	}
}

func TestRecordFlushUpdatesLastFlushCount(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("tick", 42, time.Millisecond)

	m.mu.RLock()
	lastCount := m.lastFlushCount
	m.mu.RUnlock()

	if lastCount != 42 {
		t.Errorf("lastFlushCount = %d, want 42", lastCount)
	}
}

func TestRecordFlushAccumulatesDuration(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("tick", 10, 100*time.Millisecond)
	m.RecordFlush("tick", 20, 200*time.Millisecond)

	avg := m.AvgFlushDuration()
	expected := 150 * time.Millisecond
	if avg != expected {
		t.Errorf("AvgFlushDuration = %v, want %v", avg, expected)
	}
}

func TestRecordFlushMultipleAccumulates(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("tick", 10, time.Millisecond)
	m.RecordFlush("tick", 20, time.Millisecond)
	m.RecordFlush("bar", 5, time.Millisecond)

	if m.TicksFlushed() != 30 {
		t.Errorf("TicksFlushed = %d, want 30", m.TicksFlushed())
	}
	if m.BarsFlushed() != 5 {
		t.Errorf("BarsFlushed = %d, want 5", m.BarsFlushed())
	}
}

// ---------------------------------------------------------------------------
// RecordError
// ---------------------------------------------------------------------------

func TestRecordErrorIncrementsFlushErrors(t *testing.T) {
	m := NewMetrics()
	m.RecordError("db_timeout")
	m.RecordError("db_timeout")
	m.RecordError("connection_lost")
	if m.FlushErrors() != 3 {
		t.Errorf("FlushErrors = %d, want 3", m.FlushErrors())
	}
}

func TestRecordErrorTracksTypes(t *testing.T) {
	m := NewMetrics()
	m.RecordError("db_timeout")
	m.RecordError("db_timeout")
	m.RecordError("connection_lost")

	m.errorMu.Lock()
	defer m.errorMu.Unlock()
	if m.errorCounts["db_timeout"] != 2 {
		t.Errorf("db_timeout count = %d, want 2", m.errorCounts["db_timeout"])
	}
	if m.errorCounts["connection_lost"] != 1 {
		t.Errorf("connection_lost count = %d, want 1", m.errorCounts["connection_lost"])
	}
}

// ---------------------------------------------------------------------------
// AvgFlushDuration
// ---------------------------------------------------------------------------

func TestAvgFlushDurationZeroFlushes(t *testing.T) {
	m := NewMetrics()
	if m.AvgFlushDuration() != 0 {
		t.Errorf("AvgFlushDuration = %v, want 0", m.AvgFlushDuration())
	}
}

func TestAvgFlushDurationSingleFlush(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("tick", 10, 500*time.Microsecond)
	if m.AvgFlushDuration() != 500*time.Microsecond {
		t.Errorf("AvgFlushDuration = %v, want 500µs", m.AvgFlushDuration())
	}
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

func TestStatsReturnsAllKeys(t *testing.T) {
	m := NewMetrics()
	m.RecordTick()
	m.RecordBar()
	m.RecordFlush("tick", 1, time.Millisecond)
	m.RecordError("test_error")

	stats := m.Stats()

	expectedKeys := []string{
		"ticks_received", "ticks_flushed",
		"bars_received", "bars_flushed",
		"flush_errors", "last_flush_time",
		"last_flush_count", "avg_flush_duration",
		"errors_by_type",
	}
	for _, key := range expectedKeys {
		if _, ok := stats[key]; !ok {
			t.Errorf("Stats missing key %q", key)
		}
	}
}

func TestStatsTicksReceivedValue(t *testing.T) {
	m := NewMetrics()
	m.RecordTick()
	m.RecordTick()
	stats := m.Stats()
	if stats["ticks_received"].(uint64) != 2 {
		t.Errorf("stats[ticks_received] = %v, want 2", stats["ticks_received"])
	}
}

func TestStatsErrorsByTypeCopy(t *testing.T) {
	m := NewMetrics()
	m.RecordError("err_a")
	m.RecordError("err_a")

	stats := m.Stats()
	errMap := stats["errors_by_type"].(map[string]uint64)

	if errMap["err_a"] != 2 {
		t.Errorf("errors_by_type[err_a] = %d, want 2", errMap["err_a"])
	}

	// Modifying returned map should not affect metrics
	errMap["err_a"] = 999
	m.errorMu.Lock()
	if m.errorCounts["err_a"] != 2 {
		t.Errorf("internal errorCounts modified via Stats return, got %d", m.errorCounts["err_a"])
	}
	m.errorMu.Unlock()
}

func TestStatsLastFlushCount(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("bar", 77, time.Millisecond)
	stats := m.Stats()
	if stats["last_flush_count"].(int) != 77 {
		t.Errorf("stats[last_flush_count] = %v, want 77", stats["last_flush_count"])
	}
}

func TestStatsAvgFlushDurationString(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("tick", 10, 1*time.Second)
	stats := m.Stats()
	dur := stats["avg_flush_duration"].(string)
	if dur != "1s" {
		t.Errorf("avg_flush_duration = %q, want \"1s\"", dur)
	}
}

// ---------------------------------------------------------------------------
// Reset
// ---------------------------------------------------------------------------

func TestResetClearsCounters(t *testing.T) {
	m := NewMetrics()
	m.RecordTick()
	m.RecordTick()
	m.RecordBar()
	m.RecordFlush("tick", 10, time.Millisecond)
	m.RecordError("test")

	m.Reset()

	if m.TicksReceived() != 0 {
		t.Errorf("TicksReceived after reset = %d, want 0", m.TicksReceived())
	}
	if m.BarsReceived() != 0 {
		t.Errorf("BarsReceived after reset = %d, want 0", m.BarsReceived())
	}
	if m.TicksFlushed() != 0 {
		t.Errorf("TicksFlushed after reset = %d, want 0", m.TicksFlushed())
	}
	if m.BarsFlushed() != 0 {
		t.Errorf("BarsFlushed after reset = %d, want 0", m.BarsFlushed())
	}
	if m.FlushErrors() != 0 {
		t.Errorf("FlushErrors after reset = %d, want 0", m.FlushErrors())
	}
}

func TestResetClearsFlushStats(t *testing.T) {
	m := NewMetrics()
	m.RecordFlush("tick", 50, time.Second)
	m.Reset()

	if m.AvgFlushDuration() != 0 {
		t.Errorf("AvgFlushDuration after reset = %v, want 0", m.AvgFlushDuration())
	}

	m.mu.RLock()
	if m.lastFlushCount != 0 {
		t.Errorf("lastFlushCount after reset = %d, want 0", m.lastFlushCount)
	}
	m.mu.RUnlock()
}

func TestResetClearsErrorCounts(t *testing.T) {
	m := NewMetrics()
	m.RecordError("db_timeout")
	m.RecordError("connection_lost")
	m.Reset()

	m.errorMu.Lock()
	if len(m.errorCounts) != 0 {
		t.Errorf("errorCounts after reset has %d entries, want 0", len(m.errorCounts))
	}
	m.errorMu.Unlock()
}

// ---------------------------------------------------------------------------
// Concurrency
// ---------------------------------------------------------------------------

func TestMetricsConcurrentAccess(t *testing.T) {
	m := NewMetrics()
	var wg sync.WaitGroup
	goroutines := 10

	wg.Add(goroutines * 4)
	for i := 0; i < goroutines; i++ {
		go func() {
			defer wg.Done()
			for j := 0; j < 100; j++ {
				m.RecordTick()
			}
		}()
		go func() {
			defer wg.Done()
			for j := 0; j < 100; j++ {
				m.RecordBar()
			}
		}()
		go func() {
			defer wg.Done()
			for j := 0; j < 10; j++ {
				m.RecordFlush("tick", 5, time.Millisecond)
			}
		}()
		go func() {
			defer wg.Done()
			for j := 0; j < 10; j++ {
				m.RecordError("concurrent_err")
			}
		}()
	}
	wg.Wait()

	if m.TicksReceived() != uint64(goroutines*100) {
		t.Errorf("TicksReceived = %d, want %d", m.TicksReceived(), goroutines*100)
	}
	if m.BarsReceived() != uint64(goroutines*100) {
		t.Errorf("BarsReceived = %d, want %d", m.BarsReceived(), goroutines*100)
	}
	if m.FlushErrors() != uint64(goroutines*10) {
		t.Errorf("FlushErrors = %d, want %d", m.FlushErrors(), goroutines*10)
	}
}

func TestMetricsConcurrentStatsRead(t *testing.T) {
	m := NewMetrics()
	var wg sync.WaitGroup

	// Writers
	wg.Add(2)
	go func() {
		defer wg.Done()
		for i := 0; i < 100; i++ {
			m.RecordTick()
			m.RecordFlush("tick", 1, time.Microsecond)
		}
	}()

	// Concurrent readers
	go func() {
		defer wg.Done()
		for i := 0; i < 100; i++ {
			stats := m.Stats()
			_ = stats["ticks_received"]
			_ = m.AvgFlushDuration()
		}
	}()

	wg.Wait()
	// No race condition — test passes if -race detector is clean
}
