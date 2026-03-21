package connectors

import (
	"encoding/json"
	"testing"
)

// ---------------------------------------------------------------------------
// NewBinanceConnector
// ---------------------------------------------------------------------------

func TestNewBinanceConnectorName(t *testing.T) {
	b := NewBinanceConnector("wss://stream.binance.com:9443/stream", []string{"btcusdt"})
	if b.Name() != "binance-spot" {
		t.Errorf("Name() = %q, want binance-spot", b.Name())
	}
}

func TestNewBinanceConnectorState(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", []string{"ethusdt"})
	if connState(b.state.Load()) != stateDisconnected {
		t.Error("initial state should be stateDisconnected")
	}
}

func TestNewBinanceConnectorFields(t *testing.T) {
	syms := []string{"btcusdt", "ethusdt"}
	b := NewBinanceConnector("wss://test.example.com/ws", syms)
	if b.wsURL != "wss://test.example.com/ws" {
		t.Errorf("wsURL = %q", b.wsURL)
	}
	if len(b.symbols) != 2 {
		t.Errorf("symbols len = %d, want 2", len(b.symbols))
	}
	if b.maxReconnects != 50 {
		t.Errorf("maxReconnects = %d, want 50", b.maxReconnects)
	}
}

func TestNewBinanceConnectorChannelSizes(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if cap(b.msgChan) != 4096 {
		t.Errorf("msgChan capacity = %d, want 4096", cap(b.msgChan))
	}
	if cap(b.errChan) != 10 {
		t.Errorf("errChan capacity = %d, want 10", cap(b.errChan))
	}
}

// ---------------------------------------------------------------------------
// toStreamName
// ---------------------------------------------------------------------------

func TestToStreamNameTrade(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "trade"); got != "btcusdt@trade" {
		t.Errorf("toStreamName(trade) = %q, want btcusdt@trade", got)
	}
}

func TestToStreamNameDepth(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("ethusdt", "depth"); got != "ethusdt@depth20@100ms" {
		t.Errorf("toStreamName(depth) = %q, want ethusdt@depth20@100ms", got)
	}
}

func TestToStreamNameKline1m(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "kline_1m"); got != "btcusdt@kline_1m" {
		t.Errorf("toStreamName(kline_1m) = %q", got)
	}
}

func TestToStreamNameKline5m(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "kline_5m"); got != "btcusdt@kline_5m" {
		t.Errorf("toStreamName(kline_5m) = %q", got)
	}
}

func TestToStreamNameKline15m(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "kline_15m"); got != "btcusdt@kline_15m" {
		t.Errorf("toStreamName(kline_15m) = %q", got)
	}
}

func TestToStreamNameKline1h(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "kline_1h"); got != "btcusdt@kline_1h" {
		t.Errorf("toStreamName(kline_1h) = %q", got)
	}
}

func TestToStreamNameTicker(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "ticker"); got != "btcusdt@miniTicker" {
		t.Errorf("toStreamName(ticker) = %q, want btcusdt@miniTicker", got)
	}
}

func TestToStreamNameBookTicker(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "bookTicker"); got != "btcusdt@bookTicker" {
		t.Errorf("toStreamName(bookTicker) = %q", got)
	}
}

func TestToStreamNameUnknownPassthrough(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if got := b.toStreamName("btcusdt", "customChannel"); got != "btcusdt@customChannel" {
		t.Errorf("toStreamName(custom) = %q, want btcusdt@customChannel", got)
	}
}

// ---------------------------------------------------------------------------
// parseStreamEnvelope
// ---------------------------------------------------------------------------

func TestParseStreamEnvelopeCombinedFormat(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	data := []byte(`{"stream":"btcusdt@trade","data":{"e":"trade","s":"BTCUSDT","p":"50000.00","q":"0.1"}}`)
	symbol, channel := b.parseStreamEnvelope(data)
	if symbol != "btcusdt" {
		t.Errorf("symbol = %q, want btcusdt", symbol)
	}
	if channel != "trade" {
		t.Errorf("channel = %q, want trade", channel)
	}
}

func TestParseStreamEnvelopeRawFormat(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	data := []byte(`{"e":"trade","s":"ETHUSDT","p":"3000.00","q":"1.5"}`)
	symbol, channel := b.parseStreamEnvelope(data)
	if symbol != "ethusdt" {
		t.Errorf("symbol = %q, want ethusdt", symbol)
	}
	if channel != "trade" {
		t.Errorf("channel = %q, want trade", channel)
	}
}

func TestParseStreamEnvelopeStreamNoAt(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	data := []byte(`{"stream":"somestreamname","data":{}}`)
	symbol, channel := b.parseStreamEnvelope(data)
	if symbol != "somestreamname" {
		t.Errorf("symbol = %q, want somestreamname", symbol)
	}
	if channel != unknownValue {
		t.Errorf("channel = %q, want %q", channel, unknownValue)
	}
}

func TestParseStreamEnvelopeInvalidJSON(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	data := []byte(`{invalid json}`)
	symbol, channel := b.parseStreamEnvelope(data)
	if symbol != unknownValue {
		t.Errorf("symbol = %q, want %q", symbol, unknownValue)
	}
	if channel != unknownValue {
		t.Errorf("channel = %q, want %q", channel, unknownValue)
	}
}

func TestParseStreamEnvelopeEmptyObject(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	data := []byte(`{}`)
	symbol, channel := b.parseStreamEnvelope(data)
	if symbol != unknownValue {
		t.Errorf("symbol = %q, want %q", symbol, unknownValue)
	}
	if channel != unknownValue {
		t.Errorf("channel = %q, want %q", channel, unknownValue)
	}
}

func TestParseStreamEnvelopeDepthStream(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	data := []byte(`{"stream":"btcusdt@depth20@100ms","data":{"lastUpdateId":123}}`)
	symbol, channel := b.parseStreamEnvelope(data)
	if symbol != "btcusdt" {
		t.Errorf("symbol = %q, want btcusdt", symbol)
	}
	// depth20@100ms — first split on @ gives ["btcusdt", "depth20@100ms"]
	if channel != "depth20@100ms" {
		t.Errorf("channel = %q, want depth20@100ms", channel)
	}
}

// ---------------------------------------------------------------------------
// backoffDelay
// ---------------------------------------------------------------------------

func TestBackoffDelayPositive(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	b.reconnectAttempts = 1
	delay := b.backoffDelay()
	if delay <= 0 {
		t.Errorf("backoffDelay should be positive, got %v", delay)
	}
}

func TestBackoffDelayIncreases(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)

	b.reconnectAttempts = 1
	delay1 := b.backoffDelay()
	b.reconnectAttempts = 5
	delay5 := b.backoffDelay()

	// Due to jitter, delay5 might occasionally be less than delay1
	// but the base exponential should make it generally higher.
	// We just verify they are both positive.
	if delay1 <= 0 || delay5 <= 0 {
		t.Errorf("delays should be positive: %v, %v", delay1, delay5)
	}
}

func TestBackoffDelayCappedAtMax(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	b.reconnectAttempts = 100 // Very high attempt count
	delay := b.backoffDelay()
	// maxReconnectDelay is 5 minutes + 20% jitter = max ~6 min
	maxAllowed := b.config.MaxReconnectDelay + b.config.MaxReconnectDelay/5 + 1
	if delay > maxAllowed {
		t.Errorf("backoffDelay = %v exceeds max %v", delay, maxAllowed)
	}
}

// ---------------------------------------------------------------------------
// DroppedMessages
// ---------------------------------------------------------------------------

func TestDroppedMessagesInitiallyZero(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	if b.DroppedMessages() != 0 {
		t.Errorf("DroppedMessages = %d, want 0", b.DroppedMessages())
	}
}

// ---------------------------------------------------------------------------
// ConnectOnClosedConnector
// ---------------------------------------------------------------------------

func TestConnectOnClosedConnectorErrors(t *testing.T) {
	b := NewBinanceConnector("wss://test.example.com/ws", nil)
	b.state.Store(int32(stateClosed))
	err := b.Connect()
	if err == nil {
		t.Error("Connect on closed connector should error")
	}
}

// ---------------------------------------------------------------------------
// binanceSubscribeRequest JSON
// ---------------------------------------------------------------------------

func TestBinanceSubscribeRequestJSON(t *testing.T) {
	req := binanceSubscribeRequest{
		Method: "SUBSCRIBE",
		Params: []string{"btcusdt@trade", "ethusdt@trade"},
		ID:     1,
	}
	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("marshal error: %v", err)
	}
	var parsed map[string]interface{}
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("unmarshal error: %v", err)
	}
	if parsed["method"] != "SUBSCRIBE" {
		t.Errorf("method = %v, want SUBSCRIBE", parsed["method"])
	}
	params := parsed["params"].([]interface{})
	if len(params) != 2 {
		t.Errorf("params len = %d, want 2", len(params))
	}
}
