// Package health provides the health check protocol for MONEYMAKER Go services.
package health

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"
)

// Status represents service health status.
type Status string

const (
	StatusHealthy   Status = "healthy"
	StatusDegraded  Status = "degraded"
	StatusUnhealthy Status = "unhealthy"
)

// CheckResult contains the result of a health check.
type CheckResult struct {
	Status        Status            `json:"status"`
	Message       string            `json:"message"`
	Details       map[string]string `json:"details,omitempty"`
	UptimeSeconds float64           `json:"uptime_seconds"`
}

// Checker manages health checks for a service.
type Checker struct {
	serviceName string
	startTime   time.Time
	ready       bool
	mu          sync.RWMutex
	checks      map[string]func() error
}

// NewChecker creates a new health checker.
func NewChecker(serviceName string) *Checker {
	return &Checker{
		serviceName: serviceName,
		startTime:   time.Now(),
		checks:      make(map[string]func() error),
	}
}

// SetReady marks the service as ready to accept requests.
func (c *Checker) SetReady() {
	c.mu.Lock()
	c.ready = true
	c.mu.Unlock()
}

// SetNotReady marks the service as not ready.
func (c *Checker) SetNotReady() {
	c.mu.Lock()
	c.ready = false
	c.mu.Unlock()
}

// RegisterCheck adds a dependency check function.
func (c *Checker) RegisterCheck(name string, fn func() error) {
	c.checks[name] = fn
}

// RegisterHTTPHandlers registers /healthz, /readyz, /health on the given mux.
func (c *Checker) RegisterHTTPHandlers(mux *http.ServeMux) {
	mux.HandleFunc("/healthz", c.handleLiveness)
	mux.HandleFunc("/readyz", c.handleReadiness)
	mux.HandleFunc("/health", c.handleDeep)
}

func (c *Checker) handleLiveness(w http.ResponseWriter, r *http.Request) {
	result := CheckResult{
		Status:        StatusHealthy,
		Message:       "alive",
		UptimeSeconds: time.Since(c.startTime).Seconds(),
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

func (c *Checker) handleReadiness(w http.ResponseWriter, r *http.Request) {
	c.mu.RLock()
	ready := c.ready
	c.mu.RUnlock()

	result := CheckResult{UptimeSeconds: time.Since(c.startTime).Seconds()}
	if ready {
		result.Status = StatusHealthy
		result.Message = "ready"
	} else {
		result.Status = StatusUnhealthy
		result.Message = "not ready"
		w.WriteHeader(http.StatusServiceUnavailable)
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}

func (c *Checker) handleDeep(w http.ResponseWriter, r *http.Request) {
	details := make(map[string]string)
	overall := StatusHealthy

	for name, fn := range c.checks {
		if err := fn(); err != nil {
			details[name] = "error: " + err.Error()
			overall = StatusUnhealthy
		} else {
			details[name] = "ok"
		}
	}

	result := CheckResult{
		Status:        overall,
		Details:       details,
		UptimeSeconds: time.Since(c.startTime).Seconds(),
	}
	if overall != StatusHealthy {
		result.Message = "some checks failed"
		w.WriteHeader(http.StatusServiceUnavailable)
	} else {
		result.Message = "all checks passed"
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(result)
}
