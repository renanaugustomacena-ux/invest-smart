package ratelimit

import (
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/peer"
	grpcstatus "google.golang.org/grpc/status"
)

// ─── Config Tests ────────────────────────────────────────────────────────────

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.RequestsPerWindow != 60 {
		t.Errorf("RequestsPerWindow = %d, want 60", cfg.RequestsPerWindow)
	}
	if cfg.WindowSeconds != 60 {
		t.Errorf("WindowSeconds = %d, want 60", cfg.WindowSeconds)
	}
	if cfg.BurstSize != 10 {
		t.Errorf("BurstSize = %d, want 10", cfg.BurstSize)
	}
	if cfg.KeyPrefix != "ratelimit" {
		t.Errorf("KeyPrefix = %q, want %q", cfg.KeyPrefix, "ratelimit")
	}
}

func TestConfigRefillRate(t *testing.T) {
	cfg := Config{RequestsPerWindow: 60, WindowSeconds: 60}
	if rate := cfg.RefillRate(); rate != 1.0 {
		t.Errorf("RefillRate() = %f, want 1.0", rate)
	}

	cfg2 := Config{RequestsPerWindow: 120, WindowSeconds: 60}
	if rate := cfg2.RefillRate(); rate != 2.0 {
		t.Errorf("RefillRate() = %f, want 2.0", rate)
	}
}

func TestConfigMaxTokens(t *testing.T) {
	cfg := Config{RequestsPerWindow: 60, BurstSize: 10}
	if max := cfg.MaxTokens(); max != 70 {
		t.Errorf("MaxTokens() = %d, want 70", max)
	}

	cfg2 := Config{RequestsPerWindow: 100, BurstSize: 0}
	if max := cfg2.MaxTokens(); max != 100 {
		t.Errorf("MaxTokens() = %d, want 100", max)
	}
}

func TestPresets(t *testing.T) {
	if Presets.PublicAPI.RequestsPerWindow != 60 {
		t.Errorf("PublicAPI.RequestsPerWindow = %d, want 60", Presets.PublicAPI.RequestsPerWindow)
	}
	if Presets.InternalService.RequestsPerWindow != 1000 {
		t.Errorf("InternalService.RequestsPerWindow = %d, want 1000", Presets.InternalService.RequestsPerWindow)
	}
	if Presets.Trading.RequestsPerWindow != 10 {
		t.Errorf("Trading.RequestsPerWindow = %d, want 10", Presets.Trading.RequestsPerWindow)
	}
	if Presets.HealthCheck.RequestsPerWindow != 300 {
		t.Errorf("HealthCheck.RequestsPerWindow = %d, want 300", Presets.HealthCheck.RequestsPerWindow)
	}
	if Presets.Strict.RequestsPerWindow != 5 {
		t.Errorf("Strict.RequestsPerWindow = %d, want 5", Presets.Strict.RequestsPerWindow)
	}
}

// ─── RateLimitError Tests ────────────────────────────────────────────────────

func TestRateLimitErrorMessage(t *testing.T) {
	err := &RateLimitError{
		Key:           "test:user1",
		Limit:         60,
		WindowSeconds: 60,
		RetryAfter:    0,
	}
	msg := err.Error()
	if !strings.Contains(msg, "rate limit exceeded") {
		t.Errorf("Error() = %q, should contain 'rate limit exceeded'", msg)
	}
	if !strings.Contains(msg, "test:user1") {
		t.Errorf("Error() = %q, should contain key", msg)
	}
	if strings.Contains(msg, "retry after") {
		t.Errorf("Error() = %q, should NOT contain 'retry after' when RetryAfter=0", msg)
	}
}

func TestRateLimitErrorMessageWithRetryAfter(t *testing.T) {
	err := &RateLimitError{
		Key:           "test:user1",
		Limit:         60,
		WindowSeconds: 60,
		RetryAfter:    2.5,
	}
	msg := err.Error()
	if !strings.Contains(msg, "retry after 2.5s") {
		t.Errorf("Error() = %q, should contain 'retry after 2.5s'", msg)
	}
}

// ─── MemoryLimiter Tests ─────────────────────────────────────────────────────

func TestNewMemoryLimiter(t *testing.T) {
	limiter := NewMemoryLimiter(DefaultConfig(), "test")
	if limiter == nil {
		t.Fatal("NewMemoryLimiter returned nil")
	}
	if limiter.serviceName != "test" {
		t.Errorf("serviceName = %q, want %q", limiter.serviceName, "test")
	}
}

func TestMemoryLimiterCheckFirstRequest(t *testing.T) {
	cfg := Config{RequestsPerWindow: 10, WindowSeconds: 60, BurstSize: 5}
	limiter := NewMemoryLimiter(cfg, "test")

	allowed, retryAfter, remaining, err := limiter.Check(context.Background(), "user1", "/api/test")
	if err != nil {
		t.Fatalf("Check() error = %v", err)
	}
	if !allowed {
		t.Error("first request should be allowed")
	}
	if retryAfter != 0 {
		t.Errorf("retryAfter = %f, want 0", retryAfter)
	}
	// MaxTokens = 10+5 = 15, after consuming 1 = 14
	if remaining != 14 {
		t.Errorf("remaining = %d, want 14", remaining)
	}
}

func TestMemoryLimiterExhaustion(t *testing.T) {
	cfg := Config{RequestsPerWindow: 5, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")
	ctx := context.Background()

	// Consume all 5 tokens
	for i := 0; i < 5; i++ {
		allowed, _, _, err := limiter.Check(ctx, "user1", "/api/test")
		if err != nil {
			t.Fatalf("Check() error on request %d: %v", i, err)
		}
		if !allowed {
			t.Fatalf("request %d should be allowed", i)
		}
	}

	// Next request should be rejected
	allowed, retryAfter, remaining, err := limiter.Check(ctx, "user1", "/api/test")
	if err != nil {
		t.Fatalf("Check() error: %v", err)
	}
	if allowed {
		t.Error("request should be rejected after exhaustion")
	}
	if retryAfter <= 0 {
		t.Errorf("retryAfter = %f, want > 0", retryAfter)
	}
	if remaining != 0 {
		t.Errorf("remaining = %d, want 0", remaining)
	}
}

func TestMemoryLimiterDifferentIdentifiers(t *testing.T) {
	cfg := Config{RequestsPerWindow: 2, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")
	ctx := context.Background()

	// Exhaust user1
	for i := 0; i < 2; i++ {
		limiter.Check(ctx, "user1", "/api")
	}

	// user2 should still be allowed
	allowed, _, _, _ := limiter.Check(ctx, "user2", "/api")
	if !allowed {
		t.Error("user2 should be allowed (independent from user1)")
	}
}

func TestMemoryLimiterCheckOrFailSuccess(t *testing.T) {
	cfg := Config{RequestsPerWindow: 10, WindowSeconds: 60, BurstSize: 5}
	limiter := NewMemoryLimiter(cfg, "test")

	err := limiter.CheckOrFail(context.Background(), "user1", "/api/test")
	if err != nil {
		t.Errorf("CheckOrFail() error = %v, want nil", err)
	}
}

func TestMemoryLimiterCheckOrFailRejected(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")
	ctx := context.Background()

	// Consume the only token
	limiter.Check(ctx, "user1", "/api")

	// Next should fail
	err := limiter.CheckOrFail(ctx, "user1", "/api")
	if err == nil {
		t.Fatal("CheckOrFail() should return error when exhausted")
	}

	rlErr, ok := err.(*RateLimitError)
	if !ok {
		t.Fatalf("error should be *RateLimitError, got %T", err)
	}
	if rlErr.Limit != 1 {
		t.Errorf("Limit = %d, want 1", rlErr.Limit)
	}
	if rlErr.RetryAfter <= 0 {
		t.Errorf("RetryAfter = %f, want > 0", rlErr.RetryAfter)
	}
}

func TestMemoryLimiterCleanup(t *testing.T) {
	cfg := Config{RequestsPerWindow: 10, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")
	ctx := context.Background()

	limiter.Check(ctx, "user1", "/api")
	limiter.Check(ctx, "user2", "/api")

	if len(limiter.buckets) != 2 {
		t.Errorf("buckets count = %d, want 2", len(limiter.buckets))
	}

	// Cleanup with 0 maxAge removes everything
	limiter.Cleanup(0)

	if len(limiter.buckets) != 0 {
		t.Errorf("buckets count after cleanup = %d, want 0", len(limiter.buckets))
	}
}

func TestMemoryLimiterCleanupKeepsFresh(t *testing.T) {
	cfg := Config{RequestsPerWindow: 10, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")
	ctx := context.Background()

	limiter.Check(ctx, "user1", "/api")

	// Cleanup with long maxAge keeps the bucket
	limiter.Cleanup(time.Hour)

	if len(limiter.buckets) != 1 {
		t.Errorf("buckets count after cleanup = %d, want 1", len(limiter.buckets))
	}
}

// ─── extractIdentifier Tests ─────────────────────────────────────────────────

func TestExtractIdentifierWithPeer(t *testing.T) {
	ctx := peer.NewContext(context.Background(), &peer.Peer{
		Addr: &net.TCPAddr{IP: net.ParseIP("192.168.1.1"), Port: 5000},
	})

	id := extractIdentifier(ctx)
	if id != "192.168.1.1" {
		t.Errorf("extractIdentifier() = %q, want %q", id, "192.168.1.1")
	}
}

func TestExtractIdentifierNoPeer(t *testing.T) {
	id := extractIdentifier(context.Background())
	if id != "unknown" {
		t.Errorf("extractIdentifier() = %q, want %q", id, "unknown")
	}
}

// ─── HTTP Middleware Tests ───────────────────────────────────────────────────

func TestHTTPMiddlewareAllowed(t *testing.T) {
	cfg := Config{RequestsPerWindow: 100, WindowSeconds: 60, BurstSize: 10}
	limiter := NewMemoryLimiter(cfg, "test")

	handler := HTTPMiddleware(limiter)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	}))

	req := httptest.NewRequest(http.MethodGet, "/api/test", nil)
	req.RemoteAddr = "192.168.1.1:5000"
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	remaining := rec.Header().Get("X-RateLimit-Remaining")
	if remaining == "" {
		t.Error("X-RateLimit-Remaining header missing")
	}
}

func TestHTTPMiddlewareRejected(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")

	handler := HTTPMiddleware(limiter)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	// First request consumes the only token
	req := httptest.NewRequest(http.MethodGet, "/api/test", nil)
	req.RemoteAddr = "192.168.1.1:5000"
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("first request status = %d, want %d", rec.Code, http.StatusOK)
	}

	// Second request should be rate limited
	req2 := httptest.NewRequest(http.MethodGet, "/api/test", nil)
	req2.RemoteAddr = "192.168.1.1:5000"
	rec2 := httptest.NewRecorder()
	handler.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusTooManyRequests {
		t.Errorf("status = %d, want %d", rec2.Code, http.StatusTooManyRequests)
	}

	retryAfter := rec2.Header().Get("Retry-After")
	if retryAfter == "" {
		t.Error("Retry-After header missing")
	}

	remaining := rec2.Header().Get("X-RateLimit-Remaining")
	if remaining != "0" {
		t.Errorf("X-RateLimit-Remaining = %q, want %q", remaining, "0")
	}
}

func TestHTTPMiddlewareExcludedPaths(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")

	handler := HTTPMiddleware(limiter, "/health", "/healthz")(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	// Exhaust the limiter
	req := httptest.NewRequest(http.MethodGet, "/api/test", nil)
	req.RemoteAddr = "10.0.0.1:5000"
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	// Health endpoint should still work (excluded)
	req2 := httptest.NewRequest(http.MethodGet, "/health", nil)
	req2.RemoteAddr = "10.0.0.1:5000"
	rec2 := httptest.NewRecorder()
	handler.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusOK {
		t.Errorf("excluded path status = %d, want %d", rec2.Code, http.StatusOK)
	}
}

func TestHTTPMiddlewareXForwardedFor(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")

	handler := HTTPMiddleware(limiter)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	// Use X-Forwarded-For to identify a different client
	req := httptest.NewRequest(http.MethodGet, "/api/test", nil)
	req.Header.Set("X-Forwarded-For", "203.0.113.1, 10.0.0.1")
	req.RemoteAddr = "127.0.0.1:5000"
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
}

// ─── gRPC Interceptor Tests ─────────────────────────────────────────────────

func TestUnaryServerInterceptorAllowed(t *testing.T) {
	cfg := Config{RequestsPerWindow: 100, WindowSeconds: 60, BurstSize: 10}
	limiter := NewMemoryLimiter(cfg, "test")

	interceptor := UnaryServerInterceptor(limiter)

	ctx := peer.NewContext(context.Background(), &peer.Peer{
		Addr: &net.TCPAddr{IP: net.ParseIP("192.168.1.1"), Port: 5000},
	})

	info := &grpc.UnaryServerInfo{FullMethod: "/test.Service/Method"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return "response", nil
	}

	resp, err := interceptor(ctx, "request", info, handler)
	if err != nil {
		t.Fatalf("interceptor error = %v", err)
	}
	if resp != "response" {
		t.Errorf("response = %v, want %q", resp, "response")
	}
}

func TestUnaryServerInterceptorRejected(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")

	interceptor := UnaryServerInterceptor(limiter)

	ctx := peer.NewContext(context.Background(), &peer.Peer{
		Addr: &net.TCPAddr{IP: net.ParseIP("192.168.1.1"), Port: 5000},
	})

	info := &grpc.UnaryServerInfo{FullMethod: "/test.Service/Method"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return "response", nil
	}

	// First request
	_, _ = interceptor(ctx, "request", info, handler)

	// Second request should be rejected
	_, err := interceptor(ctx, "request", info, handler)
	if err == nil {
		t.Fatal("interceptor should return error when rate limited")
	}

	st, ok := grpcstatus.FromError(err)
	if !ok {
		t.Fatalf("error should be gRPC status, got %T: %v", err, err)
	}
	if st.Code() != codes.ResourceExhausted {
		t.Errorf("code = %v, want %v", st.Code(), codes.ResourceExhausted)
	}
}

func TestUnaryServerInterceptorExcluded(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")

	interceptor := UnaryServerInterceptor(limiter, "/test.Service/Health")

	ctx := peer.NewContext(context.Background(), &peer.Peer{
		Addr: &net.TCPAddr{IP: net.ParseIP("192.168.1.1"), Port: 5000},
	})

	info := &grpc.UnaryServerInfo{FullMethod: "/test.Service/Health"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return "response", nil
	}

	// Call multiple times - excluded methods bypass rate limit
	for i := 0; i < 5; i++ {
		_, err := interceptor(ctx, "request", info, handler)
		if err != nil {
			t.Fatalf("excluded method call %d error = %v", i, err)
		}
	}
}

// mockServerStream implements grpc.ServerStream for testing
type mockServerStream struct {
	grpc.ServerStream
	ctx context.Context
}

func (m *mockServerStream) Context() context.Context {
	return m.ctx
}

func TestStreamServerInterceptorAllowed(t *testing.T) {
	cfg := Config{RequestsPerWindow: 100, WindowSeconds: 60, BurstSize: 10}
	limiter := NewMemoryLimiter(cfg, "test")

	interceptor := StreamServerInterceptor(limiter)

	ctx := peer.NewContext(context.Background(), &peer.Peer{
		Addr: &net.TCPAddr{IP: net.ParseIP("192.168.1.1"), Port: 5000},
	})

	info := &grpc.StreamServerInfo{FullMethod: "/test.Service/StreamMethod"}
	stream := &mockServerStream{ctx: ctx}
	handler := func(srv interface{}, ss grpc.ServerStream) error {
		return nil
	}

	err := interceptor(nil, stream, info, handler)
	if err != nil {
		t.Fatalf("interceptor error = %v", err)
	}
}

func TestStreamServerInterceptorRejected(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")

	interceptor := StreamServerInterceptor(limiter)

	ctx := peer.NewContext(context.Background(), &peer.Peer{
		Addr: &net.TCPAddr{IP: net.ParseIP("192.168.1.1"), Port: 5000},
	})

	info := &grpc.StreamServerInfo{FullMethod: "/test.Service/StreamMethod"}
	stream := &mockServerStream{ctx: ctx}
	handler := func(srv interface{}, ss grpc.ServerStream) error {
		return nil
	}

	// First request
	_ = interceptor(nil, stream, info, handler)

	// Second request should be rejected
	err := interceptor(nil, stream, info, handler)
	if err == nil {
		t.Fatal("interceptor should return error when rate limited")
	}

	st, ok := grpcstatus.FromError(err)
	if !ok {
		t.Fatalf("error should be gRPC status, got %T: %v", err, err)
	}
	if st.Code() != codes.ResourceExhausted {
		t.Errorf("code = %v, want %v", st.Code(), codes.ResourceExhausted)
	}
}

func TestStreamServerInterceptorExcluded(t *testing.T) {
	cfg := Config{RequestsPerWindow: 1, WindowSeconds: 60, BurstSize: 0}
	limiter := NewMemoryLimiter(cfg, "test")

	interceptor := StreamServerInterceptor(limiter, "/test.Service/StreamHealth")

	ctx := peer.NewContext(context.Background(), &peer.Peer{
		Addr: &net.TCPAddr{IP: net.ParseIP("192.168.1.1"), Port: 5000},
	})

	info := &grpc.StreamServerInfo{FullMethod: "/test.Service/StreamHealth"}
	stream := &mockServerStream{ctx: ctx}
	handler := func(srv interface{}, ss grpc.ServerStream) error {
		return nil
	}

	// Call multiple times - excluded methods bypass rate limit
	for i := 0; i < 5; i++ {
		err := interceptor(nil, stream, info, handler)
		if err != nil {
			t.Fatalf("excluded method call %d error = %v", i, err)
		}
	}
}

// ─── NewLimiter Factory Tests ────────────────────────────────────────────────

func TestNewLimiterNilRedis(t *testing.T) {
	limiter := NewLimiter(context.Background(), nil, DefaultConfig(), "test")
	if limiter == nil {
		t.Fatal("NewLimiter returned nil")
	}

	// Should return a MemoryLimiter when redis is nil
	if _, ok := limiter.(*MemoryLimiter); !ok {
		t.Errorf("limiter should be *MemoryLimiter, got %T", limiter)
	}
}
