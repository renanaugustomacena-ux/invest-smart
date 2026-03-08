"""Tests for moneymaker_common.metrics — Prometheus metric definitions."""

from prometheus_client import Counter, Gauge, Histogram

from moneymaker_common import metrics


class TestCommonMetrics:
    def test_service_up_is_gauge(self):
        assert isinstance(metrics.SERVICE_UP, Gauge)

    def test_request_duration_is_histogram(self):
        assert isinstance(metrics.REQUEST_DURATION, Histogram)

    def test_error_counter_is_counter(self):
        assert isinstance(metrics.ERROR_COUNTER, Counter)


class TestBrainMetrics:
    def test_features_computed_exists(self):
        assert isinstance(metrics.FEATURES_COMPUTED, Counter)

    def test_regime_classified_exists(self):
        assert isinstance(metrics.REGIME_CLASSIFIED, Counter)

    def test_signals_generated_exists(self):
        assert isinstance(metrics.SIGNALS_GENERATED, Counter)

    def test_signals_rejected_exists(self):
        assert isinstance(metrics.SIGNALS_REJECTED, Counter)

    def test_signal_confidence_exists(self):
        assert isinstance(metrics.SIGNAL_CONFIDENCE, Histogram)

    def test_pipeline_latency_exists(self):
        assert isinstance(metrics.PIPELINE_LATENCY, Histogram)


class TestIngestionMetrics:
    def test_ticks_received_exists(self):
        assert isinstance(metrics.TICKS_RECEIVED, Counter)

    def test_bars_completed_exists(self):
        assert isinstance(metrics.BARS_COMPLETED, Counter)

    def test_ingestion_latency_exists(self):
        assert isinstance(metrics.INGESTION_LATENCY, Histogram)


class TestBridgeMetrics:
    def test_trades_executed_exists(self):
        assert isinstance(metrics.TRADES_EXECUTED, Counter)

    def test_open_positions_exists(self):
        assert isinstance(metrics.OPEN_POSITIONS, Gauge)

    def test_execution_latency_exists(self):
        assert isinstance(metrics.EXECUTION_LATENCY, Histogram)

    def test_slippage_pips_exists(self):
        assert isinstance(metrics.SLIPPAGE_PIPS, Histogram)
