package dbwriter

import (
	"sync"
	"testing"
	"time"

	"github.com/shopspring/decimal"
)

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func makeTick(symbol string) TickRecord {
	return TickRecord{
		Time:      time.Now(),
		Symbol:    symbol,
		Bid:       decimal.NewFromFloat(1.10000),
		Ask:       decimal.NewFromFloat(1.10020),
		LastPrice: decimal.NewFromFloat(1.10010),
		Volume:    decimal.NewFromInt(100),
		Spread:    decimal.NewFromFloat(0.00020),
		Source:    "test",
	}
}

func makeBar(symbol string) BarRecord {
	return BarRecord{
		Time:      time.Now(),
		Symbol:    symbol,
		Timeframe: "M5",
		Open:      decimal.NewFromFloat(1.10000),
		High:      decimal.NewFromFloat(1.10100),
		Low:       decimal.NewFromFloat(1.09900),
		Close:     decimal.NewFromFloat(1.10050),
		Volume:    decimal.NewFromInt(500),
		TickCount: 42,
		SpreadAvg: decimal.NewFromFloat(0.00015),
		Source:    "test",
	}
}

// ---------------------------------------------------------------------------
// TickBuffer
// ---------------------------------------------------------------------------

func TestNewTickBufferDefaultCapacity(t *testing.T) {
	buf := NewTickBuffer(0)
	if buf.capacity != 1000 {
		t.Errorf("capacity = %d, want 1000", buf.capacity)
	}
}

func TestNewTickBufferNegativeCapacity(t *testing.T) {
	buf := NewTickBuffer(-5)
	if buf.capacity != 1000 {
		t.Errorf("capacity = %d, want 1000", buf.capacity)
	}
}

func TestNewTickBufferCustomCapacity(t *testing.T) {
	buf := NewTickBuffer(50)
	if buf.capacity != 50 {
		t.Errorf("capacity = %d, want 50", buf.capacity)
	}
}

func TestTickBufferAddBelowCapacity(t *testing.T) {
	buf := NewTickBuffer(5)
	result := buf.Add(makeTick("EURUSD"))
	if result != nil {
		t.Error("Add should return nil when below capacity")
	}
	if buf.Len() != 1 {
		t.Errorf("Len = %d, want 1", buf.Len())
	}
}

func TestTickBufferAddAtCapacity(t *testing.T) {
	buf := NewTickBuffer(3)
	buf.Add(makeTick("EURUSD"))
	buf.Add(makeTick("EURUSD"))
	batch := buf.Add(makeTick("EURUSD"))

	if batch == nil {
		t.Fatal("Add should return batch at capacity")
	}
	if len(batch) != 3 {
		t.Errorf("batch len = %d, want 3", len(batch))
	}
	if buf.Len() != 0 {
		t.Errorf("Len after flush = %d, want 0", buf.Len())
	}
}

func TestTickBufferFlushReturnsRecords(t *testing.T) {
	buf := NewTickBuffer(10)
	buf.Add(makeTick("EURUSD"))
	buf.Add(makeTick("GBPUSD"))

	batch := buf.Flush()
	if len(batch) != 2 {
		t.Errorf("Flush returned %d records, want 2", len(batch))
	}
	if buf.Len() != 0 {
		t.Errorf("Len after Flush = %d, want 0", buf.Len())
	}
}

func TestTickBufferFlushEmpty(t *testing.T) {
	buf := NewTickBuffer(10)
	batch := buf.Flush()
	if batch != nil {
		t.Error("Flush on empty buffer should return nil")
	}
}

func TestTickBufferLenStartsZero(t *testing.T) {
	buf := NewTickBuffer(10)
	if buf.Len() != 0 {
		t.Errorf("Len = %d, want 0", buf.Len())
	}
}

func TestTickBufferConcurrentAccess(t *testing.T) {
	buf := NewTickBuffer(10000)
	var wg sync.WaitGroup
	goroutines := 10
	ticksPerGoroutine := 100

	wg.Add(goroutines)
	for g := 0; g < goroutines; g++ {
		go func() {
			defer wg.Done()
			for i := 0; i < ticksPerGoroutine; i++ {
				buf.Add(makeTick("EURUSD"))
			}
		}()
	}
	wg.Wait()

	// All ticks accounted for (some may have been flushed as batches)
	remaining := buf.Len()
	total := goroutines * ticksPerGoroutine
	if remaining > total {
		t.Errorf("Len = %d, exceeds total added %d", remaining, total)
	}
}

// ---------------------------------------------------------------------------
// BarBuffer
// ---------------------------------------------------------------------------

func TestNewBarBufferDefaultCapacity(t *testing.T) {
	buf := NewBarBuffer(0)
	if buf.capacity != 100 {
		t.Errorf("capacity = %d, want 100", buf.capacity)
	}
}

func TestNewBarBufferNegativeCapacity(t *testing.T) {
	buf := NewBarBuffer(-1)
	if buf.capacity != 100 {
		t.Errorf("capacity = %d, want 100", buf.capacity)
	}
}

func TestNewBarBufferCustomCapacity(t *testing.T) {
	buf := NewBarBuffer(25)
	if buf.capacity != 25 {
		t.Errorf("capacity = %d, want 25", buf.capacity)
	}
}

func TestBarBufferAddBelowCapacity(t *testing.T) {
	buf := NewBarBuffer(5)
	result := buf.Add(makeBar("EURUSD"))
	if result != nil {
		t.Error("Add should return nil when below capacity")
	}
	if buf.Len() != 1 {
		t.Errorf("Len = %d, want 1", buf.Len())
	}
}

func TestBarBufferAddAtCapacity(t *testing.T) {
	buf := NewBarBuffer(2)
	buf.Add(makeBar("EURUSD"))
	batch := buf.Add(makeBar("GBPUSD"))

	if batch == nil {
		t.Fatal("Add should return batch at capacity")
	}
	if len(batch) != 2 {
		t.Errorf("batch len = %d, want 2", len(batch))
	}
	if buf.Len() != 0 {
		t.Errorf("Len after flush = %d, want 0", buf.Len())
	}
}

func TestBarBufferFlushReturnsRecords(t *testing.T) {
	buf := NewBarBuffer(10)
	buf.Add(makeBar("XAUUSD"))
	batch := buf.Flush()
	if len(batch) != 1 {
		t.Errorf("Flush returned %d records, want 1", len(batch))
	}
}

func TestBarBufferFlushEmpty(t *testing.T) {
	buf := NewBarBuffer(10)
	batch := buf.Flush()
	if batch != nil {
		t.Error("Flush on empty buffer should return nil")
	}
}

func TestBarBufferConcurrentAccess(t *testing.T) {
	buf := NewBarBuffer(10000)
	var wg sync.WaitGroup
	goroutines := 5
	barsPerGoroutine := 50

	wg.Add(goroutines)
	for g := 0; g < goroutines; g++ {
		go func() {
			defer wg.Done()
			for i := 0; i < barsPerGoroutine; i++ {
				buf.Add(makeBar("EURUSD"))
			}
		}()
	}
	wg.Wait()

	remaining := buf.Len()
	total := goroutines * barsPerGoroutine
	if remaining > total {
		t.Errorf("Len = %d, exceeds total added %d", remaining, total)
	}
}
