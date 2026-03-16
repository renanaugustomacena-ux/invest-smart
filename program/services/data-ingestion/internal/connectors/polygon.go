package connectors

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"math"
	"math/rand"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

// ────────────────────────────────────────────────────────────────────────────
// Message Types
// ────────────────────────────────────────────────────────────────────────────

// PolygonMessage rappresenta il tipo base di messaggio Polygon.io.
type PolygonMessage struct {
	EventType string `json:"ev"`
}

// PolygonAuthMessage è il messaggio di autenticazione.
type PolygonAuthMessage struct {
	Action string `json:"action"`
	Params string `json:"params"`
}

// PolygonSubscribeMessage è il messaggio di sottoscrizione.
type PolygonSubscribeMessage struct {
	Action string `json:"action"`
	Params string `json:"params"`
}

// PolygonStatusMessage rappresenta un messaggio di stato dal server.
type PolygonStatusMessage struct {
	EventType string `json:"ev"`
	Status    string `json:"status"`
	Message   string `json:"message"`
}

// PolygonCurrencyTrade rappresenta un singolo tick Forex.
type PolygonCurrencyTrade struct {
	EventType string `json:"ev"`
	Pair      string `json:"p"`
}

// PolygonCurrencyAggregate rappresenta una candela aggregata.
type PolygonCurrencyAggregate struct {
	EventType string `json:"ev"`
	Pair      string `json:"pair"`
}

// ────────────────────────────────────────────────────────────────────────────
// Connection State
// ────────────────────────────────────────────────────────────────────────────

// connState rappresenta lo stato della connessione WebSocket.
type connState int32

const (
	stateDisconnected connState = iota
	stateConnecting
	stateConnected
	stateReconnecting
	stateClosed
)

// ────────────────────────────────────────────────────────────────────────────
// PolygonConnector
// ────────────────────────────────────────────────────────────────────────────

// PolygonConnector implementa l'interfaccia Connector per Polygon.io Forex/CFD.
//
// Caratteristiche:
//   - Reconnection automatica con exponential backoff + jitter
//   - Auto-resubscribe dopo ogni reconnection
//   - Circuit breaker dopo N tentativi consecutivi falliti
//   - Message buffering asincrono
//   - Graceful shutdown
type PolygonConnector struct {
	apiKey  string
	wsURL   string
	symbols []string
	config  ConnectorConfig

	conn  *websocket.Conn
	mu    sync.Mutex
	state atomic.Int32 // connState

	authenticated bool

	// lastSubscription memorizza l'ultima sottoscrizione per auto-resubscribe.
	lastSubscription struct {
		symbols  []string
		channels []string
	}

	// reconnectAttempts conta i tentativi consecutivi di riconnessione.
	reconnectAttempts atomic.Int32
	maxReconnects     int

	// msgChan bufferizza i messaggi in arrivo.
	msgChan chan RawMessage
	errChan chan error

	// droppedMessages conta i messaggi scartati per backpressure.
	droppedMessages atomic.Uint64

	// stopChan segnala l'arresto delle goroutine interne.
	stopChan chan struct{}
}

// NewPolygonConnector crea un nuovo connettore per Polygon.io.
func NewPolygonConnector(apiKey, wsURL string, symbols []string) *PolygonConnector {
	if apiKey == "" {
		slog.Error("polygon: POLYGON_API_KEY is empty — authentication will fail")
	} else if len(apiKey) < 6 {
		slog.Warn("polygon: POLYGON_API_KEY looks invalid (too short)", slog.Int("length", len(apiKey)))
	}

	if wsURL == "" {
		wsURL = "wss://socket.polygon.io/forex"
	}

	cfg := DefaultConnectorConfig()
	cfg.WSURL = wsURL
	cfg.Symbols = symbols
	cfg.PingInterval = 30 * time.Second
	cfg.ReconnectDelay = 2 * time.Second
	cfg.MaxReconnectDelay = 60 * time.Second

	p := &PolygonConnector{
		apiKey:        apiKey,
		wsURL:         wsURL,
		symbols:       symbols,
		config:        cfg,
		maxReconnects: 50,
		msgChan:       make(chan RawMessage, 256),
		errChan:       make(chan error, 10),
		stopChan:      make(chan struct{}),
	}
	p.state.Store(int32(stateDisconnected))
	return p
}

// Name restituisce l'identificativo del connettore.
func (p *PolygonConnector) Name() string {
	return "polygon-forex"
}

// Connect stabilisce la connessione WebSocket con Polygon.io e si autentica.
func (p *PolygonConnector) Connect() error {
	if connState(p.state.Load()) == stateClosed {
		return fmt.Errorf("polygon connector: connector has been closed")
	}

	return p.dialAndAuth()
}

// Subscribe sottoscrive ai simboli specificati e memorizza la sottoscrizione
// per auto-resubscribe dopo una riconnessione.
func (p *PolygonConnector) Subscribe(symbols []string, channels []string) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	// Memorizza per auto-resubscribe dopo reconnection.
	p.lastSubscription.symbols = symbols
	p.lastSubscription.channels = channels

	return p.sendSubscription(symbols, channels)
}

// ReadMessage legge il prossimo messaggio dalla coda interna.
// Blocca finché un messaggio è disponibile o il connettore è chiuso.
func (p *PolygonConnector) ReadMessage() (RawMessage, error) {
	select {
	case msg := <-p.msgChan:
		return msg, nil
	case err := <-p.errChan:
		return RawMessage{}, err
	case <-p.stopChan:
		return RawMessage{}, fmt.Errorf("polygon connector: closed")
	}
}

// Close chiude la connessione e ferma tutte le goroutine interne.
func (p *PolygonConnector) Close() error {
	if !p.state.CompareAndSwap(int32(stateConnected), int32(stateClosed)) {
		// Prova anche da altri stati.
		p.state.Store(int32(stateClosed))
	}

	// Segnala a tutte le goroutine di fermarsi.
	select {
	case <-p.stopChan:
		// Già chiuso.
	default:
		close(p.stopChan)
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	return p.closeConn()
}

// ────────────────────────────────────────────────────────────────────────────
// Connection Management
// ────────────────────────────────────────────────────────────────────────────

// dialAndAuth esegue la connessione WebSocket, l'autenticazione, e avvia
// le goroutine di read e ping.
func (p *PolygonConnector) dialAndAuth() error {
	p.state.Store(int32(stateConnecting))

	p.mu.Lock()
	defer p.mu.Unlock()

	// Chiude la vecchia connessione se presente.
	_ = p.closeConn()

	u, err := url.Parse(p.wsURL)
	if err != nil {
		p.state.Store(int32(stateDisconnected))
		return fmt.Errorf("polygon connector: invalid URL %q: %w", p.wsURL, err)
	}

	dialer := websocket.Dialer{
		HandshakeTimeout: 15 * time.Second,
	}

	conn, _, err := dialer.Dial(u.String(), nil)
	if err != nil {
		p.state.Store(int32(stateDisconnected))
		return fmt.Errorf("polygon connector: dial failed: %w", err)
	}

	p.conn = conn
	p.authenticated = false

	_ = conn.SetReadDeadline(time.Now().Add(90 * time.Second))
	conn.SetPongHandler(func(appData string) error {
		return conn.SetReadDeadline(time.Now().Add(90 * time.Second))
	})

	// Autenticazione.
	authMsg := PolygonAuthMessage{Action: "auth", Params: p.apiKey}
	if err := p.sendJSON(authMsg); err != nil {
		_ = p.closeConn()
		p.state.Store(int32(stateDisconnected))
		return fmt.Errorf("polygon connector: auth send failed: %w", err)
	}

	if err := p.waitForAuth(); err != nil {
		_ = p.closeConn()
		p.state.Store(int32(stateDisconnected))
		return fmt.Errorf("polygon connector: auth failed: %w", err)
	}

	p.state.Store(int32(stateConnected))
	p.reconnectAttempts.Store(0)

	// Avvia goroutine.
	go p.readLoop()
	go p.pingLoop()

	return nil
}

// reconnect esegue la logica di riconnessione con exponential backoff + jitter.
// Viene chiamata automaticamente quando la readLoop rileva una disconnessione.
func (p *PolygonConnector) reconnect() {
	if connState(p.state.Load()) == stateClosed {
		return
	}

	p.state.Store(int32(stateReconnecting))

	for {
		select {
		case <-p.stopChan:
			return
		default:
		}

		attempts := p.reconnectAttempts.Add(1)

		if int(attempts) > p.maxReconnects {
			p.errChan <- fmt.Errorf(
				"polygon connector: max reconnect attempts (%d) exceeded, giving up",
				p.maxReconnects,
			)
			return
		}

		// Exponential backoff con jitter.
		delay := p.backoffDelay()

		select {
		case <-time.After(delay):
		case <-p.stopChan:
			return
		}

		// Tenta la riconnessione.
		if err := p.dialAndAuth(); err != nil {
			continue
		}

		// Riconnessione riuscita — re-subscribe automatico.
		p.mu.Lock()
		syms := p.lastSubscription.symbols
		chs := p.lastSubscription.channels
		p.mu.Unlock()

		if len(syms) > 0 {
			p.mu.Lock()
			if err := p.sendSubscription(syms, chs); err != nil {
				p.mu.Unlock()
				continue
			}
			p.mu.Unlock()
		}

		return
	}
}

// backoffDelay calcola il delay con exponential backoff + jitter.
// Formula: min(base * 2^attempt + jitter, maxDelay)
func (p *PolygonConnector) backoffDelay() time.Duration {
	base := p.config.ReconnectDelay.Seconds()
	maxD := p.config.MaxReconnectDelay.Seconds()

	exp := base * math.Pow(2, float64(p.reconnectAttempts.Load()-1))
	if exp > maxD {
		exp = maxD
	}

	// Jitter: +/- 20% per evitare thundering herd.
	jitter := exp * 0.2 * (rand.Float64()*2 - 1)
	delay := exp + jitter
	if delay < 0.1 {
		delay = 0.1
	}

	return time.Duration(delay * float64(time.Second))
}

// closeConn chiude la connessione WebSocket sottostante.
// Deve essere chiamata con il mutex acquisito.
func (p *PolygonConnector) closeConn() error {
	if p.conn == nil {
		return nil
	}

	closeMsg := websocket.FormatCloseMessage(websocket.CloseNormalClosure, "")
	_ = p.conn.WriteControl(websocket.CloseMessage, closeMsg, time.Now().Add(2*time.Second))

	err := p.conn.Close()
	p.conn = nil
	p.authenticated = false
	return err
}

// ────────────────────────────────────────────────────────────────────────────
// Subscription
// ────────────────────────────────────────────────────────────────────────────

// sendSubscription invia i messaggi di sottoscrizione.
// Deve essere chiamata con il mutex acquisito.
func (p *PolygonConnector) sendSubscription(symbols []string, channels []string) error {
	if p.conn == nil || !p.authenticated {
		return fmt.Errorf("polygon connector: not connected/authenticated")
	}

	var topics []string
	for _, sym := range symbols {
		if len(channels) == 0 {
			topics = append(topics, "C."+sym)
			continue
		}
		for _, ch := range channels {
			topic := p.buildTopic(sym, ch)
			if topic != "" {
				topics = append(topics, topic)
			}
		}
	}

	if len(topics) == 0 {
		return fmt.Errorf("polygon connector: no valid topics")
	}

	return p.sendJSON(PolygonSubscribeMessage{
		Action: "subscribe",
		Params: strings.Join(topics, ","),
	})
}

// buildTopic costruisce il topic Polygon.io dal simbolo e canale MONEYMAKER.
func (p *PolygonConnector) buildTopic(symbol, channel string) string {
	if !strings.HasPrefix(symbol, "C:") && !strings.HasPrefix(symbol, "CA:") {
		symbol = "C:" + symbol
	}

	switch channel {
	case "trade", "tick":
		return "C." + symbol
	case "aggregate", "candle", "kline":
		return "CA." + symbol
	case "quote":
		return "CQ." + symbol
	default:
		return channel + "." + symbol
	}
}

// ────────────────────────────────────────────────────────────────────────────
// Internal Loops
// ────────────────────────────────────────────────────────────────────────────

// readLoop legge messaggi dal WebSocket. Se la connessione cade, avvia il
// processo di riconnessione automatica.
func (p *PolygonConnector) readLoop() {
	for {
		p.mu.Lock()
		conn := p.conn
		p.mu.Unlock()

		if conn == nil || connState(p.state.Load()) == stateClosed {
			return
		}

		_, data, err := conn.ReadMessage()
		if err != nil {
			if connState(p.state.Load()) == stateClosed {
				return
			}
			// Connessione persa: avvia reconnection.
			go p.reconnect()
			return
		}

		now := time.Now().UnixNano()

		var messages []json.RawMessage
		if err := json.Unmarshal(data, &messages); err != nil {
			messages = []json.RawMessage{json.RawMessage(data)}
		}

		for _, msgData := range messages {
			var base PolygonMessage
			if err := json.Unmarshal(msgData, &base); err != nil {
				continue
			}

			if base.EventType == "status" {
				continue
			}

			symbol, channel := p.parseEventType(base.EventType, msgData)

			raw := RawMessage{
				Exchange:  "polygon",
				Symbol:    symbol,
				Channel:   channel,
				Data:      []byte(msgData),
				Timestamp: now,
			}

			select {
			case p.msgChan <- raw:
			default:
				// Buffer pieno: scarta il più vecchio per fare spazio.
				dropped := p.droppedMessages.Add(1)
				if dropped == 1 || dropped%100 == 0 {
					slog.Warn("polygon message dropped (buffer full)",
						slog.Uint64("total_dropped", dropped),
						slog.String("symbol", symbol),
						slog.String("channel", channel),
					)
				}
				select {
				case <-p.msgChan:
				default:
				}
				p.msgChan <- raw
			}
		}
	}
}

// parseEventType estrae simbolo e canale dal tipo di evento e payload.
func (p *PolygonConnector) parseEventType(eventType string, data json.RawMessage) (symbol, channel string) {
	switch eventType {
	case "C":
		var trade PolygonCurrencyTrade
		if err := json.Unmarshal(data, &trade); err == nil && trade.Pair != "" {
			return trade.Pair, "trade"
		}
	case "CA":
		var agg PolygonCurrencyAggregate
		if err := json.Unmarshal(data, &agg); err == nil && agg.Pair != "" {
			return agg.Pair, "aggregate"
		}
	case "CQ":
		var quote struct {
			Pair string `json:"p"`
		}
		if err := json.Unmarshal(data, &quote); err == nil && quote.Pair != "" {
			return quote.Pair, "quote"
		}
	}
	return unknownValue, unknownValue
}

// pingLoop invia ping frames periodici per mantenere viva la connessione.
func (p *PolygonConnector) pingLoop() {
	ticker := time.NewTicker(p.config.PingInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p.mu.Lock()
			conn := p.conn
			state := connState(p.state.Load())
			p.mu.Unlock()

			if state == stateClosed || conn == nil {
				return
			}

			if err := conn.WriteControl(websocket.PingMessage, nil, time.Now().Add(5*time.Second)); err != nil {
				return
			}
		case <-p.stopChan:
			return
		}
	}
}

// ────────────────────────────────────────────────────────────────────────────
// Utilities
// ────────────────────────────────────────────────────────────────────────────

// DroppedMessages restituisce il numero totale di messaggi scartati per backpressure.
func (p *PolygonConnector) DroppedMessages() uint64 {
	return p.droppedMessages.Load()
}

// sendJSON invia un messaggio JSON al WebSocket.
func (p *PolygonConnector) sendJSON(v interface{}) error {
	data, err := json.Marshal(v)
	if err != nil {
		return fmt.Errorf("marshal json: %w", err)
	}
	return p.conn.WriteMessage(websocket.TextMessage, data)
}

// waitForAuth attende il messaggio di conferma autenticazione dal server.
func (p *PolygonConnector) waitForAuth() error {
	timeout := time.After(10 * time.Second)

	for {
		select {
		case <-timeout:
			return fmt.Errorf("authentication timeout")
		default:
		}

		_, data, err := p.conn.ReadMessage()
		if err != nil {
			return fmt.Errorf("read auth response: %w", err)
		}

		var messages []PolygonStatusMessage
		if err := json.Unmarshal(data, &messages); err != nil {
			var msg PolygonStatusMessage
			if err := json.Unmarshal(data, &msg); err != nil {
				continue
			}
			messages = []PolygonStatusMessage{msg}
		}

		for _, msg := range messages {
			if msg.EventType == "status" {
				if msg.Status == "auth_success" {
					p.authenticated = true
					return nil
				}
				if msg.Status == "auth_failed" || msg.Status == "error" {
					return fmt.Errorf("auth rejected: %s", msg.Message)
				}
			}
		}
	}
}
