// Il pacchetto connectors definisce l'interfaccia per gli adattatori delle sorgenti
// dati e il tipo di messaggio grezzo canonico usato nella pipeline.
package connectors

import (
	"fmt"
	"time"
)

// unknownValue is the default fallback for unidentified symbols or channels.
const unknownValue = "unknown"

// RawMessage rappresenta un messaggio non elaborato ricevuto da un exchange.
// Porta con sé i dati grezzi e i metadati sulla sua origine.
type RawMessage struct {
	// Exchange identifica l'exchange sorgente (es. "binance").
	Exchange string

	// Symbol is the trading pair this message pertains to, in the exchange's
	// native format (e.g., "btcusdt" for Binance).
	Symbol string

	// Channel è il canale del feed (es. "trade", "kline_1m").
	Channel string

	// Data contiene il carico utile (payload) grezzo JSON o binario.
	Data []byte

	// Timestamp is the time the message was received by the connector,
	// expressed as Unix nanoseconds for maximum precision.
	Timestamp int64
}

// String restituisce un riepilogo leggibile del messaggio per il log.
func (m RawMessage) String() string {
	ts := time.Unix(0, m.Timestamp)
	return fmt.Sprintf("RawMessage{exchange=%s, symbol=%s, channel=%s, time=%s, bytes=%d}",
		m.Exchange, m.Symbol, m.Channel, ts.Format(time.RFC3339Nano), len(m.Data))
}

// Connector definisce il contratto per ogni adattatore di exchange — "il Cacciatore".
// Ogni Cacciatore gestisce la propria connessione e offre un'interfaccia di lettura.
type Connector interface {
	// Name returns a unique identifier for this connector instance
	// (e.g., "binance-spot", "bybit-futures").
	Name() string

	// Connect establishes the WebSocket connection to the exchange.
	// It should handle authentication if required by the exchange.
	// Returns an error if the connection cannot be established.
	Connect() error

	// Subscribe sends subscription requests for the given symbols and channels
	// to the exchange. The format of symbols and channels is exchange-specific.
	//
	// Examples:
	//   symbols:  ["btcusdt", "ethusdt"]
	//   channels: ["trade", "depth20"]
	Subscribe(symbols []string, channels []string) error

	// ReadMessage blocks until the next message is available from the exchange
	// feed, or until the connection is closed. Returns a RawMessage containing
	// the unprocessed exchange payload.
	//
	// Callers should check for io.EOF or a closed-connection error to detect
	// that the connector has been shut down.
	ReadMessage() (RawMessage, error)

	// Close gracefully shuts down the connector, closing the underlying
	// WebSocket connection and releasing all resources. After Close returns,
	// ReadMessage will return an error on subsequent calls.
	Close() error
}

// ConnectorConfig contiene le impostazioni condivise dai Cacciatori.
type ConnectorConfig struct {
	// WSURL è l'indirizzo base per la connessione WebSocket.
	WSURL string

	// Symbols è la lista dei simboli da seguire.
	Symbols []string

	// Channels è la lista dei canali da seguire.
	Channels []string

	// ReconnectDelay is the initial delay before attempting reconnection
	// after a disconnection. Connectors should use exponential backoff.
	ReconnectDelay time.Duration

	// MaxReconnectDelay è il limite massimo per l'attesa di riconnessione.
	MaxReconnectDelay time.Duration

	// PingInterval is how often to send ping frames to keep the
	// WebSocket connection alive.
	PingInterval time.Duration
}

// DefaultConnectorConfig restituisce una configurazione con valori predefiniti sensati.
func DefaultConnectorConfig() ConnectorConfig {
	return ConnectorConfig{
		ReconnectDelay:    1 * time.Second,
		MaxReconnectDelay: 60 * time.Second,
		PingInterval:      30 * time.Second,
	}
}
