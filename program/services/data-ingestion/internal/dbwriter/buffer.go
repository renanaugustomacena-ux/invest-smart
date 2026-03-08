// Package dbwriter - buffer.go
//
// Implementa buffer thread-safe per l'accumulo di record prima del flush.
// Utilizza un design lock-free dove possibile per massimizzare il throughput.
package dbwriter

import (
	"sync"
)

// TickBuffer è un buffer thread-safe per accumulare TickRecord.
// Quando il buffer raggiunge la capacità, restituisce un batch completo.
type TickBuffer struct {
	mu       sync.Mutex
	records  []TickRecord
	capacity int
}

// NewTickBuffer crea un nuovo buffer per tick con la capacità specificata.
func NewTickBuffer(capacity int) *TickBuffer {
	if capacity <= 0 {
		capacity = 1000
	}
	return &TickBuffer{
		records:  make([]TickRecord, 0, capacity),
		capacity: capacity,
	}
}

// Add aggiunge un record al buffer.
// Se il buffer è pieno, restituisce un batch completo e svuota il buffer.
// Altrimenti restituisce nil.
func (b *TickBuffer) Add(record TickRecord) []TickRecord {
	b.mu.Lock()
	defer b.mu.Unlock()

	b.records = append(b.records, record)

	if len(b.records) >= b.capacity {
		batch := b.records
		b.records = make([]TickRecord, 0, b.capacity)
		return batch
	}

	return nil
}

// Flush restituisce tutti i record accumulati e svuota il buffer.
// Utilizzato per flush periodici o durante lo shutdown.
func (b *TickBuffer) Flush() []TickRecord {
	b.mu.Lock()
	defer b.mu.Unlock()

	if len(b.records) == 0 {
		return nil
	}

	batch := b.records
	b.records = make([]TickRecord, 0, b.capacity)
	return batch
}

// Len restituisce il numero di record attualmente nel buffer.
func (b *TickBuffer) Len() int {
	b.mu.Lock()
	defer b.mu.Unlock()
	return len(b.records)
}

// BarBuffer è un buffer thread-safe per accumulare BarRecord.
type BarBuffer struct {
	mu       sync.Mutex
	records  []BarRecord
	capacity int
}

// NewBarBuffer crea un nuovo buffer per bar con la capacità specificata.
func NewBarBuffer(capacity int) *BarBuffer {
	if capacity <= 0 {
		capacity = 100
	}
	return &BarBuffer{
		records:  make([]BarRecord, 0, capacity),
		capacity: capacity,
	}
}

// Add aggiunge un record al buffer.
// Se il buffer è pieno, restituisce un batch completo e svuota il buffer.
func (b *BarBuffer) Add(record BarRecord) []BarRecord {
	b.mu.Lock()
	defer b.mu.Unlock()

	b.records = append(b.records, record)

	if len(b.records) >= b.capacity {
		batch := b.records
		b.records = make([]BarRecord, 0, b.capacity)
		return batch
	}

	return nil
}

// Flush restituisce tutti i record accumulati e svuota il buffer.
func (b *BarBuffer) Flush() []BarRecord {
	b.mu.Lock()
	defer b.mu.Unlock()

	if len(b.records) == 0 {
		return nil
	}

	batch := b.records
	b.records = make([]BarRecord, 0, b.capacity)
	return batch
}

// Len restituisce il numero di record attualmente nel buffer.
func (b *BarBuffer) Len() int {
	b.mu.Lock()
	defer b.mu.Unlock()
	return len(b.records)
}
