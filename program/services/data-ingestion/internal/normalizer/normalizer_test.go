package normalizer

import (
	"encoding/json"
	"testing"

	"github.com/moneymaker-v1/services/data-ingestion/internal/connectors"
	"github.com/shopspring/decimal"
)

func newTestNormalizer() *Normalizer {
	return NewNormalizer(map[string]string{
		"btcusdt":  "BTC/USDT",
		"ethusdt":  "ETH/USDT",
		"eur/usd":  "EUR/USD",
		"gbp/usd":  "GBP/USD",
		"test_sym": "TEST/SYM",
	})
}

func TestNewNormalizer(t *testing.T) {
	n := NewNormalizer(nil)
	if n == nil {
		t.Fatal("NewNormalizer returned nil")
	}
}

func TestUnsupportedExchange(t *testing.T) {
	n := newTestNormalizer()
	raw := connectors.RawMessage{
		Exchange:  "unknown_exchange",
		Data:      []byte(`{}`),
		Timestamp: 1000,
	}
	_, err := n.NormalizeRawMessage(raw)
	if err == nil {
		t.Fatal("expected error for unsupported exchange")
	}
	if got := err.Error(); got != `normalizer: unsupported exchange "unknown_exchange"` {
		t.Errorf("unexpected error message: %s", got)
	}
}

// --- Binance tests ---

func TestBinanceTradeNormalization(t *testing.T) {
	n := newTestNormalizer()
	data, _ := json.Marshal(map[string]interface{}{
		"e": "trade",
		"E": 1672515782136,
		"s": "BTCUSDT",
		"t": 12345,
		"p": "50000.50",
		"q": "0.001",
		"T": 1672515782136,
		"m": false,
	})

	raw := connectors.RawMessage{
		Exchange:  "binance",
		Data:      data,
		Timestamp: 9999,
	}

	tick, err := n.NormalizeRawMessage(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if tick.Exchange != "binance" {
		t.Errorf("expected exchange binance, got %s", tick.Exchange)
	}
	if tick.Symbol != "BTC/USDT" {
		t.Errorf("expected symbol BTC/USDT, got %s", tick.Symbol)
	}
	if tick.EventType != "trade" {
		t.Errorf("expected event_type trade, got %s", tick.EventType)
	}
	expectedPrice, _ := decimal.NewFromString("50000.50")
	if !tick.Price.Equal(expectedPrice) {
		t.Errorf("expected price 50000.50, got %s", tick.Price)
	}
	expectedQty, _ := decimal.NewFromString("0.001")
	if !tick.Quantity.Equal(expectedQty) {
		t.Errorf("expected quantity 0.001, got %s", tick.Quantity)
	}
	if tick.Side != "buy" {
		t.Errorf("expected side buy (m=false), got %s", tick.Side)
	}
	if tick.IngestTimestamp != 9999 {
		t.Errorf("expected ingest_ts 9999, got %d", tick.IngestTimestamp)
	}
	if tick.ExchangeTimestamp != 1672515782136 {
		t.Errorf("expected exchange_ts 1672515782136, got %d", tick.ExchangeTimestamp)
	}
	if tick.Extra["trade_id"] != int64(12345) {
		t.Errorf("expected trade_id 12345, got %v (%T)", tick.Extra["trade_id"], tick.Extra["trade_id"])
	}
}

func TestBinanceSellSide(t *testing.T) {
	n := newTestNormalizer()
	data, _ := json.Marshal(map[string]interface{}{
		"e": "trade",
		"E": 1000,
		"s": "ETHUSDT",
		"t": 1,
		"p": "3000.00",
		"q": "1.0",
		"T": 1000,
		"m": true, // buyer is maker => sell
	})

	tick, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "binance", Data: data, Timestamp: 1,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tick.Side != "sell" {
		t.Errorf("expected side sell (m=true), got %s", tick.Side)
	}
	if tick.Symbol != "ETH/USDT" {
		t.Errorf("expected symbol ETH/USDT, got %s", tick.Symbol)
	}
}

func TestBinanceCombinedStreamEnvelope(t *testing.T) {
	n := newTestNormalizer()
	innerData, _ := json.Marshal(map[string]interface{}{
		"e": "trade",
		"E": 1000,
		"s": "BTCUSDT",
		"t": 99,
		"p": "42000.00",
		"q": "0.5",
		"T": 1000,
		"m": false,
	})
	envelope, _ := json.Marshal(map[string]interface{}{
		"stream": "btcusdt@trade",
		"data":   json.RawMessage(innerData),
	})

	tick, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "binance", Data: envelope, Timestamp: 1,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	expectedPrice, _ := decimal.NewFromString("42000.00")
	if !tick.Price.Equal(expectedPrice) {
		t.Errorf("expected price 42000.00, got %s", tick.Price)
	}
}

func TestBinanceUnsupportedEventType(t *testing.T) {
	n := newTestNormalizer()
	data, _ := json.Marshal(map[string]interface{}{
		"e": "kline",
		"E": 1000,
		"s": "BTCUSDT",
	})

	_, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "binance", Data: data, Timestamp: 1,
	})
	if err == nil {
		t.Fatal("expected error for unsupported event type")
	}
}

func TestBinanceInvalidJSON(t *testing.T) {
	n := newTestNormalizer()
	_, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "binance", Data: []byte(`not json`), Timestamp: 1,
	})
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

func TestBinanceInvalidPrice(t *testing.T) {
	n := newTestNormalizer()
	data, _ := json.Marshal(map[string]interface{}{
		"e": "trade",
		"E": 1000,
		"s": "BTCUSDT",
		"t": 1,
		"p": "not_a_number",
		"q": "1.0",
		"T": 1000,
		"m": false,
	})
	_, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "binance", Data: data, Timestamp: 1,
	})
	if err == nil {
		t.Fatal("expected error for invalid price")
	}
}

// --- Polygon tests ---

func TestPolygonTradeNormalization(t *testing.T) {
	n := newTestNormalizer()
	data := []byte(`{"ev":"C","p":"EUR/USD","x":1,"a":1.1234,"b":1.1230,"t":1672515782123}`)

	tick, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "polygon", Data: data, Timestamp: 5000,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if tick.Exchange != "polygon" {
		t.Errorf("expected exchange polygon, got %s", tick.Exchange)
	}
	if tick.Symbol != "EUR/USD" {
		t.Errorf("expected symbol EUR/USD, got %s", tick.Symbol)
	}
	if tick.EventType != "trade" {
		t.Errorf("expected event_type trade, got %s", tick.EventType)
	}
	// Mid price = (1.1230 + 1.1234) / 2 = 1.1232
	expectedMid, _ := decimal.NewFromString("1.1232")
	if !tick.Price.Equal(expectedMid) {
		t.Errorf("expected mid price 1.1232, got %s", tick.Price)
	}
	if !tick.Quantity.Equal(decimal.Zero) {
		t.Errorf("expected zero quantity for forex, got %s", tick.Quantity)
	}
	if tick.Side != "" {
		t.Errorf("expected empty side for forex, got %s", tick.Side)
	}
	// Timestamp: ms -> ns
	if tick.ExchangeTimestamp != 1672515782123*1_000_000 {
		t.Errorf("expected exchange_ts %d, got %d", 1672515782123*1_000_000, tick.ExchangeTimestamp)
	}
	// Check spread in extras
	ask, _ := decimal.NewFromString("1.1234")
	bid, _ := decimal.NewFromString("1.1230")
	expectedSpread := ask.Sub(bid)
	if tick.Extra["spread"] != expectedSpread.String() {
		t.Errorf("expected spread %s, got %v", expectedSpread, tick.Extra["spread"])
	}
}

func TestPolygonAggregateNormalization(t *testing.T) {
	n := newTestNormalizer()
	data := []byte(`{"ev":"CA","pair":"EUR/USD","o":1.1230,"h":1.1250,"l":1.1220,"c":1.1245,"v":1000,"s":1672515780000,"e":1672515839999}`)

	tick, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "polygon", Data: data, Timestamp: 5000,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if tick.EventType != "aggregate" {
		t.Errorf("expected event_type aggregate, got %s", tick.EventType)
	}
	closeP, _ := decimal.NewFromString("1.1245")
	if !tick.Price.Equal(closeP) {
		t.Errorf("expected price (close) 1.1245, got %s", tick.Price)
	}
	vol, _ := decimal.NewFromString("1000")
	if !tick.Quantity.Equal(vol) {
		t.Errorf("expected quantity (volume) 1000, got %s", tick.Quantity)
	}
	if tick.Extra["open"] != "1.123" {
		t.Errorf("expected open 1.123, got %v", tick.Extra["open"])
	}
	if tick.Extra["high"] != "1.125" {
		t.Errorf("expected high 1.125, got %v", tick.Extra["high"])
	}
}

func TestPolygonQuoteNormalization(t *testing.T) {
	n := newTestNormalizer()
	data := []byte(`{"ev":"CQ","p":"GBP/USD","a":1.2650,"b":1.2648,"t":1672515782000}`)

	tick, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "polygon", Data: data, Timestamp: 5000,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if tick.EventType != "quote" {
		t.Errorf("expected event_type quote, got %s", tick.EventType)
	}
	ask, _ := decimal.NewFromString("1.2650")
	bid, _ := decimal.NewFromString("1.2648")
	expectedMid := bid.Add(ask).Div(decimal.NewFromInt(2))
	if !tick.Price.Equal(expectedMid) {
		t.Errorf("expected mid price %s, got %s", expectedMid, tick.Price)
	}
}

func TestPolygonUnsupportedEventType(t *testing.T) {
	n := newTestNormalizer()
	data := []byte(`{"ev":"X","p":"EUR/USD"}`)

	_, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "polygon", Data: data, Timestamp: 1,
	})
	if err == nil {
		t.Fatal("expected error for unsupported polygon event type")
	}
}

func TestPolygonInvalidJSON(t *testing.T) {
	n := newTestNormalizer()
	_, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "polygon", Data: []byte(`{broken`), Timestamp: 1,
	})
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

// --- Mock tests ---

func TestMockNormalization(t *testing.T) {
	n := newTestNormalizer()
	data, _ := json.Marshal(map[string]interface{}{
		"e":   "trade",
		"s":   "test_sym",
		"p":   "100.50",
		"q":   "10",
		"T":   1672515782000,
		"seq": 42,
	})

	tick, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "mock", Data: data, Timestamp: 7777,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if tick.Exchange != "mock" {
		t.Errorf("expected exchange mock, got %s", tick.Exchange)
	}
	if tick.Symbol != "TEST/SYM" {
		t.Errorf("expected symbol TEST/SYM, got %s", tick.Symbol)
	}
	if tick.Side != "buy" {
		t.Errorf("expected side buy, got %s", tick.Side)
	}
	expectedPrice, _ := decimal.NewFromString("100.50")
	if !tick.Price.Equal(expectedPrice) {
		t.Errorf("expected price 100.50, got %s", tick.Price)
	}
	if tick.Extra["seq_num"] != 42 {
		t.Errorf("expected seq_num 42, got %v (%T)", tick.Extra["seq_num"], tick.Extra["seq_num"])
	}
}

// --- Symbol mapping tests ---

func TestMapSymbolExplicit(t *testing.T) {
	n := newTestNormalizer()
	got := n.mapSymbol("btcusdt")
	if got != "BTC/USDT" {
		t.Errorf("expected BTC/USDT, got %s", got)
	}
}

func TestMapSymbolAutoDetectSuffix(t *testing.T) {
	n := NewNormalizer(map[string]string{}) // empty map, forces auto-detect
	got := n.mapSymbol("ethusdc")
	if got != "ETH/USDC" {
		t.Errorf("expected ETH/USDC, got %s", got)
	}
}

func TestMapSymbolAutoDetectBUSD(t *testing.T) {
	n := NewNormalizer(map[string]string{})
	got := n.mapSymbol("adabusd")
	if got != "ADA/BUSD" {
		t.Errorf("expected ADA/BUSD, got %s", got)
	}
}

func TestMapSymbolFallbackUppercase(t *testing.T) {
	n := NewNormalizer(map[string]string{})
	got := n.mapSymbol("unknownpair")
	// No suffix match, so returns uppercase
	if got != "UNKNOWNPAIR" {
		t.Errorf("expected UNKNOWNPAIR, got %s", got)
	}
}

func TestMapSymbolBTCSuffix(t *testing.T) {
	n := NewNormalizer(map[string]string{})
	got := n.mapSymbol("ethbtc")
	if got != "ETH/BTC" {
		t.Errorf("expected ETH/BTC, got %s", got)
	}
}

func TestNormalizeTimestampIsSet(t *testing.T) {
	n := newTestNormalizer()
	data, _ := json.Marshal(map[string]interface{}{
		"e": "trade", "s": "test_sym", "p": "1", "q": "1", "T": 0, "seq": 0,
	})
	tick, err := n.NormalizeRawMessage(connectors.RawMessage{
		Exchange: "mock", Data: data, Timestamp: 1,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tick.NormalizeTimestamp <= 0 {
		t.Error("expected NormalizeTimestamp to be set")
	}
}
