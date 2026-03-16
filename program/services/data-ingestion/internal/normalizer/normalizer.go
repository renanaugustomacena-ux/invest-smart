// Il pacchetto normalizer trasforma i messaggi grezzi degli exchange nel
// formato canonico di MONEYMAKER. Ogni exchange ha schemi JSON e convenzioni
// differenti; il Normalizzatore astrae queste differenze dietro un modello unico.
package normalizer

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/moneymaker-v1/services/data-ingestion/internal/connectors"
	"github.com/shopspring/decimal"
)

// two is a pre-computed constant for mid-price calculation: (bid+ask)/2.
var two = decimal.NewFromInt(2)

// NormalizedTick rappresenta un singolo evento di mercato nel formato standard MONEYMAKER.
// È il prodotto raffinato pronto per la spedizione ai servizi a valle.
type NormalizedTick struct {
	// Exchange è il nome della sorgente (l'exchange).
	Exchange string `json:"exchange"`

	// Symbol è il simbolo canonico (es. "BTC/USDT").
	Symbol string `json:"symbol"`

	// EventType classifica il tipo di materiale (es. "trade", "depth_update").
	EventType string `json:"event_type"`

	// Price è il prezzo di scambio, con precisione decimale.
	Price decimal.Decimal `json:"price"`

	// Quantity è la quantità scambiata.
	Quantity decimal.Decimal `json:"quantity"`

	// Side indica l'aggressore: "buy" o "sell".
	// Vuoto per eventi non di scambio.
	Side string `json:"side,omitempty"`

	// ExchangeTimestamp è l'orario riportato dalla sorgente (millisecondi).
	ExchangeTimestamp int64 `json:"exchange_ts"`

	// IngestTimestamp è quando il materiale grezzo è arrivato ai nostri magazzini.
	IngestTimestamp int64 `json:"ingest_ts"`

	// NormalizeTimestamp è quando la raffinazione è stata completata.
	NormalizeTimestamp int64 `json:"normalize_ts"`

	// Extra contiene campi specifici dell'exchange non standardizzati.
	Extra map[string]interface{} `json:"extra,omitempty"`
}

// Normalizer trasforma i RawMessage eterogenei nel formato standard NormalizedTick.
// È il "Centro di Raffinazione e Standardizzazione".
type Normalizer struct {
	// symbolMap mappa i nomi simboli dei fornitori ai nomi standard di fabbrica.
	// Es: "btcusdt" -> "BTC/USDT"
	symbolMap map[string]string
}

// NewNormalizer crea un Centro di Raffinazione con la mappa dei simboli fornita.
func NewNormalizer(symbolMap map[string]string) *Normalizer {
	return &Normalizer{
		symbolMap: symbolMap,
	}
}

// NormalizeRawMessage converte un messaggio grezzo in un tick standardizzato.
// Smista il lavoro ai reparti specializzati in base all'exchange.
func (n *Normalizer) NormalizeRawMessage(raw connectors.RawMessage) (*NormalizedTick, error) {
	normalizeTS := time.Now().UnixNano()

	switch raw.Exchange {
	case "binance":
		return n.normalizeBinance(raw, normalizeTS)
	case "polygon":
		return n.normalizePolygon(raw, normalizeTS)
	case "mock":
		return n.normalizeMock(raw, normalizeTS)
	default:
		return nil, fmt.Errorf("normalizer: unsupported exchange %q", raw.Exchange)
	}
}

// normalizeBinance gestisce la raffinazione specifica per Binance.
func (n *Normalizer) normalizeBinance(raw connectors.RawMessage, normalizeTS int64) (*NormalizedTick, error) {
	// Binance trade message format:
	// {
	//   "e": "trade",
	//   "E": 1672515782136,   // Event time
	//   "s": "BTCUSDT",       // Symbol
	//   "t": 12345,           // Trade ID
	//   "p": "50000.00",      // Price
	//   "q": "0.001",         // Quantity
	//   "b": 88,              // Buyer order ID
	//   "a": 50,              // Seller order ID
	//   "T": 1672515782136,   // Trade time
	//   "m": true,            // Is buyer the market maker?
	//   "M": true             // Ignore
	// }

	var msg struct {
		EventType    string `json:"e"`
		EventTime    int64  `json:"E"`
		Symbol       string `json:"s"`
		TradeID      int64  `json:"t"`
		Price        string `json:"p"`
		Quantity     string `json:"q"`
		TradeTime    int64  `json:"T"`
		IsBuyerMaker bool   `json:"m"`
	}

	// Gestisce l'involucro del flusso combinato se presente.
	data := raw.Data
	var envelope struct {
		Stream string          `json:"stream"`
		Data   json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal(data, &envelope); err == nil && envelope.Data != nil {
		data = []byte(envelope.Data)
	}

	if err := json.Unmarshal(data, &msg); err != nil {
		return nil, fmt.Errorf("normalizer: parse binance message: %w", err)
	}

	// Per ora gestiamo solo gli eventi di scambio (trade).
	// TODO: Aggiungere supporto per book, kline, ecc.
	if msg.EventType != "trade" {
		return nil, fmt.Errorf("normalizer: unsupported binance event type %q", msg.EventType)
	}

	price, err := decimal.NewFromString(msg.Price)
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse price %q: %w", msg.Price, err)
	}

	quantity, err := decimal.NewFromString(msg.Quantity)
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse quantity %q: %w", msg.Quantity, err)
	}

	// Determina il lato dello scambio. Su Binance, m=true significa che il compratore
	// è il maker, quindi lo scambio è stato iniziato da un ordine di vendita.
	side := "buy"
	if msg.IsBuyerMaker {
		side = "sell"
	}

	// Mappa il simbolo del fornitore al simbolo standard di fabbrica.
	canonicalSymbol := n.mapSymbol(strings.ToLower(msg.Symbol))

	return &NormalizedTick{
		Exchange:           "binance",
		Symbol:             canonicalSymbol,
		EventType:          "trade",
		Price:              price,
		Quantity:           quantity,
		Side:               side,
		ExchangeTimestamp:  msg.TradeTime,
		IngestTimestamp:    raw.Timestamp,
		NormalizeTimestamp: normalizeTS,
		Extra: map[string]interface{}{
			"trade_id": msg.TradeID,
		},
	}, nil
}

// normalizePolygon gestisce la raffinazione specifica per Polygon.io Forex/CFD.
func (n *Normalizer) normalizePolygon(raw connectors.RawMessage, normalizeTS int64) (*NormalizedTick, error) {
	// Polygon.io invia messaggi con campo "ev" per il tipo di evento.
	// Eventi supportati:
	// - "C": Currency trade (tick level) - bid/ask prices
	// - "CA": Currency aggregate (OHLCV candle)
	// - "CQ": Currency quote (best bid/ask)

	var base struct {
		EventType string `json:"ev"`
	}
	if err := json.Unmarshal(raw.Data, &base); err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon event type: %w", err)
	}

	switch base.EventType {
	case "C": // Currency trade tick
		return n.normalizePolygonTrade(raw, normalizeTS)
	case "CA": // Currency aggregate (candle)
		return n.normalizePolygonAggregate(raw, normalizeTS)
	case "CQ": // Currency quote
		return n.normalizePolygonQuote(raw, normalizeTS)
	default:
		return nil, fmt.Errorf("normalizer: unsupported polygon event type %q", base.EventType)
	}
}

// normalizePolygonTrade normalizza un tick trade Forex da Polygon.io.
// Formato: {"ev":"C","p":"EUR/USD","x":1,"a":1.1234,"b":1.1233,"t":1672515782123}
//
// NOTA: Tutti i calcoli sui prezzi usano shopspring/decimal per evitare
// precision loss da float64. I numeri JSON vengono parsati come stringhe
// tramite json.Decoder.UseNumber().
func (n *Normalizer) normalizePolygonTrade(raw connectors.RawMessage, normalizeTS int64) (*NormalizedTick, error) {
	var msg struct {
		EventType string      `json:"ev"` // "C"
		Pair      string      `json:"p"`  // "EUR/USD"
		Exchange  int         `json:"x"`  // Exchange ID
		Ask       json.Number `json:"a"`  // Ask price (parsed as string)
		Bid       json.Number `json:"b"`  // Bid price (parsed as string)
		Timestamp int64       `json:"t"`  // Unix milliseconds
	}

	dec := json.NewDecoder(bytes.NewReader(raw.Data))
	dec.UseNumber()
	if err := dec.Decode(&msg); err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon trade: %w", err)
	}

	ask, err := decimal.NewFromString(msg.Ask.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon ask %q: %w", msg.Ask, err)
	}
	bid, err := decimal.NewFromString(msg.Bid.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon bid %q: %w", msg.Bid, err)
	}

	// Mid price: (bid + ask) / 2 — calcolo interamente in decimal.
	price := bid.Add(ask).Div(two)

	// Spread come misura di liquidità.
	spread := ask.Sub(bid)

	canonicalSymbol := n.mapSymbol(strings.ToLower(msg.Pair))

	return &NormalizedTick{
		Exchange:           "polygon",
		Symbol:             canonicalSymbol,
		EventType:          "trade",
		Price:              price,
		Quantity:           decimal.Zero,              // Forex ticks non hanno volume significativo
		Side:               "",                        // Forex ticks non hanno side
		ExchangeTimestamp:  msg.Timestamp * 1_000_000, // ms -> ns
		IngestTimestamp:    raw.Timestamp,
		NormalizeTimestamp: normalizeTS,
		Extra: map[string]interface{}{
			"ask":         ask.String(),
			"bid":         bid.String(),
			"spread":      spread.String(),
			"exchange_id": msg.Exchange,
		},
	}, nil
}

// normalizePolygonAggregate normalizza una candela aggregata da Polygon.io.
// Formato: {"ev":"CA","pair":"EUR/USD","o":1.1234,"h":1.1250,"l":1.1230,"c":1.1245,"v":1000,"s":1672515780000,"e":1672515839999}
//
// NOTA: Tutti i prezzi OHLCV parsati tramite json.Number → decimal.Decimal.
func (n *Normalizer) normalizePolygonAggregate(raw connectors.RawMessage, normalizeTS int64) (*NormalizedTick, error) {
	var msg struct {
		EventType string      `json:"ev"`   // "CA"
		Pair      string      `json:"pair"` // "EUR/USD"
		Open      json.Number `json:"o"`    // Open price
		High      json.Number `json:"h"`    // High price
		Low       json.Number `json:"l"`    // Low price
		Close     json.Number `json:"c"`    // Close price
		Volume    json.Number `json:"v"`    // Volume
		Start     int64       `json:"s"`    // Period start (ms)
		End       int64       `json:"e"`    // Period end (ms)
	}

	dec := json.NewDecoder(bytes.NewReader(raw.Data))
	dec.UseNumber()
	if err := dec.Decode(&msg); err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon aggregate: %w", err)
	}

	openP, err := decimal.NewFromString(msg.Open.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon open %q: %w", msg.Open, err)
	}
	highP, err := decimal.NewFromString(msg.High.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon high %q: %w", msg.High, err)
	}
	lowP, err := decimal.NewFromString(msg.Low.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon low %q: %w", msg.Low, err)
	}
	closeP, err := decimal.NewFromString(msg.Close.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon close %q: %w", msg.Close, err)
	}
	volume, err := decimal.NewFromString(msg.Volume.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon volume %q: %w", msg.Volume, err)
	}

	canonicalSymbol := n.mapSymbol(strings.ToLower(msg.Pair))

	return &NormalizedTick{
		Exchange:           "polygon",
		Symbol:             canonicalSymbol,
		EventType:          "aggregate",
		Price:              closeP,
		Quantity:           volume,
		Side:               "",
		ExchangeTimestamp:  msg.End * 1_000_000, // ms -> ns
		IngestTimestamp:    raw.Timestamp,
		NormalizeTimestamp: normalizeTS,
		Extra: map[string]interface{}{
			"open":       openP.String(),
			"high":       highP.String(),
			"low":        lowP.String(),
			"close":      closeP.String(),
			"volume":     volume.String(),
			"start_time": msg.Start,
			"end_time":   msg.End,
		},
	}, nil
}

// normalizePolygonQuote normalizza un quote (best bid/ask) da Polygon.io.
//
// NOTA: Tutti i calcoli su bid/ask in decimal.Decimal.
func (n *Normalizer) normalizePolygonQuote(raw connectors.RawMessage, normalizeTS int64) (*NormalizedTick, error) {
	var msg struct {
		EventType string      `json:"ev"` // "CQ"
		Pair      string      `json:"p"`  // "EUR/USD"
		Ask       json.Number `json:"a"`  // Ask price
		Bid       json.Number `json:"b"`  // Bid price
		Timestamp int64       `json:"t"`  // Unix milliseconds
	}

	dec := json.NewDecoder(bytes.NewReader(raw.Data))
	dec.UseNumber()
	if err := dec.Decode(&msg); err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon quote: %w", err)
	}

	ask, err := decimal.NewFromString(msg.Ask.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon quote ask %q: %w", msg.Ask, err)
	}
	bid, err := decimal.NewFromString(msg.Bid.String())
	if err != nil {
		return nil, fmt.Errorf("normalizer: parse polygon quote bid %q: %w", msg.Bid, err)
	}

	price := bid.Add(ask).Div(two)
	spread := ask.Sub(bid)

	canonicalSymbol := n.mapSymbol(strings.ToLower(msg.Pair))

	return &NormalizedTick{
		Exchange:           "polygon",
		Symbol:             canonicalSymbol,
		EventType:          "quote",
		Price:              price,
		Quantity:           decimal.Zero,
		Side:               "",
		ExchangeTimestamp:  msg.Timestamp * 1_000_000, // ms -> ns
		IngestTimestamp:    raw.Timestamp,
		NormalizeTimestamp: normalizeTS,
		Extra: map[string]interface{}{
			"ask":    ask.String(),
			"bid":    bid.String(),
			"spread": spread.String(),
		},
	}, nil
}

// normalizeMock gestisce i messaggi di test — "materiale simulato".
func (n *Normalizer) normalizeMock(raw connectors.RawMessage, normalizeTS int64) (*NormalizedTick, error) {
	var msg struct {
		EventType string `json:"e"`
		Symbol    string `json:"s"`
		Price     string `json:"p"`
		Quantity  string `json:"q"`
		TradeTime int64  `json:"T"`
		SeqNum    int    `json:"seq"`
	}

	if err := json.Unmarshal(raw.Data, &msg); err != nil {
		return nil, fmt.Errorf("normalizer: parse mock message: %w", err)
	}

	price, _ := decimal.NewFromString(msg.Price)
	quantity, _ := decimal.NewFromString(msg.Quantity)

	canonicalSymbol := n.mapSymbol(strings.ToLower(msg.Symbol))

	return &NormalizedTick{
		Exchange:           "mock",
		Symbol:             canonicalSymbol,
		EventType:          msg.EventType,
		Price:              price,
		Quantity:           quantity,
		Side:               "buy",
		ExchangeTimestamp:  msg.TradeTime,
		IngestTimestamp:    raw.Timestamp,
		NormalizeTimestamp: normalizeTS,
		Extra: map[string]interface{}{
			"seq_num": msg.SeqNum,
		},
	}, nil
}

// mapSymbol converte un simbolo nativo nel formato standard.
// Tenta una trasformazione automatica se non esiste una mappatura esplicita.
func (n *Normalizer) mapSymbol(exchangeSymbol string) string {
	// Controlla prima la mappatura esplicita.
	if canonical, ok := n.symbolMap[exchangeSymbol]; ok {
		return canonical
	}

	// Tentativo automatico: prova con i suffissi comuni.
	// "btcusdt" -> "BTC/USDT"
	suffixes := []string{"usdt", "usdc", "busd", "btc", "eth", "bnb"}
	upper := strings.ToUpper(exchangeSymbol)
	for _, suffix := range suffixes {
		suffixUpper := strings.ToUpper(suffix)
		if strings.HasSuffix(upper, suffixUpper) {
			base := upper[:len(upper)-len(suffixUpper)]
			if base != "" {
				return base + "/" + suffixUpper
			}
		}
	}

	// Ultima risorsa: restituisce così com'è in maiuscolo.
	return strings.ToUpper(exchangeSymbol)
}

// TODO: Aggiungere NormalizerPool per gestire più reparti di raffinazione in parallelo.
//
// type NormalizerPool struct {
//     workers    int
//     normalizer *Normalizer
//     input      chan connectors.RawMessage
//     output     chan *NormalizedTick
//     errors     chan error
//     wg         sync.WaitGroup
// }
//
// func NewPool(workers int, symbolMap map[string]string) *NormalizerPool { ... }
// func (p *NormalizerPool) Start() { ... }
// func (p *NormalizerPool) Submit(raw connectors.RawMessage) { ... }
// func (p *NormalizerPool) Results() <-chan *NormalizedTick { ... }
// func (p *NormalizerPool) Stop() { ... }

// TODO: Add normalization for additional event types:
//   - Depth/order book snapshots and updates
//   - Kline/candlestick data
//   - Book ticker (best bid/ask)
//   - Funding rate updates
//   - Liquidation events

// TODO: Add normalization for additional exchanges:
//   - Bybit (inverse and linear perpetuals)
//   - OKX
//   - Coinbase Advanced Trade
