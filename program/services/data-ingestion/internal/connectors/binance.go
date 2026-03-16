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

// BinanceConnector implementa l'interfaccia Connector per Binance Spot.
// Si connette ai flussi combinati di Binance — "il Cacciatore esperto di Binance".
//
// Caratteristiche:
//   - Reconnection automatica con exponential backoff + jitter
//   - Auto-resubscribe dopo ogni reconnection
//   - Message buffering asincrono
//   - Graceful shutdown
type BinanceConnector struct {
	wsURL   string
	symbols []string
	config  ConnectorConfig

	conn  *websocket.Conn
	mu    sync.Mutex
	state atomic.Int32 // connState

	// subscriptionID viene incrementato per ogni richiesta di iscrizione per
	// coordinare le conferme di Binance.
	subscriptionID int

	// lastSubscription memorizza l'ultima sottoscrizione per auto-resubscribe.
	lastSubscription struct {
		symbols  []string
		channels []string
	}

	// reconnectAttempts conta i tentativi consecutivi di riconnessione.
	reconnectAttempts int
	maxReconnects     int

	// msgChan bufferizza i messaggi in arrivo.
	msgChan chan RawMessage
	errChan chan error

	// droppedMessages conta i messaggi scartati per backpressure.
	droppedMessages atomic.Uint64

	// stopChan segnala l'arresto delle goroutine interne.
	stopChan chan struct{}
}

// binanceSubscribeRequest è il carico utile per le iscrizioni ai flussi di Binance.
type binanceSubscribeRequest struct {
	Method string   `json:"method"`
	Params []string `json:"params"`
	ID     int      `json:"id"`
}

// NewBinanceConnector crea un nuovo Cacciatore per Binance.
func NewBinanceConnector(wsURL string, symbols []string) *BinanceConnector {
	cfg := DefaultConnectorConfig()
	cfg.WSURL = wsURL
	cfg.Symbols = symbols
	cfg.PingInterval = 20 * time.Second // Binance chiude dopo 24h; ping frequenti.
	cfg.ReconnectDelay = 1 * time.Second
	cfg.MaxReconnectDelay = 5 * time.Minute

	b := &BinanceConnector{
		wsURL:         wsURL,
		symbols:       symbols,
		config:        cfg,
		maxReconnects: 50,
		msgChan:       make(chan RawMessage, 4096),
		errChan:       make(chan error, 10),
		stopChan:      make(chan struct{}),
	}
	b.state.Store(int32(stateDisconnected))
	return b
}

// Name restituisce l'identificativo del cacciatore.
func (b *BinanceConnector) Name() string {
	return "binance-spot"
}

// Connect stabilisce la connessione con Binance — "inizia la battuta".
func (b *BinanceConnector) Connect() error {
	if connState(b.state.Load()) == stateClosed {
		return fmt.Errorf("binance connector: connector has been closed")
	}

	return b.dialAndSetup()
}

// Subscribe richiede l'iscrizione per simboli e canali.
// I canali vengono mappati sui nomi dei flussi di Binance.
// Memorizza la sottoscrizione per auto-resubscribe dopo reconnection.
func (b *BinanceConnector) Subscribe(symbols []string, channels []string) error {
	b.mu.Lock()
	defer b.mu.Unlock()

	// Memorizza per auto-resubscribe dopo reconnection.
	b.lastSubscription.symbols = symbols
	b.lastSubscription.channels = channels

	return b.sendSubscription(symbols, channels)
}

// ReadMessage legge il prossimo messaggio dalla coda interna.
// Blocca finché un messaggio è disponibile o il connettore è chiuso.
func (b *BinanceConnector) ReadMessage() (RawMessage, error) {
	select {
	case msg := <-b.msgChan:
		return msg, nil
	case err := <-b.errChan:
		return RawMessage{}, err
	case <-b.stopChan:
		return RawMessage{}, fmt.Errorf("binance connector: closed")
	}
}

// Close chiude la connessione con Binance — "fine caccia".
func (b *BinanceConnector) Close() error {
	if !b.state.CompareAndSwap(int32(stateConnected), int32(stateClosed)) {
		b.state.Store(int32(stateClosed))
	}

	// Segnala a tutte le goroutine di fermarsi.
	select {
	case <-b.stopChan:
		// Già chiuso.
	default:
		close(b.stopChan)
	}

	b.mu.Lock()
	defer b.mu.Unlock()
	return b.closeConn()
}

// ────────────────────────────────────────────────────────────────────────────
// Connection Management
// ────────────────────────────────────────────────────────────────────────────

// dialAndSetup esegue la connessione WebSocket e avvia le goroutine di read e ping.
func (b *BinanceConnector) dialAndSetup() error {
	b.state.Store(int32(stateConnecting))

	b.mu.Lock()
	defer b.mu.Unlock()

	// Chiude la vecchia connessione se presente.
	_ = b.closeConn()

	u, err := url.Parse(b.wsURL)
	if err != nil {
		b.state.Store(int32(stateDisconnected))
		return fmt.Errorf("binance connector: invalid URL %q: %w", b.wsURL, err)
	}

	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}

	conn, _, err := dialer.Dial(u.String(), nil)
	if err != nil {
		b.state.Store(int32(stateDisconnected))
		return fmt.Errorf("binance connector: dial failed: %w", err)
	}

	// Imposta deadline e gestore pong per il mantenimento della linea.
	_ = conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	conn.SetPongHandler(func(appData string) error {
		return conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	})

	b.conn = conn
	b.state.Store(int32(stateConnected))
	b.reconnectAttempts = 0

	// Avvia goroutine.
	go b.readLoop()
	go b.pingLoop()

	return nil
}

// reconnect esegue la logica di riconnessione con exponential backoff + jitter.
// Viene chiamata automaticamente quando la readLoop rileva una disconnessione.
func (b *BinanceConnector) reconnect() {
	if connState(b.state.Load()) == stateClosed {
		return
	}

	b.state.Store(int32(stateReconnecting))

	for {
		select {
		case <-b.stopChan:
			return
		default:
		}

		b.reconnectAttempts++

		if b.reconnectAttempts > b.maxReconnects {
			b.errChan <- fmt.Errorf(
				"binance connector: max reconnect attempts (%d) exceeded, giving up",
				b.maxReconnects,
			)
			return
		}

		// Exponential backoff con jitter.
		delay := b.backoffDelay()

		select {
		case <-time.After(delay):
		case <-b.stopChan:
			return
		}

		// Tenta la riconnessione.
		if err := b.dialAndSetup(); err != nil {
			continue
		}

		// Riconnessione riuscita — re-subscribe automatico.
		b.mu.Lock()
		syms := b.lastSubscription.symbols
		chs := b.lastSubscription.channels
		b.mu.Unlock()

		if len(syms) > 0 {
			b.mu.Lock()
			if err := b.sendSubscription(syms, chs); err != nil {
				b.mu.Unlock()
				continue
			}
			b.mu.Unlock()
		}

		return
	}
}

// backoffDelay calcola il delay con exponential backoff + jitter.
func (b *BinanceConnector) backoffDelay() time.Duration {
	base := b.config.ReconnectDelay.Seconds()
	maxD := b.config.MaxReconnectDelay.Seconds()

	exp := base * math.Pow(2, float64(b.reconnectAttempts-1))
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
func (b *BinanceConnector) closeConn() error {
	if b.conn == nil {
		return nil
	}

	closeMsg := websocket.FormatCloseMessage(websocket.CloseNormalClosure, "shutting down")
	_ = b.conn.WriteControl(websocket.CloseMessage, closeMsg, time.Now().Add(3*time.Second))

	err := b.conn.Close()
	b.conn = nil
	return err
}

// ────────────────────────────────────────────────────────────────────────────
// Subscription
// ────────────────────────────────────────────────────────────────────────────

// sendSubscription invia i messaggi di sottoscrizione a Binance.
// Deve essere chiamata con il mutex acquisito.
func (b *BinanceConnector) sendSubscription(symbols []string, channels []string) error {
	if b.conn == nil {
		return fmt.Errorf("binance connector: not connected")
	}

	// Costruisce la lista dei flussi Binance (simboli x canali).
	var params []string
	for _, sym := range symbols {
		s := strings.ToLower(sym)
		for _, ch := range channels {
			streamName := b.toStreamName(s, ch)
			if streamName != "" {
				params = append(params, streamName)
			}
		}
	}

	if len(params) == 0 {
		return fmt.Errorf("binance connector: no valid stream names generated")
	}

	b.subscriptionID++
	req := binanceSubscribeRequest{
		Method: "SUBSCRIBE",
		Params: params,
		ID:     b.subscriptionID,
	}

	payload, err := json.Marshal(req)
	if err != nil {
		return fmt.Errorf("binance connector: marshal subscribe request: %w", err)
	}

	if err := b.conn.WriteMessage(websocket.TextMessage, payload); err != nil {
		return fmt.Errorf("binance connector: send subscribe: %w", err)
	}

	return nil
}

// ────────────────────────────────────────────────────────────────────────────
// Internal Loops
// ────────────────────────────────────────────────────────────────────────────

// readLoop legge messaggi dal WebSocket e li bufferizza su msgChan.
// Se la connessione cade, avvia il processo di riconnessione automatica.
func (b *BinanceConnector) readLoop() {
	for {
		b.mu.Lock()
		conn := b.conn
		b.mu.Unlock()

		if conn == nil || connState(b.state.Load()) == stateClosed {
			return
		}

		_, data, err := conn.ReadMessage()
		if err != nil {
			if connState(b.state.Load()) == stateClosed {
				return
			}
			// Connessione persa: avvia reconnection.
			go b.reconnect()
			return
		}

		now := time.Now().UnixNano()
		symbol, channel := b.parseStreamEnvelope(data)

		raw := RawMessage{
			Exchange:  "binance",
			Symbol:    symbol,
			Channel:   channel,
			Data:      data,
			Timestamp: now,
		}

		select {
		case b.msgChan <- raw:
		default:
			// Buffer pieno: scarta il più vecchio per fare spazio.
			dropped := b.droppedMessages.Add(1)
			if dropped == 1 || dropped%100 == 0 {
				slog.Warn("binance message dropped (buffer full)",
					slog.Uint64("total_dropped", dropped),
					slog.String("symbol", symbol),
					slog.String("channel", channel),
				)
			}
			select {
			case <-b.msgChan:
			default:
			}
			b.msgChan <- raw
		}
	}
}

// pingLoop invia frame di ping periodici per tenere viva la linea.
func (b *BinanceConnector) pingLoop() {
	ticker := time.NewTicker(b.config.PingInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			b.mu.Lock()
			conn := b.conn
			st := connState(b.state.Load())
			b.mu.Unlock()

			if st == stateClosed || conn == nil {
				return
			}

			if err := conn.WriteControl(websocket.PingMessage, nil, time.Now().Add(5*time.Second)); err != nil {
				return
			}
		case <-b.stopChan:
			return
		}
	}
}

// ────────────────────────────────────────────────────────────────────────────
// Utilities
// ────────────────────────────────────────────────────────────────────────────

// DroppedMessages restituisce il numero totale di messaggi scartati per backpressure.
func (b *BinanceConnector) DroppedMessages() uint64 {
	return b.droppedMessages.Load()
}

// toStreamName mappa un canale MONEYMAKER nella convenzione di Binance.
func (b *BinanceConnector) toStreamName(symbol, channel string) string {
	switch channel {
	case "trade":
		return symbol + "@trade"
	case "depth":
		return symbol + "@depth20@100ms"
	case "kline_1m":
		return symbol + "@kline_1m"
	case "kline_5m":
		return symbol + "@kline_5m"
	case "kline_15m":
		return symbol + "@kline_15m"
	case "kline_1h":
		return symbol + "@kline_1h"
	case "ticker":
		return symbol + "@miniTicker"
	case "bookTicker":
		return symbol + "@bookTicker"
	default:
		// Consente il pass-through per i nomi di flusso raw di Binance.
		return symbol + "@" + channel
	}
}

// parseStreamEnvelope estrae simbolo e canale dall'involucro JSON di Binance.
// Supporta sia il formato combined-stream (con "stream"+"data") sia il formato
// raw (con "e"+"s" direttamente nel messaggio).
func (b *BinanceConnector) parseStreamEnvelope(data []byte) (symbol, channel string) {
	// Tentativo 1: formato combined-stream con involucro {"stream":"...","data":{...}}
	var envelope struct {
		Stream string          `json:"stream"`
		Data   json.RawMessage `json:"data"`
	}

	if err := json.Unmarshal(data, &envelope); err == nil && envelope.Stream != "" {
		parts := strings.SplitN(envelope.Stream, "@", 2)
		if len(parts) == 2 {
			return parts[0], parts[1]
		}
		return envelope.Stream, unknownValue
	}

	// Tentativo 2: formato raw senza involucro {"e":"trade","s":"BTCUSDT",...}
	var raw struct {
		EventType string `json:"e"`
		Symbol    string `json:"s"`
	}
	if err := json.Unmarshal(data, &raw); err == nil && raw.Symbol != "" {
		return strings.ToLower(raw.Symbol), raw.EventType
	}

	return unknownValue, unknownValue
}
