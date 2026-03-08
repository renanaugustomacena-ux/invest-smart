// Package ratelimit provides rate limiting for MONEYMAKER Go services.
//
// Implementa l'algoritmo Token Bucket con storage Redis per garantire
// rate limiting distribuito tra multiple istanze del servizio.
//
// Come il "vigile urbano" della fabbrica: limita il traffico in entrata
// per evitare sovraccarichi e attacchi DoS.
package ratelimit

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/redis/go-redis/v9"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/peer"
	"google.golang.org/grpc/status"
)

// ============================================================
// Errors
// ============================================================

// ErrRateLimitExceeded is returned when rate limit is exceeded.
var ErrRateLimitExceeded = errors.New("rate limit exceeded")

// RateLimitError provides detailed information about rate limit violation.
type RateLimitError struct {
	Key           string
	Limit         int
	WindowSeconds int
	RetryAfter    float64
}

func (e *RateLimitError) Error() string {
	msg := fmt.Sprintf("rate limit exceeded for '%s': max %d requests per %ds",
		e.Key, e.Limit, e.WindowSeconds)
	if e.RetryAfter > 0 {
		msg += fmt.Sprintf(" (retry after %.1fs)", e.RetryAfter)
	}
	return msg
}

// ============================================================
// Metrics
// ============================================================

var (
	rateLimitRequests = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "moneymaker_ratelimit_requests_total",
			Help: "Total requests processed by rate limiter",
		},
		[]string{"service", "endpoint", "status"},
	)

	rateLimitRejected = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "moneymaker_ratelimit_rejected_total",
			Help: "Requests rejected due to rate limit",
		},
		[]string{"service", "endpoint"},
	)

	rateLimitLatency = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "moneymaker_ratelimit_check_latency_seconds",
			Help:    "Rate limit check latency",
			Buckets: []float64{0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05},
		},
		[]string{"service"},
	)
)

// ============================================================
// Configuration
// ============================================================

// Config holds rate limit configuration.
type Config struct {
	// RequestsPerWindow is the maximum number of requests allowed in the window.
	RequestsPerWindow int

	// WindowSeconds is the time window in seconds.
	WindowSeconds int

	// BurstSize allows extra requests above the limit for burst handling.
	BurstSize int

	// KeyPrefix is the Redis key prefix for this rate limiter.
	KeyPrefix string
}

// DefaultConfig returns sensible defaults for public API.
func DefaultConfig() Config {
	return Config{
		RequestsPerWindow: 60,
		WindowSeconds:     60,
		BurstSize:         10,
		KeyPrefix:         "ratelimit",
	}
}

// RefillRate returns the tokens refilled per second.
func (c Config) RefillRate() float64 {
	return float64(c.RequestsPerWindow) / float64(c.WindowSeconds)
}

// MaxTokens returns the maximum bucket capacity.
func (c Config) MaxTokens() int {
	return c.RequestsPerWindow + c.BurstSize
}

// ============================================================
// Preset Configurations
// ============================================================

// Presets contains common rate limit configurations.
var Presets = struct {
	PublicAPI       Config
	InternalService Config
	Trading         Config
	HealthCheck     Config
	Strict          Config
}{
	// PublicAPI: 60 req/min with burst of 10
	PublicAPI: Config{
		RequestsPerWindow: 60,
		WindowSeconds:     60,
		BurstSize:         10,
		KeyPrefix:         "ratelimit:public",
	},
	// InternalService: 1000 req/min (more permissive)
	InternalService: Config{
		RequestsPerWindow: 1000,
		WindowSeconds:     60,
		BurstSize:         100,
		KeyPrefix:         "ratelimit:internal",
	},
	// Trading: 10 trades/min (conservative)
	Trading: Config{
		RequestsPerWindow: 10,
		WindowSeconds:     60,
		BurstSize:         5,
		KeyPrefix:         "ratelimit:trading",
	},
	// HealthCheck: 300 req/min
	HealthCheck: Config{
		RequestsPerWindow: 300,
		WindowSeconds:     60,
		BurstSize:         50,
		KeyPrefix:         "ratelimit:health",
	},
	// Strict: 5 req/min (for sensitive operations)
	Strict: Config{
		RequestsPerWindow: 5,
		WindowSeconds:     60,
		BurstSize:         2,
		KeyPrefix:         "ratelimit:strict",
	},
}

// ============================================================
// Rate Limiter Interface
// ============================================================

// RateLimiter defines the rate limiter interface.
type RateLimiter interface {
	// Check returns whether a request is allowed.
	// Returns (allowed, retryAfter, remainingTokens).
	Check(ctx context.Context, identifier, endpoint string) (bool, float64, int, error)

	// CheckOrFail returns an error if rate limit is exceeded.
	CheckOrFail(ctx context.Context, identifier, endpoint string) error
}

// ============================================================
// Redis Rate Limiter
// ============================================================

// tokenBucketScript is the Lua script for atomic token bucket operation.
// Returns: [tokens_remaining, retry_after_seconds]
const tokenBucketScript = `
local key = KEYS[1]
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_seconds = tonumber(ARGV[4])

-- Get current state
local data = redis.call('HMGET', key, 'tokens', 'last_update')
local tokens = tonumber(data[1])
local last_update = tonumber(data[2])

-- Initialize if not exists
if tokens == nil then
    tokens = max_tokens
    last_update = now
end

-- Calculate refilled tokens
local elapsed = now - last_update
local refilled = math.floor(elapsed * refill_rate)
tokens = math.min(max_tokens, tokens + refilled)

-- Try to consume a token
if tokens >= 1 then
    tokens = tokens - 1
    redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
    redis.call('EXPIRE', key, window_seconds * 2)
    return {tokens, 0}
else
    -- Calculate wait time for next token
    local wait_time = (1 - tokens) / refill_rate
    redis.call('HMSET', key, 'last_update', now)
    redis.call('EXPIRE', key, window_seconds * 2)
    return {tokens, wait_time}
end
`

// RedisLimiter implements rate limiting with Redis backend.
type RedisLimiter struct {
	client      *redis.Client
	config      Config
	serviceName string
	scriptSHA   string
	mu          sync.RWMutex
}

// NewRedisLimiter creates a new Redis-backed rate limiter.
func NewRedisLimiter(client *redis.Client, config Config, serviceName string) *RedisLimiter {
	return &RedisLimiter{
		client:      client,
		config:      config,
		serviceName: serviceName,
	}
}

// makeKey constructs the Redis key for a client/endpoint pair.
func (r *RedisLimiter) makeKey(identifier, endpoint string) string {
	// Hash identifier for privacy and consistent length
	hash := sha256.Sum256([]byte(identifier))
	idHash := hex.EncodeToString(hash[:8])
	return fmt.Sprintf("%s:%s:%s:%s", r.config.KeyPrefix, r.serviceName, endpoint, idHash)
}

// ensureScript loads the Lua script if not already cached.
func (r *RedisLimiter) ensureScript(ctx context.Context) (string, error) {
	r.mu.RLock()
	sha := r.scriptSHA
	r.mu.RUnlock()

	if sha != "" {
		return sha, nil
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	// Double-check after acquiring write lock
	if r.scriptSHA != "" {
		return r.scriptSHA, nil
	}

	sha, err := r.client.ScriptLoad(ctx, tokenBucketScript).Result()
	if err != nil {
		return "", err
	}

	r.scriptSHA = sha
	return sha, nil
}

// Check implements RateLimiter.Check.
func (r *RedisLimiter) Check(ctx context.Context, identifier, endpoint string) (bool, float64, int, error) {
	start := time.Now()
	key := r.makeKey(identifier, endpoint)

	defer func() {
		rateLimitLatency.WithLabelValues(r.serviceName).Observe(time.Since(start).Seconds())
	}()

	sha, err := r.ensureScript(ctx)
	if err != nil {
		// Fail-open on Redis errors
		return true, 0, r.config.MaxTokens(), nil
	}

	result, err := r.client.EvalSha(ctx, sha, []string{key},
		r.config.MaxTokens(),
		r.config.RefillRate(),
		float64(time.Now().Unix()),
		r.config.WindowSeconds,
	).Result()
	if err != nil {
		// Fail-open on Redis errors
		return true, 0, r.config.MaxTokens(), nil
	}

	// Parse result
	arr, ok := result.([]interface{})
	if !ok || len(arr) != 2 {
		return true, 0, r.config.MaxTokens(), nil
	}

	tokensRemaining := int(arr[0].(int64))
	retryAfter := arr[1].(float64)
	allowed := retryAfter == 0

	// Record metrics
	status := "allowed"
	if !allowed {
		status = "rejected"
		rateLimitRejected.WithLabelValues(r.serviceName, endpoint).Inc()
	}
	rateLimitRequests.WithLabelValues(r.serviceName, endpoint, status).Inc()

	return allowed, retryAfter, tokensRemaining, nil
}

// CheckOrFail implements RateLimiter.CheckOrFail.
func (r *RedisLimiter) CheckOrFail(ctx context.Context, identifier, endpoint string) error {
	allowed, retryAfter, _, err := r.Check(ctx, identifier, endpoint)
	if err != nil {
		return err
	}

	if !allowed {
		return &RateLimitError{
			Key:           fmt.Sprintf("%s:%s", endpoint, identifier),
			Limit:         r.config.RequestsPerWindow,
			WindowSeconds: r.config.WindowSeconds,
			RetryAfter:    retryAfter,
		}
	}

	return nil
}

// ============================================================
// In-Memory Rate Limiter (fallback)
// ============================================================

type bucket struct {
	tokens     float64
	lastUpdate time.Time
}

// MemoryLimiter implements in-memory rate limiting (non-distributed).
type MemoryLimiter struct {
	config      Config
	serviceName string
	buckets     map[string]*bucket
	mu          sync.Mutex
}

// NewMemoryLimiter creates a new in-memory rate limiter.
func NewMemoryLimiter(config Config, serviceName string) *MemoryLimiter {
	return &MemoryLimiter{
		config:      config,
		serviceName: serviceName,
		buckets:     make(map[string]*bucket),
	}
}

func (m *MemoryLimiter) makeKey(identifier, endpoint string) string {
	return fmt.Sprintf("%s:%s", endpoint, identifier)
}

// Check implements RateLimiter.Check.
func (m *MemoryLimiter) Check(ctx context.Context, identifier, endpoint string) (bool, float64, int, error) {
	start := time.Now()
	key := m.makeKey(identifier, endpoint)

	m.mu.Lock()
	defer m.mu.Unlock()

	now := time.Now()

	// Get or create bucket
	b, exists := m.buckets[key]
	if !exists {
		b = &bucket{
			tokens:     float64(m.config.MaxTokens()),
			lastUpdate: now,
		}
		m.buckets[key] = b
	}

	// Refill tokens
	elapsed := now.Sub(b.lastUpdate).Seconds()
	refilled := elapsed * m.config.RefillRate()
	b.tokens = min(float64(m.config.MaxTokens()), b.tokens+refilled)
	b.lastUpdate = now

	// Try to consume
	var allowed bool
	var retryAfter float64

	if b.tokens >= 1 {
		b.tokens--
		allowed = true
		retryAfter = 0
	} else {
		allowed = false
		retryAfter = (1 - b.tokens) / m.config.RefillRate()
	}

	// Record metrics
	status := "allowed"
	if !allowed {
		status = "rejected"
		rateLimitRejected.WithLabelValues(m.serviceName, endpoint).Inc()
	}
	rateLimitRequests.WithLabelValues(m.serviceName, endpoint, status).Inc()
	rateLimitLatency.WithLabelValues(m.serviceName).Observe(time.Since(start).Seconds())

	return allowed, retryAfter, int(b.tokens), nil
}

// CheckOrFail implements RateLimiter.CheckOrFail.
func (m *MemoryLimiter) CheckOrFail(ctx context.Context, identifier, endpoint string) error {
	allowed, retryAfter, _, err := m.Check(ctx, identifier, endpoint)
	if err != nil {
		return err
	}

	if !allowed {
		return &RateLimitError{
			Key:           fmt.Sprintf("%s:%s", endpoint, identifier),
			Limit:         m.config.RequestsPerWindow,
			WindowSeconds: m.config.WindowSeconds,
			RetryAfter:    retryAfter,
		}
	}

	return nil
}

// Cleanup removes expired buckets to prevent memory growth.
func (m *MemoryLimiter) Cleanup(maxAge time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()

	now := time.Now()
	for key, b := range m.buckets {
		if now.Sub(b.lastUpdate) > maxAge {
			delete(m.buckets, key)
		}
	}
}

// ============================================================
// gRPC Interceptor
// ============================================================

// UnaryServerInterceptor returns a gRPC unary server interceptor for rate limiting.
func UnaryServerInterceptor(limiter RateLimiter, excludeMethods ...string) grpc.UnaryServerInterceptor {
	excluded := make(map[string]bool)
	for _, m := range excludeMethods {
		excluded[m] = true
	}

	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		// Skip excluded methods
		if excluded[info.FullMethod] {
			return handler(ctx, req)
		}

		// Extract client identifier
		identifier := extractIdentifier(ctx)

		// Check rate limit
		err := limiter.CheckOrFail(ctx, identifier, info.FullMethod)
		if err != nil {
			var rlErr *RateLimitError
			if errors.As(err, &rlErr) {
				return nil, status.Errorf(codes.ResourceExhausted,
					"Rate limit exceeded. Retry after %.1fs", rlErr.RetryAfter)
			}
			return nil, status.Error(codes.Internal, "Rate limit check failed")
		}

		return handler(ctx, req)
	}
}

// StreamServerInterceptor returns a gRPC stream server interceptor for rate limiting.
func StreamServerInterceptor(limiter RateLimiter, excludeMethods ...string) grpc.StreamServerInterceptor {
	excluded := make(map[string]bool)
	for _, m := range excludeMethods {
		excluded[m] = true
	}

	return func(srv interface{}, ss grpc.ServerStream, info *grpc.StreamServerInfo, handler grpc.StreamHandler) error {
		// Skip excluded methods
		if excluded[info.FullMethod] {
			return handler(srv, ss)
		}

		// Extract client identifier
		identifier := extractIdentifier(ss.Context())

		// Check rate limit
		err := limiter.CheckOrFail(ss.Context(), identifier, info.FullMethod)
		if err != nil {
			var rlErr *RateLimitError
			if errors.As(err, &rlErr) {
				return status.Errorf(codes.ResourceExhausted,
					"Rate limit exceeded. Retry after %.1fs", rlErr.RetryAfter)
			}
			return status.Error(codes.Internal, "Rate limit check failed")
		}

		return handler(srv, ss)
	}
}

// extractIdentifier extracts client IP from gRPC context.
func extractIdentifier(ctx context.Context) string {
	p, ok := peer.FromContext(ctx)
	if !ok || p.Addr == nil {
		return "unknown"
	}

	addr := p.Addr.String()
	// Format: IP:PORT
	if idx := strings.LastIndex(addr, ":"); idx > 0 {
		return addr[:idx]
	}
	return addr
}

// ============================================================
// HTTP Middleware
// ============================================================

// HTTPMiddleware creates HTTP middleware for rate limiting.
func HTTPMiddleware(limiter RateLimiter, excludePaths ...string) func(http.Handler) http.Handler {
	excluded := make(map[string]bool)
	for _, p := range excludePaths {
		excluded[p] = true
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Skip excluded paths
			if excluded[r.URL.Path] {
				next.ServeHTTP(w, r)
				return
			}

			// Extract client IP (supports X-Forwarded-For for proxies)
			identifier := r.Header.Get("X-Forwarded-For")
			if identifier == "" {
				identifier = r.RemoteAddr
			}
			// Take first IP if multiple
			if idx := strings.Index(identifier, ","); idx > 0 {
				identifier = strings.TrimSpace(identifier[:idx])
			}
			// Remove port
			if idx := strings.LastIndex(identifier, ":"); idx > 0 {
				identifier = identifier[:idx]
			}

			endpoint := r.URL.Path

			allowed, retryAfter, remaining, _ := limiter.Check(r.Context(), identifier, endpoint)

			if !allowed {
				w.Header().Set("Retry-After", strconv.Itoa(int(retryAfter)+1))
				w.Header().Set("X-RateLimit-Remaining", "0")
				http.Error(w, fmt.Sprintf("Rate limit exceeded. Retry after %.1fs", retryAfter),
					http.StatusTooManyRequests)
				return
			}

			// Add rate limit headers
			w.Header().Set("X-RateLimit-Remaining", strconv.Itoa(remaining))

			next.ServeHTTP(w, r)
		})
	}
}

// ============================================================
// Factory Function
// ============================================================

// NewLimiter creates an appropriate rate limiter based on Redis availability.
// If Redis client is provided and working, uses RedisLimiter.
// Otherwise, falls back to MemoryLimiter.
func NewLimiter(ctx context.Context, redisClient *redis.Client, config Config, serviceName string) RateLimiter {
	if redisClient != nil {
		// Test Redis connection
		if err := redisClient.Ping(ctx).Err(); err == nil {
			return NewRedisLimiter(redisClient, config, serviceName)
		}
	}

	// Fallback to in-memory
	return NewMemoryLimiter(config, serviceName)
}
