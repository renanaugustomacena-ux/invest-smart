// Package logging provides structured JSON logging for MONEYMAKER Go services.
package logging

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// NewLogger creates a structured JSON logger for a MONEYMAKER service.
func NewLogger(serviceName string) (*zap.Logger, error) {
	config := zap.NewProductionConfig()
	config.OutputPaths = []string{"stdout"}
	config.EncoderConfig.TimeKey = "timestamp"
	config.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder

	logger, err := config.Build()
	if err != nil {
		return nil, err
	}

	return logger.With(zap.String("service", serviceName)), nil
}
