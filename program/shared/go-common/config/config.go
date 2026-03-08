// Package config provides base configuration loading for MONEYMAKER Go services.
package config

import (
	"fmt"
	"log"
	"net/url"
	"os"
	"strconv"
)

// BaseConfig holds configuration common to all MONEYMAKER services.
type BaseConfig struct {
	Env           string
	DBHost        string
	DBPort        int
	DBName        string
	DBUser        string
	DBPassword    string
	RedisHost     string
	RedisPort     int
	RedisPassword string
	ZMQPubAddr    string
	MetricsPort   int
	// TLS Configuration
	TLSEnabled bool
	TLSCACert  string
}

// LoadBaseConfig reads base configuration from environment variables.
func LoadBaseConfig() *BaseConfig {
	return &BaseConfig{
		Env:           getEnv("MONEYMAKER_ENV", "development"),
		DBHost:        getEnv("MONEYMAKER_DB_HOST", "localhost"),
		DBPort:        getEnvInt("MONEYMAKER_DB_PORT", 5432),
		DBName:        getEnv("MONEYMAKER_DB_NAME", "moneymaker"),
		DBUser:        getEnv("MONEYMAKER_DB_USER", "moneymaker"),
		DBPassword:    getEnv("MONEYMAKER_DB_PASSWORD", ""),
		RedisHost:     getEnv("MONEYMAKER_REDIS_HOST", "localhost"),
		RedisPort:     getEnvInt("MONEYMAKER_REDIS_PORT", 6379),
		RedisPassword: getEnv("MONEYMAKER_REDIS_PASSWORD", ""),
		ZMQPubAddr:    getEnv("MONEYMAKER_ZMQ_PUB_ADDR", "tcp://localhost:5555"),
		MetricsPort:   getEnvInt("MONEYMAKER_METRICS_PORT", 9090),
		// TLS defaults to disabled for backward compatibility
		TLSEnabled: getEnvBool("MONEYMAKER_TLS_ENABLED", false),
		TLSCACert:  getEnv("MONEYMAKER_TLS_CA_CERT", ""),
	}
}

// DatabaseURL constructs the PostgreSQL connection string with TLS support.
// In production (or when TLS is enabled), sslmode defaults to require/verify-full.
// The password is URL-encoded to handle special characters safely.
func (c *BaseConfig) DatabaseURL() string {
	sslMode := "disable"
	sslParams := ""

	if c.TLSEnabled {
		sslMode = "verify-full"
		if c.TLSCACert != "" {
			sslParams = fmt.Sprintf("&sslrootcert=%s", c.TLSCACert)
		}
	} else if c.IsProduction() {
		sslMode = "require"
	}

	return fmt.Sprintf("postgres://%s:%s@%s:%d/%s?sslmode=%s%s",
		c.DBUser, url.PathEscape(c.DBPassword), c.DBHost, c.DBPort, c.DBName, sslMode, sslParams)
}

// ValidateProduction checks that critical credentials are set in production.
// Logs a fatal error and exits if validation fails.
func (c *BaseConfig) ValidateProduction() {
	if !c.IsProduction() {
		return
	}
	if c.DBPassword == "" {
		log.Fatal("MONEYMAKER_DB_PASSWORD must be set in production")
	}
}

// RedisURL constructs the Redis connection string with TLS support.
// Returns rediss:// scheme when TLS is enabled, redis:// otherwise.
func (c *BaseConfig) RedisURL() string {
	scheme := "redis"
	if c.TLSEnabled {
		scheme = "rediss"
	}

	auth := ""
	if c.RedisPassword != "" {
		auth = fmt.Sprintf(":%s@", c.RedisPassword)
	}

	return fmt.Sprintf("%s://%s%s:%d/0", scheme, auth, c.RedisHost, c.RedisPort)
}

// IsProduction returns true if running in production environment.
func (c *BaseConfig) IsProduction() bool {
	return c.Env == "production"
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}

// getEnvBool reads a boolean environment variable.
// Accepts "true", "1", "yes" as true values (case-insensitive).
func getEnvBool(key string, fallback bool) bool {
	if v := os.Getenv(key); v != "" {
		switch v {
		case "true", "TRUE", "True", "1", "yes", "YES", "Yes":
			return true
		case "false", "FALSE", "False", "0", "no", "NO", "No":
			return false
		}
	}
	return fallback
}
