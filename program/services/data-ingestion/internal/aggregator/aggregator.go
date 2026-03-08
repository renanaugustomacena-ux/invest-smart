// Il pacchetto aggregator accumula i tick normalizzati in barre OHLCV.
//
// L'Assemblatore raggruppa i tick per simbolo e timeframe, emettendo barre
// complete quando viene superato un limite temporale. È sicuro per l'uso
// concorrente da più goroutine grazie alla protezione interna tramite mutex.
//
// Timeframe supportati: M1, M5, M15, H1, H4, D1.
package aggregator

import (
	"fmt"
	"sync"
	"time"

	"github.com/shopspring/decimal"
)

// Timeframe rappresenta la durata di una candela — la "dimensione della scatola".
type Timeframe string

const (
	M1  Timeframe = "M1"
	M5  Timeframe = "M5"
	M15 Timeframe = "M15"
	H1  Timeframe = "H1"
	H4  Timeframe = "H4"
	D1  Timeframe = "D1"
)

// TimeframeDuration restituisce la durata temporale effettiva per il timeframe dato.
func TimeframeDuration(tf Timeframe) time.Duration {
	switch tf {
	case M1:
		return 1 * time.Minute
	case M5:
		return 5 * time.Minute
	case M15:
		return 15 * time.Minute
	case H1:
		return 1 * time.Hour
	case H4:
		return 4 * time.Hour
	case D1:
		return 24 * time.Hour
	default:
		return 1 * time.Minute
	}
}

// Bar rappresenta una candela OHLCV completata — il "pacco pronto per la spedizione".
type Bar struct {
	Symbol    string          `json:"symbol"`
	Timeframe Timeframe       `json:"timeframe"`
	OpenTime  time.Time       `json:"open_time"`
	CloseTime time.Time       `json:"close_time"`
	Open      decimal.Decimal `json:"open"`
	High      decimal.Decimal `json:"high"`
	Low       decimal.Decimal `json:"low"`
	Close     decimal.Decimal `json:"close"`
	Volume    decimal.Decimal `json:"volume"`
	TickCount int             `json:"tick_count"`
}

// OnBarComplete viene chiamata quando una barra è finalizzata — "squillo di fine produzione".
type OnBarComplete func(bar Bar)

// pendingBar tiene traccia di una candela in corso — "scatola in fase di riempimento".
type pendingBar struct {
	symbol    string
	timeframe Timeframe
	openTime  time.Time
	closeTime time.Time
	open      decimal.Decimal
	high      decimal.Decimal
	low       decimal.Decimal
	close     decimal.Decimal
	volume    decimal.Decimal
	tickCount int
}

// floorTime arrotonda un timestamp per difetto al limite temporale più vicino.
func floorTime(t time.Time, tf Timeframe) time.Time {
	d := TimeframeDuration(tf)
	return t.Truncate(d)
}

// Aggregator accumula i tick in barre OHLCV per simbolo e timeframe — "l'Assemblatore".
type Aggregator struct {
	mu         sync.Mutex
	timeframes []Timeframe
	onComplete OnBarComplete

	// bars è indicizzata come "SIMBOLO:TIMEFRAME" — "il magazzino dei pacchi aperti".
	bars map[string]*pendingBar
}

// NewAggregator crea un Assemblatore per i timeframe indicati.
// Il callback onComplete viene attivato ogni volta che un pacco è pronto.
func NewAggregator(timeframes []Timeframe, onComplete OnBarComplete) *Aggregator {
	return &Aggregator{
		timeframes: timeframes,
		onComplete: onComplete,
		bars:       make(map[string]*pendingBar),
	}
}

// key restituisce la chiave per la mappa per una combinazione simbolo + timeframe.
func key(symbol string, tf Timeframe) string {
	return fmt.Sprintf("%s:%s", symbol, string(tf))
}

// AddTick elabora un singolo tick, aggiornando tutti i pacchi aperti per quel simbolo.
// Se il tempo supera il limite del pacco, quello corrente viene chiuso e spedito
// tramite onComplete, e ne viene iniziato uno nuovo.
func (a *Aggregator) AddTick(symbol string, price decimal.Decimal, volume decimal.Decimal, tickTime time.Time) {
	a.mu.Lock()
	defer a.mu.Unlock()

	for _, tf := range a.timeframes {
		k := key(symbol, tf)
		barOpen := floorTime(tickTime, tf)
		barClose := barOpen.Add(TimeframeDuration(tf))

		pending, exists := a.bars[k]

		if exists && barOpen.After(pending.openTime) {
			// Limite temporale superato — chiudiamo il pacco corrente.
			completed := Bar{
				Symbol:    pending.symbol,
				Timeframe: pending.timeframe,
				OpenTime:  pending.openTime,
				CloseTime: pending.closeTime,
				Open:      pending.open,
				High:      pending.high,
				Low:       pending.low,
				Close:     pending.close,
				Volume:    pending.volume,
				TickCount: pending.tickCount,
			}
			if a.onComplete != nil {
				a.onComplete(completed)
			}
			exists = false
		}

		if !exists {
			// Iniziamo un nuovo pacco.
			a.bars[k] = &pendingBar{
				symbol:    symbol,
				timeframe: tf,
				openTime:  barOpen,
				closeTime: barClose,
				open:      price,
				high:      price,
				low:       price,
				close:     price,
				volume:    volume,
				tickCount: 1,
			}
		} else {
			// Aggiorniamo il pacco esistente.
			pending.close = price
			if price.GreaterThan(pending.high) {
				pending.high = price
			}
			if price.LessThan(pending.low) {
				pending.low = price
			}
			pending.volume = pending.volume.Add(volume)
			pending.tickCount++
		}
	}
}

// FlushAll finalizza ed emette tutti i pacchi aperti ignorando i limiti di tempo.
// Utile durante la chiusura del servizio per non perdere materiale parziale.
func (a *Aggregator) FlushAll() []Bar {
	a.mu.Lock()
	defer a.mu.Unlock()

	var flushed []Bar
	for k, pending := range a.bars {
		bar := Bar{
			Symbol:    pending.symbol,
			Timeframe: pending.timeframe,
			OpenTime:  pending.openTime,
			CloseTime: pending.closeTime,
			Open:      pending.open,
			High:      pending.high,
			Low:       pending.low,
			Close:     pending.close,
			Volume:    pending.volume,
			TickCount: pending.tickCount,
		}
		flushed = append(flushed, bar)
		if a.onComplete != nil {
			a.onComplete(bar)
		}
		delete(a.bars, k)
	}
	return flushed
}

// PendingCount restituisce il numero di pacchi attualmente in fase di assemblaggio.
func (a *Aggregator) PendingCount() int {
	a.mu.Lock()
	defer a.mu.Unlock()
	return len(a.bars)
}
