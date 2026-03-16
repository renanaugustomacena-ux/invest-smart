// Package dbwriter - metrics.go
//
// Implementa le metriche per monitorare le performance del DBWriter.
// Le metriche sono esportabili in formato Prometheus.
package dbwriter

import (
	"sync"
	"sync/atomic"
	"time"
)

// Metrics raccoglie le statistiche di performance del DBWriter.
type Metrics struct {
	// Contatori atomici
	ticksReceived uint64
	ticksFlushed  uint64
	barsReceived  uint64
	barsFlushed   uint64
	flushErrors   uint64

	// Statistiche con lock
	mu               sync.RWMutex
	lastFlushTime    time.Time
	lastFlushCount   int
	totalFlushTimeNs int64
	flushCount       int64

	// Per tipo di errore
	errorCounts map[string]uint64
	errorMu     sync.Mutex
}

// NewMetrics crea un nuovo raccoglitore di metriche.
func NewMetrics() *Metrics {
	return &Metrics{
		errorCounts:   make(map[string]uint64),
		lastFlushTime: time.Now(),
	}
}

// RecordTick registra la ricezione di un tick.
func (m *Metrics) RecordTick() {
	atomic.AddUint64(&m.ticksReceived, 1)
}

// RecordBar registra la ricezione di una bar.
func (m *Metrics) RecordBar() {
	atomic.AddUint64(&m.barsReceived, 1)
}

// RecordFlush registra un flush completato.
func (m *Metrics) RecordFlush(recordType string, count int, duration time.Duration) {
	switch recordType {
	case "tick":
		atomic.AddUint64(&m.ticksFlushed, uint64(count))
	case "bar":
		atomic.AddUint64(&m.barsFlushed, uint64(count))
	}

	m.mu.Lock()
	m.lastFlushTime = time.Now()
	m.lastFlushCount = count
	m.totalFlushTimeNs += duration.Nanoseconds()
	m.flushCount++
	m.mu.Unlock()
}

// RecordError registra un errore per tipo.
func (m *Metrics) RecordError(errorType string) {
	atomic.AddUint64(&m.flushErrors, 1)

	m.errorMu.Lock()
	m.errorCounts[errorType]++
	m.errorMu.Unlock()
}

// TicksReceived restituisce il numero di tick ricevuti.
func (m *Metrics) TicksReceived() uint64 {
	return atomic.LoadUint64(&m.ticksReceived)
}

// TicksFlushed restituisce il numero di tick persistiti.
func (m *Metrics) TicksFlushed() uint64 {
	return atomic.LoadUint64(&m.ticksFlushed)
}

// BarsReceived restituisce il numero di bar ricevute.
func (m *Metrics) BarsReceived() uint64 {
	return atomic.LoadUint64(&m.barsReceived)
}

// BarsFlushed restituisce il numero di bar persistite.
func (m *Metrics) BarsFlushed() uint64 {
	return atomic.LoadUint64(&m.barsFlushed)
}

// FlushErrors restituisce il numero totale di errori di flush.
func (m *Metrics) FlushErrors() uint64 {
	return atomic.LoadUint64(&m.flushErrors)
}

// AvgFlushDuration restituisce la durata media di flush.
func (m *Metrics) AvgFlushDuration() time.Duration {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.flushCount == 0 {
		return 0
	}
	return time.Duration(m.totalFlushTimeNs / m.flushCount)
}

// Stats restituisce tutte le statistiche come mappa.
func (m *Metrics) Stats() map[string]interface{} {
	m.mu.RLock()
	lastFlush := m.lastFlushTime
	lastCount := m.lastFlushCount
	avgDuration := time.Duration(0)
	if m.flushCount > 0 {
		avgDuration = time.Duration(m.totalFlushTimeNs / m.flushCount)
	}
	m.mu.RUnlock()

	m.errorMu.Lock()
	errorsCopy := make(map[string]uint64, len(m.errorCounts))
	for k, v := range m.errorCounts {
		errorsCopy[k] = v
	}
	m.errorMu.Unlock()

	return map[string]interface{}{
		"ticks_received":     atomic.LoadUint64(&m.ticksReceived),
		"ticks_flushed":      atomic.LoadUint64(&m.ticksFlushed),
		"bars_received":      atomic.LoadUint64(&m.barsReceived),
		"bars_flushed":       atomic.LoadUint64(&m.barsFlushed),
		"flush_errors":       atomic.LoadUint64(&m.flushErrors),
		"last_flush_time":    lastFlush,
		"last_flush_count":   lastCount,
		"avg_flush_duration": avgDuration.String(),
		"errors_by_type":     errorsCopy,
	}
}

// Reset azzera tutte le metriche.
func (m *Metrics) Reset() {
	atomic.StoreUint64(&m.ticksReceived, 0)
	atomic.StoreUint64(&m.ticksFlushed, 0)
	atomic.StoreUint64(&m.barsReceived, 0)
	atomic.StoreUint64(&m.barsFlushed, 0)
	atomic.StoreUint64(&m.flushErrors, 0)

	m.mu.Lock()
	m.lastFlushTime = time.Now()
	m.lastFlushCount = 0
	m.totalFlushTimeNs = 0
	m.flushCount = 0
	m.mu.Unlock()

	m.errorMu.Lock()
	m.errorCounts = make(map[string]uint64)
	m.errorMu.Unlock()
}
