package logging

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// ---------------------------------------------------------------------------
// Helpers — write to temp file, parse JSON output
// ---------------------------------------------------------------------------

// newFileLogger creates a logger that writes JSON to a temp file.
// Returns the zap.Logger and a cleanup function that syncs before reading.
func newFileLogger(t *testing.T, serviceName, path string) (*zap.Logger, func()) {
	t.Helper()
	cfg := zap.NewProductionConfig()
	cfg.OutputPaths = []string{path}
	cfg.EncoderConfig.TimeKey = "timestamp"
	cfg.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	base, err := cfg.Build()
	if err != nil {
		t.Fatalf("failed to build logger: %v", err)
	}
	logger := base.With(zap.String("service", serviceName))
	return logger, func() { _ = logger.Sync() }
}

// getLogJSON writes one log line via fn, parses the JSON, and returns it.
func getLogJSON(t *testing.T, serviceName string, fn func(*zap.Logger)) map[string]interface{} {
	t.Helper()

	tmpFile, err := os.CreateTemp("", "zap-test-*.log")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	tmpPath := tmpFile.Name()
	tmpFile.Close()
	defer os.Remove(tmpPath)

	logger, cleanup := newFileLogger(t, serviceName, tmpPath)
	fn(logger)
	cleanup()

	data, err := os.ReadFile(tmpPath)
	if err != nil {
		t.Fatalf("failed to read log output: %v", err)
	}
	line := strings.TrimSpace(string(data))
	if line == "" {
		t.Fatal("log output is empty")
	}

	var parsed map[string]interface{}
	if err := json.Unmarshal([]byte(line), &parsed); err != nil {
		t.Fatalf("log output is not valid JSON: %v\nOutput: %s", err, line)
	}
	return parsed
}

// ---------------------------------------------------------------------------
// Basic initialization (existing tests, preserved)
// ---------------------------------------------------------------------------

func TestNewLogger(t *testing.T) {
	logger, err := NewLogger("test-service")
	if err != nil {
		t.Fatalf("NewLogger() error = %v", err)
	}
	if logger == nil {
		t.Fatal("NewLogger() returned nil logger")
	}
	logger.Info("test message")
}

func TestNewLoggerDifferentServices(t *testing.T) {
	services := []string{"data-ingestion", "algo-engine", "mt5-bridge"}
	for _, svc := range services {
		t.Run(svc, func(t *testing.T) {
			logger, err := NewLogger(svc)
			if err != nil {
				t.Fatalf("NewLogger(%q) error = %v", svc, err)
			}
			if logger == nil {
				t.Fatalf("NewLogger(%q) returned nil", svc)
			}
		})
	}
}

func TestNewLoggerEmptyServiceName(t *testing.T) {
	logger, err := NewLogger("")
	if err != nil {
		t.Fatalf("NewLogger('') error = %v", err)
	}
	if logger == nil {
		t.Fatal("NewLogger('') returned nil")
	}
	logger.Info("empty service name")
}

// ---------------------------------------------------------------------------
// JSON output format verification
// ---------------------------------------------------------------------------

func TestLogOutputIsValidJSON(t *testing.T) {
	parsed := getLogJSON(t, "json-test", func(l *zap.Logger) {
		l.Info("hello world")
	})
	if len(parsed) == 0 {
		t.Error("parsed JSON is empty")
	}
}

func TestLogOutputContainsServiceField(t *testing.T) {
	parsed := getLogJSON(t, "my-service", func(l *zap.Logger) {
		l.Info("test event")
	})
	svc, ok := parsed["service"]
	if !ok {
		t.Fatal("missing 'service' field in log output")
	}
	if svc != "my-service" {
		t.Errorf("service = %q, want %q", svc, "my-service")
	}
}

func TestLogOutputContainsTimestamp(t *testing.T) {
	parsed := getLogJSON(t, "ts-test", func(l *zap.Logger) {
		l.Info("timestamp check")
	})
	ts, ok := parsed["timestamp"]
	if !ok {
		t.Fatal("missing 'timestamp' field in log output")
	}
	tsStr, ok := ts.(string)
	if !ok {
		t.Fatalf("timestamp is not a string: %T", ts)
	}
	// ISO8601 contains 'T' separator between date and time
	if !strings.Contains(tsStr, "T") {
		t.Errorf("timestamp %q does not look like ISO8601 (missing T)", tsStr)
	}
}

func TestLogOutputContainsLevel(t *testing.T) {
	parsed := getLogJSON(t, "level-test", func(l *zap.Logger) {
		l.Info("info msg")
	})
	level, ok := parsed["level"]
	if !ok {
		t.Fatal("missing 'level' field in log output")
	}
	if level != "info" {
		t.Errorf("level = %q, want %q", level, "info")
	}
}

func TestLogOutputContainsMsg(t *testing.T) {
	parsed := getLogJSON(t, "msg-test", func(l *zap.Logger) {
		l.Info("my test message")
	})
	msg, ok := parsed["msg"]
	if !ok {
		t.Fatal("missing 'msg' field in log output")
	}
	if msg != "my test message" {
		t.Errorf("msg = %q, want %q", msg, "my test message")
	}
}

func TestLogOutputWarningLevel(t *testing.T) {
	parsed := getLogJSON(t, "warn-test", func(l *zap.Logger) {
		l.Warn("warning msg")
	})
	if parsed["level"] != "warn" {
		t.Errorf("level = %q, want %q", parsed["level"], "warn")
	}
}

func TestLogOutputErrorLevel(t *testing.T) {
	parsed := getLogJSON(t, "error-test", func(l *zap.Logger) {
		l.Error("error msg")
	})
	if parsed["level"] != "error" {
		t.Errorf("level = %q, want %q", parsed["level"], "error")
	}
}

func TestLogOutputWithStructuredFields(t *testing.T) {
	parsed := getLogJSON(t, "fields-test", func(l *zap.Logger) {
		l.Info("trade signal",
			zap.String("symbol", "EURUSD"),
			zap.String("direction", "BUY"),
			zap.Float64("confidence", 0.85),
		)
	})
	if parsed["symbol"] != "EURUSD" {
		t.Errorf("symbol = %v, want %q", parsed["symbol"], "EURUSD")
	}
	if parsed["direction"] != "BUY" {
		t.Errorf("direction = %v, want %q", parsed["direction"], "BUY")
	}
	conf, ok := parsed["confidence"].(float64)
	if !ok || conf != 0.85 {
		t.Errorf("confidence = %v, want 0.85", parsed["confidence"])
	}
}

func TestLogOutputServiceFieldPersists(t *testing.T) {
	// Verify the service field appears on every log line, not just the first
	tmpFile, err := os.CreateTemp("", "zap-test-*.log")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	tmpPath := tmpFile.Name()
	tmpFile.Close()
	defer os.Remove(tmpPath)

	logger, cleanup := newFileLogger(t, "persist-test", tmpPath)
	logger.Info("first")
	logger.Info("second")
	logger.Warn("third")
	cleanup()

	data, err := os.ReadFile(tmpPath)
	if err != nil {
		t.Fatalf("failed to read: %v", err)
	}
	lines := strings.Split(strings.TrimSpace(string(data)), "\n")
	if len(lines) != 3 {
		t.Fatalf("expected 3 log lines, got %d", len(lines))
	}
	for i, line := range lines {
		var parsed map[string]interface{}
		if err := json.Unmarshal([]byte(line), &parsed); err != nil {
			t.Fatalf("line %d not valid JSON: %v", i, err)
		}
		if parsed["service"] != "persist-test" {
			t.Errorf("line %d: service = %q, want %q", i, parsed["service"], "persist-test")
		}
	}
}
