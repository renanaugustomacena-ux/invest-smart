package health

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestNewChecker(t *testing.T) {
	c := NewChecker("test-service")
	if c == nil {
		t.Fatal("NewChecker returned nil")
	}
	if c.serviceName != "test-service" {
		t.Errorf("serviceName = %q, want %q", c.serviceName, "test-service")
	}
	if c.ready {
		t.Error("ready should be false initially")
	}
}

func TestSetReadyAndNotReady(t *testing.T) {
	c := NewChecker("test")

	if c.ready {
		t.Error("should start not ready")
	}

	c.SetReady()
	if !c.ready {
		t.Error("should be ready after SetReady()")
	}

	c.SetNotReady()
	if c.ready {
		t.Error("should not be ready after SetNotReady()")
	}
}

func TestHandleLiveness(t *testing.T) {
	c := NewChecker("test")
	mux := http.NewServeMux()
	c.RegisterHTTPHandlers(mux)

	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var result CheckResult
	if err := json.NewDecoder(rec.Body).Decode(&result); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if result.Status != StatusHealthy {
		t.Errorf("status = %q, want %q", result.Status, StatusHealthy)
	}
	if result.Message != "alive" {
		t.Errorf("message = %q, want %q", result.Message, "alive")
	}
	if result.UptimeSeconds < 0 {
		t.Errorf("uptime_seconds = %f, want >= 0", result.UptimeSeconds)
	}
}

func TestHandleReadinessNotReady(t *testing.T) {
	c := NewChecker("test")
	mux := http.NewServeMux()
	c.RegisterHTTPHandlers(mux)

	req := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusServiceUnavailable)
	}

	var result CheckResult
	if err := json.NewDecoder(rec.Body).Decode(&result); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if result.Status != StatusUnhealthy {
		t.Errorf("status = %q, want %q", result.Status, StatusUnhealthy)
	}
	if result.Message != "not ready" {
		t.Errorf("message = %q, want %q", result.Message, "not ready")
	}
}

func TestHandleReadinessReady(t *testing.T) {
	c := NewChecker("test")
	c.SetReady()
	mux := http.NewServeMux()
	c.RegisterHTTPHandlers(mux)

	req := httptest.NewRequest(http.MethodGet, "/readyz", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var result CheckResult
	if err := json.NewDecoder(rec.Body).Decode(&result); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if result.Status != StatusHealthy {
		t.Errorf("status = %q, want %q", result.Status, StatusHealthy)
	}
	if result.Message != "ready" {
		t.Errorf("message = %q, want %q", result.Message, "ready")
	}
}

func TestHandleDeepAllPassing(t *testing.T) {
	c := NewChecker("test")
	c.RegisterCheck("db", func() error { return nil })
	c.RegisterCheck("redis", func() error { return nil })

	mux := http.NewServeMux()
	c.RegisterHTTPHandlers(mux)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var result CheckResult
	if err := json.NewDecoder(rec.Body).Decode(&result); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if result.Status != StatusHealthy {
		t.Errorf("status = %q, want %q", result.Status, StatusHealthy)
	}
	if result.Message != "all checks passed" {
		t.Errorf("message = %q, want %q", result.Message, "all checks passed")
	}
	if result.Details["db"] != "ok" {
		t.Errorf("details[db] = %q, want %q", result.Details["db"], "ok")
	}
	if result.Details["redis"] != "ok" {
		t.Errorf("details[redis] = %q, want %q", result.Details["redis"], "ok")
	}
}

func TestHandleDeepWithFailure(t *testing.T) {
	c := NewChecker("test")
	c.RegisterCheck("db", func() error { return nil })
	c.RegisterCheck("redis", func() error { return errors.New("connection refused") })

	mux := http.NewServeMux()
	c.RegisterHTTPHandlers(mux)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusServiceUnavailable)
	}

	var result CheckResult
	if err := json.NewDecoder(rec.Body).Decode(&result); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if result.Status != StatusUnhealthy {
		t.Errorf("status = %q, want %q", result.Status, StatusUnhealthy)
	}
	if result.Message != "some checks failed" {
		t.Errorf("message = %q, want %q", result.Message, "some checks failed")
	}
	if result.Details["db"] != "ok" {
		t.Errorf("details[db] = %q, want %q", result.Details["db"], "ok")
	}
	if result.Details["redis"] != "error: connection refused" {
		t.Errorf("details[redis] = %q, want %q", result.Details["redis"], "error: connection refused")
	}
}

func TestHandleDeepNoChecks(t *testing.T) {
	c := NewChecker("test")

	mux := http.NewServeMux()
	c.RegisterHTTPHandlers(mux)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var result CheckResult
	if err := json.NewDecoder(rec.Body).Decode(&result); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if result.Status != StatusHealthy {
		t.Errorf("status = %q, want %q", result.Status, StatusHealthy)
	}
}

func TestRegisterHTTPHandlersAllPaths(t *testing.T) {
	c := NewChecker("test")
	mux := http.NewServeMux()
	c.RegisterHTTPHandlers(mux)

	paths := []string{"/healthz", "/readyz", "/health"}
	for _, path := range paths {
		req := httptest.NewRequest(http.MethodGet, path, nil)
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)

		if rec.Code != http.StatusOK && rec.Code != http.StatusServiceUnavailable {
			t.Errorf("path %q: unexpected status %d", path, rec.Code)
		}

		contentType := rec.Header().Get("Content-Type")
		if contentType != "application/json" {
			t.Errorf("path %q: Content-Type = %q, want %q", path, contentType, "application/json")
		}
	}
}
