package connectors

import (
	"fmt"
	"sync"
	"time"
)

// MockConnector implementa l'interfaccia Connector per scopi di test.
// Genera messaggi sintetici di mercato senza richiedere una connessione reale —
// "il Simulatore di Estrazione".
type MockConnector struct {
	name       string
	connected  bool
	subscribed bool
	closed     bool
	mu         sync.Mutex

	// messages è un canale bufferizzato dove i test possono iniettare materiale.
	// ReadMessage pesca da qui.
	messages chan RawMessage

	// GenerateInterval controlla ogni quanto produrre messaggi automatici.
	// Impostare a 0 per disattivare l'estrazione automatica.
	GenerateInterval time.Duration

	// Symbols holds the symbols this mock is subscribed to.
	Symbols []string

	// Channels holds the channels this mock is subscribed to.
	Channels []string

	// OnConnect is an optional callback invoked when Connect() is called.
	// Return a non-nil error to simulate connection failure.
	OnConnect func() error

	// OnSubscribe is an optional callback invoked when Subscribe() is called.
	OnSubscribe func(symbols, channels []string) error

	// MessageFactory costruisce i messaggi sintetici per l'estrazione automatica.
	MessageFactory func(symbol string, seqNum int) RawMessage

	stopCh chan struct{}
	seqNum int
}

// MockConnectorOption is a functional option for configuring MockConnector.
type MockConnectorOption func(*MockConnector)

// WithGenerateInterval sets the auto-generation interval for synthetic data.
func WithGenerateInterval(d time.Duration) MockConnectorOption {
	return func(m *MockConnector) {
		m.GenerateInterval = d
	}
}

// WithMessageFactory sets a custom message factory for auto-generation.
func WithMessageFactory(fn func(symbol string, seqNum int) RawMessage) MockConnectorOption {
	return func(m *MockConnector) {
		m.MessageFactory = fn
	}
}

// WithOnConnect sets a callback invoked during Connect().
func WithOnConnect(fn func() error) MockConnectorOption {
	return func(m *MockConnector) {
		m.OnConnect = fn
	}
}

// NewMockConnector creates a new MockConnector with the given name and options.
func NewMockConnector(name string, opts ...MockConnectorOption) *MockConnector {
	m := &MockConnector{
		name:     name,
		messages: make(chan RawMessage, 1000),
		stopCh:   make(chan struct{}),
	}
	for _, opt := range opts {
		opt(m)
	}
	return m
}

// Name restituisce l'identificativo del simulatore.
func (m *MockConnector) Name() string {
	return m.name
}

// Connect simula l'apertura del contatto con la miniera.
func (m *MockConnector) Connect() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.connected {
		return fmt.Errorf("mock connector %q: already connected", m.name)
	}

	if m.OnConnect != nil {
		if err := m.OnConnect(); err != nil {
			return fmt.Errorf("mock connector %q: connect failed: %w", m.name, err)
		}
	}

	m.connected = true
	return nil
}

// Subscribe registra i simboli e i canali richiesti per l'estrazione.
func (m *MockConnector) Subscribe(symbols []string, channels []string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.connected {
		return fmt.Errorf("mock connector %q: not connected", m.name)
	}

	if m.OnSubscribe != nil {
		if err := m.OnSubscribe(symbols, channels); err != nil {
			return fmt.Errorf("mock connector %q: subscribe failed: %w", m.name, err)
		}
	}

	m.Symbols = symbols
	m.Channels = channels
	m.subscribed = true

	// Start auto-generation if configured.
	if m.GenerateInterval > 0 {
		go m.generateLoop()
	}

	return nil
}

// ReadMessage restituisce il prossimo carico dal buffer interno.
func (m *MockConnector) ReadMessage() (RawMessage, error) {
	select {
	case msg, ok := <-m.messages:
		if !ok {
			return RawMessage{}, fmt.Errorf("mock connector %q: closed", m.name)
		}
		return msg, nil
	case <-m.stopCh:
		return RawMessage{}, fmt.Errorf("mock connector %q: stopped", m.name)
	}
}

// Enqueue inserisce un carico nel buffer per simulare l'arrivo di materiale.
func (m *MockConnector) Enqueue(msg RawMessage) {
	select {
	case m.messages <- msg:
	default:
		// Buffer full; drop the message to avoid blocking in tests.
	}
}

// EnqueueJSON è una scorciatoia per iniettare dati in formato JSON.
func (m *MockConnector) EnqueueJSON(exchange, symbol, channel string, jsonData []byte) {
	m.Enqueue(RawMessage{
		Exchange:  exchange,
		Symbol:    symbol,
		Channel:   channel,
		Data:      jsonData,
		Timestamp: time.Now().UnixNano(),
	})
}

// Close interrompe il simulatore e svuota i nastri trasportatori.
func (m *MockConnector) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.closed {
		return nil
	}

	m.closed = true
	m.connected = false
	close(m.stopCh)

	return nil
}

// IsConnected returns the current connection state (for test assertions).
func (m *MockConnector) IsConnected() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.connected
}

// IsSubscribed returns whether Subscribe has been called (for test assertions).
func (m *MockConnector) IsSubscribed() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.subscribed
}

// generateLoop produce messaggi sintetici all'intervallo stabilito.
func (m *MockConnector) generateLoop() {
	ticker := time.NewTicker(m.GenerateInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			m.mu.Lock()
			symbols := m.Symbols
			seqNum := m.seqNum
			m.seqNum++
			m.mu.Unlock()

			for _, sym := range symbols {
				var msg RawMessage
				if m.MessageFactory != nil {
					msg = m.MessageFactory(sym, seqNum)
				} else {
					msg = m.defaultMessage(sym, seqNum)
				}

				select {
				case m.messages <- msg:
				default:
					// Buffer full; skip this tick.
				}
			}

		case <-m.stopCh:
			return
		}
	}
}

// defaultMessage crea un semplice messaggio di scambio sintetico.
func (m *MockConnector) defaultMessage(symbol string, seqNum int) RawMessage {
	data := fmt.Sprintf(
		`{"e":"trade","s":"%s","p":"50000.00","q":"0.001","T":%d,"seq":%d}`,
		symbol, time.Now().UnixMilli(), seqNum,
	)

	return RawMessage{
		Exchange:  "mock",
		Symbol:    symbol,
		Channel:   "trade",
		Data:      []byte(data),
		Timestamp: time.Now().UnixNano(),
	}
}
