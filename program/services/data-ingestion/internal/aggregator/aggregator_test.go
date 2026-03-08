package aggregator

import (
	"sync"
	"testing"
	"time"

	"github.com/shopspring/decimal"
)

func TestNewAggregator(t *testing.T) {
	agg := NewAggregator([]Timeframe{M1}, nil)
	if agg == nil {
		t.Fatal("NewAggregator returned nil")
	}
	if agg.PendingCount() != 0 {
		t.Errorf("expected 0 pending, got %d", agg.PendingCount())
	}
}

func TestAddFirstTick(t *testing.T) {
	agg := NewAggregator([]Timeframe{M1}, nil)
	now := time.Date(2025, 1, 1, 12, 0, 30, 0, time.UTC)

	// Carica un tick iniziale: 12:00:30
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50000), decimal.NewFromInt(1), now)

	if agg.PendingCount() != 1 {
		t.Errorf("expected 1 pending bar, got %d", agg.PendingCount())
	}
}

func TestMultipleTicksSameBar(t *testing.T) {
	var completed []Bar
	agg := NewAggregator([]Timeframe{M1}, func(bar Bar) {
		completed = append(completed, bar)
	})

	base := time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC)

	// Inserisce tick tutti all'interno della stessa finestra di 1 minuto
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50000), decimal.NewFromInt(1), base.Add(10*time.Second))
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50100), decimal.NewFromInt(2), base.Add(20*time.Second))
	agg.AddTick("BTC/USDT", decimal.NewFromInt(49900), decimal.NewFromInt(3), base.Add(30*time.Second))
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50050), decimal.NewFromInt(1), base.Add(40*time.Second))

	// Nessun pacchetto dovrebbe essere completato (stesso minuto)
	if len(completed) != 0 {
		t.Errorf("expected 0 completed bars, got %d", len(completed))
	}

	// Verify pending state
	if agg.PendingCount() != 1 {
		t.Errorf("expected 1 pending bar, got %d", agg.PendingCount())
	}
}

func TestBarCompletesOnTimeBoundary(t *testing.T) {
	var completed []Bar
	agg := NewAggregator([]Timeframe{M1}, func(bar Bar) {
		completed = append(completed, bar)
	})

	base := time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC)

	// Ticks nel minuto 12:00
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50000), decimal.NewFromInt(1), base.Add(10*time.Second))
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50200), decimal.NewFromInt(2), base.Add(30*time.Second))
	agg.AddTick("BTC/USDT", decimal.NewFromInt(49800), decimal.NewFromInt(1), base.Add(50*time.Second))

	// Tick nel minuto 12:01 — innesca il completamento del pacchetto
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50100), decimal.NewFromInt(3), base.Add(70*time.Second))

	if len(completed) != 1 {
		t.Fatalf("expected 1 completed bar, got %d", len(completed))
	}

	bar := completed[0]
	if bar.Symbol != "BTC/USDT" {
		t.Errorf("expected symbol BTC/USDT, got %s", bar.Symbol)
	}
	if bar.Timeframe != M1 {
		t.Errorf("expected timeframe M1, got %s", bar.Timeframe)
	}
	if !bar.Open.Equal(decimal.NewFromInt(50000)) {
		t.Errorf("expected open 50000, got %s", bar.Open)
	}
	if !bar.High.Equal(decimal.NewFromInt(50200)) {
		t.Errorf("expected high 50200, got %s", bar.High)
	}
	if !bar.Low.Equal(decimal.NewFromInt(49800)) {
		t.Errorf("expected low 49800, got %s", bar.Low)
	}
	if !bar.Close.Equal(decimal.NewFromInt(49800)) {
		t.Errorf("expected close 49800, got %s", bar.Close)
	}
	if !bar.Volume.Equal(decimal.NewFromInt(4)) {
		t.Errorf("expected volume 4, got %s", bar.Volume)
	}
	if bar.TickCount != 3 {
		t.Errorf("expected 3 ticks, got %d", bar.TickCount)
	}
}

func TestMultipleTimeframes(t *testing.T) {
	var completed []Bar
	agg := NewAggregator([]Timeframe{M1, M5}, func(bar Bar) {
		completed = append(completed, bar)
	})

	base := time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC)

	// Tick alle 12:00:30
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50000), decimal.NewFromInt(1), base.Add(30*time.Second))

	// Should have 2 pending bars (M1 + M5)
	if agg.PendingCount() != 2 {
		t.Errorf("expected 2 pending bars, got %d", agg.PendingCount())
	}

	// Tick alle 12:01:30 — attraversa il confine M1 ma NON M5
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50100), decimal.NewFromInt(1), base.Add(90*time.Second))

	// Should have 1 completed (M1), still 2 pending (new M1 + continuing M5)
	m1Completed := 0
	for _, bar := range completed {
		if bar.Timeframe == M1 {
			m1Completed++
		}
	}
	if m1Completed != 1 {
		t.Errorf("expected 1 M1 bar completed, got %d", m1Completed)
	}
}

func TestMultipleSymbols(t *testing.T) {
	agg := NewAggregator([]Timeframe{M1}, nil)
	now := time.Date(2025, 1, 1, 12, 0, 30, 0, time.UTC)

	agg.AddTick("BTC/USDT", decimal.NewFromInt(50000), decimal.NewFromInt(1), now)
	agg.AddTick("ETH/USDT", decimal.NewFromInt(3000), decimal.NewFromInt(5), now)

	if agg.PendingCount() != 2 {
		t.Errorf("expected 2 pending bars (one per symbol), got %d", agg.PendingCount())
	}
}

func TestFlushAll(t *testing.T) {
	var callbackBars []Bar
	agg := NewAggregator([]Timeframe{M1}, func(bar Bar) {
		callbackBars = append(callbackBars, bar)
	})

	now := time.Date(2025, 1, 1, 12, 0, 30, 0, time.UTC)
	agg.AddTick("BTC/USDT", decimal.NewFromInt(50000), decimal.NewFromInt(1), now)
	agg.AddTick("ETH/USDT", decimal.NewFromInt(3000), decimal.NewFromInt(5), now)

	flushed := agg.FlushAll()

	if len(flushed) != 2 {
		t.Errorf("expected 2 flushed bars, got %d", len(flushed))
	}
	if len(callbackBars) != 2 {
		t.Errorf("expected 2 callback bars, got %d", len(callbackBars))
	}
	if agg.PendingCount() != 0 {
		t.Errorf("expected 0 pending after flush, got %d", agg.PendingCount())
	}
}

func TestConcurrentAccess(t *testing.T) {
	agg := NewAggregator([]Timeframe{M1}, nil)
	base := time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC)

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			price := decimal.NewFromInt(int64(50000 + i))
			vol := decimal.NewFromInt(1)
			agg.AddTick("BTC/USDT", price, vol, base.Add(time.Duration(i)*time.Millisecond))
		}(i)
	}
	wg.Wait()

	// Non dovrebbe andare in panico; il conteggio esatto dipende dai tempi di esecuzione
	if agg.PendingCount() < 1 {
		t.Error("expected at least 1 pending bar after concurrent adds")
	}
}

func TestTimeframeDuration(t *testing.T) {
	cases := []struct {
		tf       Timeframe
		expected time.Duration
	}{
		{M1, 1 * time.Minute},
		{M5, 5 * time.Minute},
		{M15, 15 * time.Minute},
		{H1, 1 * time.Hour},
		{H4, 4 * time.Hour},
		{D1, 24 * time.Hour},
	}
	for _, tc := range cases {
		got := TimeframeDuration(tc.tf)
		if got != tc.expected {
			t.Errorf("TimeframeDuration(%s): got %v, want %v", tc.tf, got, tc.expected)
		}
	}
}
