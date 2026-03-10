// Package main è il punto di ingresso per il Servizio di Approvvigionamento Dati MONEYMAKER.
//
// Il Servizio di Approvvigionamento è responsabile di:
//   - Connettersi ai flussi WebSocket degli exchange (Cacciatori)
//   - Raffinare i dati grezzi in un formato standard (Raffinazione)
//   - Aggregare i tick in barre OHLCV su più timeframe (Assemblaggio)
//   - Spedire i dati raffinati tramite ZeroMQ agli altri reparti della fabbrica (Molo)
//   - Registrare i dati grezzi su PostgreSQL per l'analisi storica (Archivio)
//   - Archiviare gli ultimi tick su Redis per l'accesso rapido (Memoria pronta)
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/moneymaker-v1/services/data-ingestion/internal/aggregator"
	"github.com/moneymaker-v1/services/data-ingestion/internal/connectors"
	"github.com/moneymaker-v1/services/data-ingestion/internal/dbwriter"
	"github.com/moneymaker-v1/services/data-ingestion/internal/normalizer"
	"github.com/moneymaker-v1/services/data-ingestion/internal/publisher"
	"github.com/moneymaker-v1/shared/go-common/config"
	"github.com/moneymaker-v1/shared/go-common/health"
	"github.com/moneymaker-v1/shared/go-common/logging"
	"go.uber.org/zap"
)

const serviceName = "data-ingestion"

func main() {
	// ─── Inizializzazione Registro (Logger) ─────────────────────────────
	logger, err := logging.NewLogger(serviceName)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	logger.Info("starting MONEYMAKER Data Ingestion Service",
		zap.String("version", "1.0.0"),
	)

	// ─── Caricamento Configurazione ─────────────────────────────────────
	baseCfg := config.LoadBaseConfig()
	baseCfg.ValidateProduction()

	logger.Info("configuration loaded",
		zap.String("env", baseCfg.Env),
		zap.String("zmq_pub_addr", baseCfg.ZMQPubAddr),
		zap.Int("metrics_port", baseCfg.MetricsPort),
		zap.String("db_host", baseCfg.DBHost),
		zap.Int("db_port", baseCfg.DBPort),
	)

	// ─── Archivio Dati (DBWriter - TimescaleDB) ─────────────────────────
	dbCfg := dbwriter.DefaultConfig()
	dbCfg.DSN = baseCfg.DatabaseURL()
	// Legge parametri opzionali da variabili ambiente
	if batchSize := os.Getenv("MONEYMAKER_DB_BATCH_SIZE"); batchSize != "" {
		if bs, err := parseIntEnv(batchSize); err == nil && bs > 0 {
			dbCfg.BatchSize = bs
		}
	}
	if flushMs := os.Getenv("MONEYMAKER_DB_FLUSH_INTERVAL_MS"); flushMs != "" {
		if fi, err := parseIntEnv(flushMs); err == nil && fi > 0 {
			dbCfg.FlushInterval = time.Duration(fi) * time.Millisecond
		}
	}
	if workers := os.Getenv("MONEYMAKER_DB_WRITER_WORKERS"); workers != "" {
		if w, err := parseIntEnv(workers); err == nil && w > 0 {
			dbCfg.WorkerCount = w
		}
	}
	// Disabilita DB se non configurato o esplicitamente disabilitato
	if baseCfg.DBHost == "" || os.Getenv("MONEYMAKER_DB_ENABLED") == "false" {
		dbCfg.Enabled = false
	}

	dbWriter, err := dbwriter.New(context.Background(), dbCfg, logger)
	if err != nil {
		logger.Fatal("failed to create DBWriter", zap.Error(err))
	}
	defer func() {
		if closeErr := dbWriter.Close(); closeErr != nil {
			logger.Error("DBWriter close error", zap.Error(closeErr))
		}
	}()
	logger.Info("DBWriter initialized",
		zap.Bool("enabled", dbCfg.Enabled),
		zap.Int("batch_size", dbCfg.BatchSize),
		zap.Duration("flush_interval", dbCfg.FlushInterval),
	)

	// ─── Controllo Medico (Health Checker) ──────────────────────────────
	checker := health.NewChecker(serviceName)

	// ─── Server HTTP per la Salute ──────────────────────────────────────
	healthMux := http.NewServeMux()
	checker.RegisterHTTPHandlers(healthMux)

	healthPort := 8081
	if baseCfg.MetricsPort > 0 {
		healthPort = baseCfg.MetricsPort + 1
	}

	healthServer := &http.Server{
		Addr:         fmt.Sprintf(":%d", healthPort),
		Handler:      healthMux,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	go func() {
		logger.Info("health server listening", zap.Int("port", healthPort))
		if srvErr := healthServer.ListenAndServe(); srvErr != nil && srvErr != http.ErrServerClosed {
			logger.Fatal("health server failed", zap.Error(srvErr))
		}
	}()

	// ─── Molo di Spedizione ZMQ (Publisher) ─────────────────────────────
	pub, err := publisher.NewPublisher(baseCfg.ZMQPubAddr)
	if err != nil {
		logger.Fatal("failed to create ZMQ publisher", zap.Error(err))
	}
	defer pub.Close()
	logger.Info("ZMQ publisher bound", zap.String("addr", baseCfg.ZMQPubAddr))

	checker.RegisterCheck("zmq_publisher", func() error { return pub.Ping() })
	checker.RegisterCheck("timescaledb", func() error { return dbWriter.Ping() })

	// ─── Reparto Raffinazione (Normalizer) ──────────────────────────────
	// Symbol map: exchange-native format -> canonical MONEYMAKER format
	symbolMap := map[string]string{
		// Polygon.io Forex format (with and without "C:" prefix)
		"c:xauusd": "XAU/USD",
		"xau/usd":  "XAU/USD",
		"xauusd":   "XAU/USD",
		"c:eurusd": "EUR/USD",
		"eur/usd":  "EUR/USD",
		"eurusd":   "EUR/USD",
		"c:gbpusd": "GBP/USD",
		"gbp/usd":  "GBP/USD",
		"gbpusd":   "GBP/USD",
		"c:usdjpy": "USD/JPY",
		"usd/jpy":  "USD/JPY",
		"usdjpy":   "USD/JPY",
		"c:audusd": "AUD/USD",
		"aud/usd":  "AUD/USD",
		"audusd":   "AUD/USD",
		"c:usdcad": "USD/CAD",
		"usd/cad":  "USD/CAD",
		"usdcad":   "USD/CAD",
		"c:nzdusd": "NZD/USD",
		"nzd/usd":  "NZD/USD",
		"nzdusd":   "NZD/USD",
		"c:usdchf": "USD/CHF",
		"usd/chf":  "USD/CHF",
		"usdchf":   "USD/CHF",
		// Crypto (Binance format, if enabled)
		"btcusdt": "BTC/USDT",
		"ethusdt": "ETH/USDT",
	}
	norm := normalizer.NewNormalizer(symbolMap)
	logger.Info("normalizer initialized", zap.Int("symbol_mappings", len(symbolMap)))

	// ─── Assemblatore di Candele (Aggregator) ───────────────────────────
	timeframes := []aggregator.Timeframe{
		aggregator.M1,
		aggregator.M5,
		aggregator.M15,
		aggregator.H1,
	}

	agg := aggregator.NewAggregator(timeframes, func(bar aggregator.Bar) {
		// Spedisce il pacco completato sul molo ZMQ
		barJSON, err := json.Marshal(bar)
		if err != nil {
			logger.Error("failed to marshal bar", zap.Error(err))
			return
		}
		topic := fmt.Sprintf("bar.%s.%s", bar.Symbol, string(bar.Timeframe))
		if pubErr := pub.Publish(topic, barJSON); pubErr != nil {
			logger.Error("failed to publish bar", zap.Error(pubErr), zap.String("topic", topic))
		}

		// Persistenza su TimescaleDB (Archivio)
		dbWriter.WriteBar(
			bar.Symbol,
			string(bar.Timeframe),
			bar.OpenTime,
			bar.Open,
			bar.High,
			bar.Low,
			bar.Close,
			bar.Volume,
			bar.TickCount,
			"aggregator",
		)

		logger.Debug("bar published",
			zap.String("symbol", bar.Symbol),
			zap.String("timeframe", string(bar.Timeframe)),
			zap.Int("ticks", bar.TickCount),
		)
	})
	logger.Info("candle aggregator initialized",
		zap.Int("timeframes", len(timeframes)),
	)

	// ─── Reparto Cacciatori: Connector Selection ────────────────────────
	// MONEYMAKER_DATA_CONNECTOR env var selects the market data source:
	//   "binance"  → Binance Spot WebSocket (free, real-time crypto)
	//   "polygon"  → Polygon.io Forex WebSocket (requires paid plan)
	//   "mock"     → Mock connector for local development
	// If unset, defaults to: polygon for production/staging, mock otherwise.
	symbols := []string{
		"C:XAUUSD", // Gold/USD - Primary asset for MONEYMAKER V1
		"C:EURUSD", // Euro/USD - Most liquid Forex pair
		"C:GBPUSD", // Pound/USD
		"C:USDJPY", // USD/Yen
	}
	channels := []string{"trade"} // Tick-level trade data

	connectorType := os.Getenv("MONEYMAKER_DATA_CONNECTOR")
	if connectorType == "" {
		if baseCfg.Env == "production" || baseCfg.Env == "staging" {
			connectorType = "polygon"
		} else {
			connectorType = "mock"
		}
	}

	var conn connectors.Connector
	switch connectorType {
	case "binance":
		// Binance Spot — free real-time crypto data (no API key needed)
		symbols = []string{
			"btcusdt",  // Bitcoin/USDT
			"ethusdt",  // Ethereum/USDT
			"solusdt",  // Solana/USDT
			"bnbusdt",  // BNB/USDT
			"xrpusdt",  // XRP/USDT
			"adausdt",  // Cardano/USDT
			"dogeusdt", // Dogecoin/USDT
			"avaxusdt", // Avalanche/USDT
		}
		channels = []string{"trade"}
		conn = connectors.NewBinanceConnector(
			"wss://stream.binance.com:9443/stream",
			symbols,
		)
		logger.Info("using Binance crypto connector (real-time)",
			zap.Int("symbols", len(symbols)),
			zap.Strings("channels", channels),
		)

	case "polygon":
		// Polygon.io Forex — requires paid WebSocket plan
		polygonAPIKey := os.Getenv("POLYGON_API_KEY")
		if polygonAPIKey == "" {
			logger.Fatal("POLYGON_API_KEY environment variable not set")
		}
		if len(polygonAPIKey) < 10 {
			logger.Warn("POLYGON_API_KEY looks suspiciously short",
				zap.Int("length", len(polygonAPIKey)),
			)
		}
		conn = connectors.NewPolygonConnector(
			polygonAPIKey,
			"wss://socket.polygon.io/forex",
			symbols,
		)
		logger.Info("using Polygon.io Forex connector",
			zap.Int("symbols", len(symbols)),
		)

	default:
		// Development mode: Mock connector
		conn = connectors.NewMockConnector("mock-dev")
		logger.Info("using Mock connector (dev mode)")
	}

	if err := conn.Connect(); err != nil {
		logger.Fatal("connector failed to connect", zap.Error(err))
	}
	defer conn.Close()

	if err := conn.Subscribe(symbols, channels); err != nil {
		logger.Warn("subscribe failed, will retry on reconnect", zap.Error(err))
	}

	// Segna il servizio come pronto dopo che tutti i reparti sono avviati.
	checker.SetReady()
	logger.Info("servizio pronto e in attesa di dati")

	// ─── Configurazione Chiusura Ordinata (Graceful Shutdown) ───────────
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	// ─── Ciclo Principale di Approvvigionamento ─────────────────────────
	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			default:
			}

			raw, err := conn.ReadMessage()
			if err != nil {
				if ctx.Err() != nil {
					return // shutting down
				}
				logger.Warn("read error", zap.Error(err))
				continue
			}

			// Raffinazione
			tick, err := norm.NormalizeRawMessage(raw)
			if err != nil {
				logger.Debug("normalization skipped", zap.Error(err))
				continue
			}

			// Spedizione tick grezzo
			tickJSON, err := json.Marshal(tick)
			if err != nil {
				logger.Error("failed to marshal tick", zap.Error(err))
				continue
			}
			topic := fmt.Sprintf("%s.%s.%s", tick.EventType, tick.Exchange, tick.Symbol)
			if pubErr := pub.Publish(topic, tickJSON); pubErr != nil {
				logger.Warn("tick publish error", zap.Error(pubErr))
			}

			// Persistenza tick su TimescaleDB (Archivio)
			dbWriter.WriteTick(tick)

			// Invio all'Assemblatore
			tickTime := time.Unix(0, tick.NormalizeTimestamp)
			agg.AddTick(tick.Symbol, tick.Price, tick.Quantity, tickTime)
		}
	}()

	// Block until shutdown signal
	<-ctx.Done()

	logger.Info("shutdown signal received, draining connections...")
	checker.SetNotReady()

	// Svuota i pacchi parziali
	flushed := agg.FlushAll()
	logger.Info("flushed partial bars on shutdown", zap.Int("count", len(flushed)))

	// Flush finale del DBWriter
	dbWriter.FlushTicks()
	dbWriter.FlushBars()
	logger.Info("DBWriter final flush complete", zap.Any("stats", dbWriter.Stats()))

	// Tempo per completare le spedizioni in corso.
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	// Chiude il server della salute.
	if err := healthServer.Shutdown(shutdownCtx); err != nil {
		logger.Error("health server shutdown error", zap.Error(err))
	}

	logger.Info("MONEYMAKER Data Ingestion Service stopped cleanly")
}

// parseIntEnv converte una stringa in intero per le variabili d'ambiente.
func parseIntEnv(s string) (int, error) {
	var n int
	_, err := fmt.Sscanf(s, "%d", &n)
	return n, err
}
