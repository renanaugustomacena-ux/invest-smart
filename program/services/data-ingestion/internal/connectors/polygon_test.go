package connectors

import (
	"encoding/json"
	"testing"
)

// ---------------------------------------------------------------------------
// NewPolygonConnector
// ---------------------------------------------------------------------------

func TestNewPolygonConnectorName(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", []string{"C:XAUUSD"})
	if p.Name() != "polygon-forex" {
		t.Errorf("Name() = %q, want polygon-forex", p.Name())
	}
}

func TestNewPolygonConnectorDefaultURL(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	if p.wsURL != "wss://socket.polygon.io/forex" {
		t.Errorf("wsURL = %q, want default wss://socket.polygon.io/forex", p.wsURL)
	}
}

func TestNewPolygonConnectorCustomURL(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "wss://custom.example.com/ws", nil)
	if p.wsURL != "wss://custom.example.com/ws" {
		t.Errorf("wsURL = %q", p.wsURL)
	}
}

func TestNewPolygonConnectorState(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	if connState(p.state.Load()) != stateDisconnected {
		t.Error("initial state should be stateDisconnected")
	}
}

func TestNewPolygonConnectorFields(t *testing.T) {
	p := NewPolygonConnector("mykey123456", "wss://test.example.com", []string{"C:EURUSD"})
	if p.apiKey != "mykey123456" {
		t.Errorf("apiKey = %q", p.apiKey)
	}
	if len(p.symbols) != 1 {
		t.Errorf("symbols len = %d, want 1", len(p.symbols))
	}
	if p.maxReconnects != 50 {
		t.Errorf("maxReconnects = %d, want 50", p.maxReconnects)
	}
}

func TestNewPolygonConnectorChannelSizes(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	if cap(p.msgChan) != 256 {
		t.Errorf("msgChan capacity = %d, want 256", cap(p.msgChan))
	}
	if cap(p.errChan) != 10 {
		t.Errorf("errChan capacity = %d, want 10", cap(p.errChan))
	}
}

// ---------------------------------------------------------------------------
// buildTopic
// ---------------------------------------------------------------------------

func TestBuildTopicTrade(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("XAUUSD", "trade")
	if got != "C.C:XAUUSD" {
		t.Errorf("buildTopic(trade) = %q, want C.C:XAUUSD", got)
	}
}

func TestBuildTopicTick(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("EURUSD", "tick")
	if got != "C.C:EURUSD" {
		t.Errorf("buildTopic(tick) = %q, want C.C:EURUSD", got)
	}
}

func TestBuildTopicAggregate(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("GBPUSD", "aggregate")
	if got != "CA.C:GBPUSD" {
		t.Errorf("buildTopic(aggregate) = %q, want CA.C:GBPUSD", got)
	}
}

func TestBuildTopicCandle(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("USDJPY", "candle")
	if got != "CA.C:USDJPY" {
		t.Errorf("buildTopic(candle) = %q, want CA.C:USDJPY", got)
	}
}

func TestBuildTopicKline(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("AUDUSD", "kline")
	if got != "CA.C:AUDUSD" {
		t.Errorf("buildTopic(kline) = %q, want CA.C:AUDUSD", got)
	}
}

func TestBuildTopicQuote(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("NZDUSD", "quote")
	if got != "CQ.C:NZDUSD" {
		t.Errorf("buildTopic(quote) = %q, want CQ.C:NZDUSD", got)
	}
}

func TestBuildTopicUnknownChannel(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("USDCHF", "customchannel")
	if got != "customchannel.C:USDCHF" {
		t.Errorf("buildTopic(custom) = %q, want customchannel.C:USDCHF", got)
	}
}

func TestBuildTopicWithCPrefix(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	// Symbol already has C: prefix — should not double-prefix
	got := p.buildTopic("C:XAUUSD", "trade")
	if got != "C.C:XAUUSD" {
		t.Errorf("buildTopic with C: prefix = %q, want C.C:XAUUSD", got)
	}
}

func TestBuildTopicWithCAPrefix(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	got := p.buildTopic("CA:XAUUSD", "trade")
	if got != "C.CA:XAUUSD" {
		t.Errorf("buildTopic with CA: prefix = %q, want C.CA:XAUUSD", got)
	}
}

// ---------------------------------------------------------------------------
// parseEventType
// ---------------------------------------------------------------------------

func TestParseEventTypeTrade(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	data := json.RawMessage(`{"ev":"C","p":"EUR/USD","x":1,"a":1.1234,"b":1.1230,"t":1609459200000}`)
	symbol, channel := p.parseEventType("C", data)
	if symbol != "EUR/USD" {
		t.Errorf("symbol = %q, want EUR/USD", symbol)
	}
	if channel != "trade" {
		t.Errorf("channel = %q, want trade", channel)
	}
}

func TestParseEventTypeAggregate(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	data := json.RawMessage(`{"ev":"CA","pair":"GBP/USD","o":1.35,"c":1.36,"h":1.37,"l":1.34,"v":1000}`)
	symbol, channel := p.parseEventType("CA", data)
	if symbol != "GBP/USD" {
		t.Errorf("symbol = %q, want GBP/USD", symbol)
	}
	if channel != "aggregate" {
		t.Errorf("channel = %q, want aggregate", channel)
	}
}

func TestParseEventTypeQuote(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	data := json.RawMessage(`{"ev":"CQ","p":"USD/JPY","a":110.5,"b":110.4}`)
	symbol, channel := p.parseEventType("CQ", data)
	if symbol != "USD/JPY" {
		t.Errorf("symbol = %q, want USD/JPY", symbol)
	}
	if channel != "quote" {
		t.Errorf("channel = %q, want quote", channel)
	}
}

func TestParseEventTypeUnknown(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	data := json.RawMessage(`{"ev":"X","something":"data"}`)
	symbol, channel := p.parseEventType("X", data)
	if symbol != unknownValue {
		t.Errorf("symbol = %q, want %q", symbol, unknownValue)
	}
	if channel != unknownValue {
		t.Errorf("channel = %q, want %q", channel, unknownValue)
	}
}

func TestParseEventTypeTradeInvalidJSON(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	data := json.RawMessage(`{invalid}`)
	symbol, channel := p.parseEventType("C", data)
	if symbol != unknownValue {
		t.Errorf("symbol = %q, want %q", symbol, unknownValue)
	}
	if channel != unknownValue {
		t.Errorf("channel = %q, want %q", channel, unknownValue)
	}
}

func TestParseEventTypeTradeEmptyPair(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	data := json.RawMessage(`{"ev":"C","p":""}`)
	symbol, channel := p.parseEventType("C", data)
	if symbol != unknownValue {
		t.Errorf("symbol = %q, want %q for empty pair", symbol, unknownValue)
	}
	if channel != unknownValue {
		t.Errorf("channel = %q, want %q for empty pair", channel, unknownValue)
	}
}

// ---------------------------------------------------------------------------
// backoffDelay
// ---------------------------------------------------------------------------

func TestPolygonBackoffDelayPositive(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	p.reconnectAttempts.Store(1)
	delay := p.backoffDelay()
	if delay <= 0 {
		t.Errorf("backoffDelay should be positive, got %v", delay)
	}
}

func TestPolygonBackoffDelayCapped(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	p.reconnectAttempts.Store(100)
	delay := p.backoffDelay()
	maxAllowed := p.config.MaxReconnectDelay + p.config.MaxReconnectDelay/5 + 1
	if delay > maxAllowed {
		t.Errorf("backoffDelay = %v exceeds max %v", delay, maxAllowed)
	}
}

// ---------------------------------------------------------------------------
// DroppedMessages
// ---------------------------------------------------------------------------

func TestPolygonDroppedMessagesInitiallyZero(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	if p.DroppedMessages() != 0 {
		t.Errorf("DroppedMessages = %d, want 0", p.DroppedMessages())
	}
}

// ---------------------------------------------------------------------------
// ConnectOnClosedConnector
// ---------------------------------------------------------------------------

func TestPolygonConnectOnClosedErrors(t *testing.T) {
	p := NewPolygonConnector("test-api-key-123", "", nil)
	p.state.Store(int32(stateClosed))
	err := p.Connect()
	if err == nil {
		t.Error("Connect on closed connector should error")
	}
}

// ---------------------------------------------------------------------------
// Polygon message types — JSON serialization
// ---------------------------------------------------------------------------

func TestPolygonAuthMessageJSON(t *testing.T) {
	msg := PolygonAuthMessage{Action: "auth", Params: "my-api-key"}
	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	var parsed map[string]string
	json.Unmarshal(data, &parsed)
	if parsed["action"] != "auth" {
		t.Errorf("action = %q, want auth", parsed["action"])
	}
	if parsed["params"] != "my-api-key" {
		t.Errorf("params = %q, want my-api-key", parsed["params"])
	}
}

func TestPolygonSubscribeMessageJSON(t *testing.T) {
	msg := PolygonSubscribeMessage{Action: "subscribe", Params: "C.C:XAUUSD,C.C:EURUSD"}
	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	var parsed map[string]string
	json.Unmarshal(data, &parsed)
	if parsed["action"] != "subscribe" {
		t.Errorf("action = %q, want subscribe", parsed["action"])
	}
}

// ---------------------------------------------------------------------------
// DefaultConnectorConfig
// ---------------------------------------------------------------------------

func TestDefaultConnectorConfigValues(t *testing.T) {
	cfg := DefaultConnectorConfig()
	if cfg.ReconnectDelay.Seconds() != 1 {
		t.Errorf("ReconnectDelay = %v, want 1s", cfg.ReconnectDelay)
	}
	if cfg.MaxReconnectDelay.Seconds() != 60 {
		t.Errorf("MaxReconnectDelay = %v, want 60s", cfg.MaxReconnectDelay)
	}
	if cfg.PingInterval.Seconds() != 30 {
		t.Errorf("PingInterval = %v, want 30s", cfg.PingInterval)
	}
}

// ---------------------------------------------------------------------------
// RawMessage.String()
// ---------------------------------------------------------------------------

func TestRawMessageString(t *testing.T) {
	msg := RawMessage{
		Exchange:  "binance",
		Symbol:    "btcusdt",
		Channel:   "trade",
		Data:      []byte(`{"price":"50000"}`),
		Timestamp: 1609459200000000000, // 2021-01-01T00:00:00Z
	}
	s := msg.String()
	if s == "" {
		t.Error("String() should return non-empty")
	}
	if !stringContains(s, "binance") {
		t.Error("String() should contain exchange")
	}
	if !stringContains(s, "btcusdt") {
		t.Error("String() should contain symbol")
	}
	if !stringContains(s, "trade") {
		t.Error("String() should contain channel")
	}
}

func stringContains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
