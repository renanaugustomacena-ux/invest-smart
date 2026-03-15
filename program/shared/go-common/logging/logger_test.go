package logging

import (
	"testing"
)

func TestNewLogger(t *testing.T) {
	logger, err := NewLogger("test-service")
	if err != nil {
		t.Fatalf("NewLogger() error = %v", err)
	}
	if logger == nil {
		t.Fatal("NewLogger() returned nil logger")
	}

	// Verify logger can write without panic
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
