package config

import (
	"testing"
)

func TestLoadBaseConfigDefaults(t *testing.T) {
	// Clear any env vars that might interfere
	for _, key := range []string{
		"MONEYMAKER_ENV", "MONEYMAKER_DB_HOST", "MONEYMAKER_DB_PORT",
		"MONEYMAKER_DB_NAME", "MONEYMAKER_DB_USER", "MONEYMAKER_DB_PASSWORD",
		"MONEYMAKER_REDIS_HOST", "MONEYMAKER_REDIS_PORT", "MONEYMAKER_REDIS_PASSWORD",
		"MONEYMAKER_ZMQ_PUB_ADDR", "MONEYMAKER_METRICS_PORT",
		"MONEYMAKER_TLS_ENABLED", "MONEYMAKER_TLS_CA_CERT",
	} {
		t.Setenv(key, "")
	}

	cfg := LoadBaseConfig()

	if cfg.Env != "development" {
		t.Errorf("Env = %q, want %q", cfg.Env, "development")
	}
	if cfg.DBHost != "localhost" {
		t.Errorf("DBHost = %q, want %q", cfg.DBHost, "localhost")
	}
	if cfg.DBPort != 5432 {
		t.Errorf("DBPort = %d, want %d", cfg.DBPort, 5432)
	}
	if cfg.DBName != "moneymaker" {
		t.Errorf("DBName = %q, want %q", cfg.DBName, "moneymaker")
	}
	if cfg.DBUser != "moneymaker" {
		t.Errorf("DBUser = %q, want %q", cfg.DBUser, "moneymaker")
	}
	if cfg.DBPassword != "" {
		t.Errorf("DBPassword = %q, want empty", cfg.DBPassword)
	}
	if cfg.RedisHost != "localhost" {
		t.Errorf("RedisHost = %q, want %q", cfg.RedisHost, "localhost")
	}
	if cfg.RedisPort != 6379 {
		t.Errorf("RedisPort = %d, want %d", cfg.RedisPort, 6379)
	}
	if cfg.RedisPassword != "" {
		t.Errorf("RedisPassword = %q, want empty", cfg.RedisPassword)
	}
	if cfg.ZMQPubAddr != "tcp://localhost:5555" {
		t.Errorf("ZMQPubAddr = %q, want %q", cfg.ZMQPubAddr, "tcp://localhost:5555")
	}
	if cfg.MetricsPort != 9090 {
		t.Errorf("MetricsPort = %d, want %d", cfg.MetricsPort, 9090)
	}
	if cfg.TLSEnabled {
		t.Error("TLSEnabled should be false by default")
	}
	if cfg.TLSCACert != "" {
		t.Errorf("TLSCACert = %q, want empty", cfg.TLSCACert)
	}
}

func TestLoadBaseConfigEnvOverrides(t *testing.T) {
	t.Setenv("MONEYMAKER_ENV", "production")
	t.Setenv("MONEYMAKER_DB_HOST", "db.example.com")
	t.Setenv("MONEYMAKER_DB_PORT", "5433")
	t.Setenv("MONEYMAKER_DB_NAME", "trading")
	t.Setenv("MONEYMAKER_DB_USER", "admin")
	t.Setenv("MONEYMAKER_DB_PASSWORD", "s3cret")
	t.Setenv("MONEYMAKER_REDIS_HOST", "redis.example.com")
	t.Setenv("MONEYMAKER_REDIS_PORT", "6380")
	t.Setenv("MONEYMAKER_REDIS_PASSWORD", "redispw")
	t.Setenv("MONEYMAKER_ZMQ_PUB_ADDR", "tcp://zmq:5556")
	t.Setenv("MONEYMAKER_METRICS_PORT", "9091")
	t.Setenv("MONEYMAKER_TLS_ENABLED", "true")
	t.Setenv("MONEYMAKER_TLS_CA_CERT", "/etc/ssl/ca.pem")

	cfg := LoadBaseConfig()

	if cfg.Env != "production" {
		t.Errorf("Env = %q, want %q", cfg.Env, "production")
	}
	if cfg.DBHost != "db.example.com" {
		t.Errorf("DBHost = %q, want %q", cfg.DBHost, "db.example.com")
	}
	if cfg.DBPort != 5433 {
		t.Errorf("DBPort = %d, want %d", cfg.DBPort, 5433)
	}
	if cfg.DBName != "trading" {
		t.Errorf("DBName = %q, want %q", cfg.DBName, "trading")
	}
	if cfg.DBUser != "admin" {
		t.Errorf("DBUser = %q, want %q", cfg.DBUser, "admin")
	}
	if cfg.DBPassword != "s3cret" {
		t.Errorf("DBPassword = %q, want %q", cfg.DBPassword, "s3cret")
	}
	if cfg.RedisHost != "redis.example.com" {
		t.Errorf("RedisHost = %q, want %q", cfg.RedisHost, "redis.example.com")
	}
	if cfg.RedisPort != 6380 {
		t.Errorf("RedisPort = %d, want %d", cfg.RedisPort, 6380)
	}
	if cfg.RedisPassword != "redispw" {
		t.Errorf("RedisPassword = %q, want %q", cfg.RedisPassword, "redispw")
	}
	if cfg.ZMQPubAddr != "tcp://zmq:5556" {
		t.Errorf("ZMQPubAddr = %q, want %q", cfg.ZMQPubAddr, "tcp://zmq:5556")
	}
	if cfg.MetricsPort != 9091 {
		t.Errorf("MetricsPort = %d, want %d", cfg.MetricsPort, 9091)
	}
	if !cfg.TLSEnabled {
		t.Error("TLSEnabled should be true")
	}
	if cfg.TLSCACert != "/etc/ssl/ca.pem" {
		t.Errorf("TLSCACert = %q, want %q", cfg.TLSCACert, "/etc/ssl/ca.pem")
	}
}

func TestGetEnvIntInvalidValue(t *testing.T) {
	t.Setenv("MONEYMAKER_DB_PORT", "notanumber")
	result := getEnvInt("MONEYMAKER_DB_PORT", 5432)
	if result != 5432 {
		t.Errorf("getEnvInt with invalid value = %d, want %d", result, 5432)
	}
}

func TestGetEnvBoolValues(t *testing.T) {
	tests := []struct {
		value    string
		fallback bool
		want     bool
	}{
		{"true", false, true},
		{"TRUE", false, true},
		{"True", false, true},
		{"1", false, true},
		{"yes", false, true},
		{"YES", false, true},
		{"Yes", false, true},
		{"false", true, false},
		{"FALSE", true, false},
		{"False", true, false},
		{"0", true, false},
		{"no", true, false},
		{"NO", true, false},
		{"No", true, false},
		{"invalid", false, false},
		{"invalid", true, true},
		{"", false, false},
		{"", true, true},
	}

	for _, tt := range tests {
		t.Run(tt.value+"_fallback_"+boolStr(tt.fallback), func(t *testing.T) {
			t.Setenv("TEST_BOOL", tt.value)
			got := getEnvBool("TEST_BOOL", tt.fallback)
			if got != tt.want {
				t.Errorf("getEnvBool(%q, %v) = %v, want %v", tt.value, tt.fallback, got, tt.want)
			}
		})
	}
}

func boolStr(b bool) string {
	if b {
		return "true"
	}
	return "false"
}

func TestDatabaseURLDevDefault(t *testing.T) {
	cfg := &BaseConfig{
		Env:      "development",
		DBUser:   "moneymaker",
		DBHost:   "localhost",
		DBPort:   5432,
		DBName:   "moneymaker",
		TLSEnabled: false,
	}

	url := cfg.DatabaseURL()
	want := "postgres://moneymaker:@localhost:5432/moneymaker?sslmode=disable"
	if url != want {
		t.Errorf("DatabaseURL() = %q, want %q", url, want)
	}
}

func TestDatabaseURLProduction(t *testing.T) {
	cfg := &BaseConfig{
		Env:        "production",
		DBUser:     "admin",
		DBPassword: "s3cret",
		DBHost:     "db.prod.com",
		DBPort:     5432,
		DBName:     "trading",
		TLSEnabled: false,
	}

	url := cfg.DatabaseURL()
	want := "postgres://admin:s3cret@db.prod.com:5432/trading?sslmode=require"
	if url != want {
		t.Errorf("DatabaseURL() = %q, want %q", url, want)
	}
}

func TestDatabaseURLWithTLS(t *testing.T) {
	cfg := &BaseConfig{
		Env:        "production",
		DBUser:     "admin",
		DBPassword: "pass",
		DBHost:     "db.prod.com",
		DBPort:     5432,
		DBName:     "trading",
		TLSEnabled: true,
		TLSCACert:  "/etc/ssl/ca.pem",
	}

	url := cfg.DatabaseURL()
	want := "postgres://admin:pass@db.prod.com:5432/trading?sslmode=verify-full&sslrootcert=/etc/ssl/ca.pem"
	if url != want {
		t.Errorf("DatabaseURL() = %q, want %q", url, want)
	}
}

func TestDatabaseURLWithTLSNoCA(t *testing.T) {
	cfg := &BaseConfig{
		Env:        "development",
		DBUser:     "user",
		DBHost:     "localhost",
		DBPort:     5432,
		DBName:     "test",
		TLSEnabled: true,
	}

	url := cfg.DatabaseURL()
	want := "postgres://user:@localhost:5432/test?sslmode=verify-full"
	if url != want {
		t.Errorf("DatabaseURL() = %q, want %q", url, want)
	}
}

func TestDatabaseURLPasswordEscaping(t *testing.T) {
	cfg := &BaseConfig{
		Env:        "development",
		DBUser:     "user",
		DBPassword: "p@ss/word",
		DBHost:     "localhost",
		DBPort:     5432,
		DBName:     "test",
	}

	u := cfg.DatabaseURL()
	// url.PathEscape encodes / as %2F but keeps @ as-is
	want := "postgres://user:p@ss%2Fword@localhost:5432/test?sslmode=disable"
	if u != want {
		t.Errorf("DatabaseURL() = %q, want %q", u, want)
	}
}

func TestRedisURLDefault(t *testing.T) {
	cfg := &BaseConfig{
		RedisHost: "localhost",
		RedisPort: 6379,
	}

	url := cfg.RedisURL()
	want := "redis://localhost:6379/0"
	if url != want {
		t.Errorf("RedisURL() = %q, want %q", url, want)
	}
}

func TestRedisURLWithPassword(t *testing.T) {
	cfg := &BaseConfig{
		RedisHost:     "redis.example.com",
		RedisPort:     6380,
		RedisPassword: "secret",
	}

	url := cfg.RedisURL()
	want := "redis://:secret@redis.example.com:6380/0"
	if url != want {
		t.Errorf("RedisURL() = %q, want %q", url, want)
	}
}

func TestRedisURLWithTLS(t *testing.T) {
	cfg := &BaseConfig{
		RedisHost:  "redis.example.com",
		RedisPort:  6380,
		TLSEnabled: true,
	}

	url := cfg.RedisURL()
	want := "rediss://redis.example.com:6380/0"
	if url != want {
		t.Errorf("RedisURL() = %q, want %q", url, want)
	}
}

func TestRedisURLWithTLSAndPassword(t *testing.T) {
	cfg := &BaseConfig{
		RedisHost:     "redis.example.com",
		RedisPort:     6380,
		RedisPassword: "pw",
		TLSEnabled:    true,
	}

	url := cfg.RedisURL()
	want := "rediss://:pw@redis.example.com:6380/0"
	if url != want {
		t.Errorf("RedisURL() = %q, want %q", url, want)
	}
}

func TestIsProduction(t *testing.T) {
	tests := []struct {
		env  string
		want bool
	}{
		{"production", true},
		{"development", false},
		{"staging", false},
		{"", false},
	}

	for _, tt := range tests {
		t.Run(tt.env, func(t *testing.T) {
			cfg := &BaseConfig{Env: tt.env}
			if got := cfg.IsProduction(); got != tt.want {
				t.Errorf("IsProduction() with env=%q = %v, want %v", tt.env, got, tt.want)
			}
		})
	}
}

func TestValidateProductionDevNoOp(t *testing.T) {
	cfg := &BaseConfig{Env: "development", DBPassword: ""}
	// Should not panic or exit in development mode
	cfg.ValidateProduction()
}
