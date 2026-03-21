package publisher

import (
	"errors"
	"sync"
	"testing"
	"time"
)

// ---------------------------------------------------------------------------
// NewPublisher + real ZMQ PUB/SUB
// ---------------------------------------------------------------------------

func TestNewPublisherBindsSuccessfully(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15550")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	defer pub.Close()

	if pub.Addr() != "tcp://127.0.0.1:15550" {
		t.Errorf("Addr() = %q, want tcp://127.0.0.1:15550", pub.Addr())
	}
}

func TestNewPublisherInvalidAddrErrors(t *testing.T) {
	// An address that ZMQ cannot bind to
	_, err := NewPublisher("tcp://999.999.999.999:99999")
	if err == nil {
		t.Error("NewPublisher should fail on invalid address")
	}
}

// ---------------------------------------------------------------------------
// Publish
// ---------------------------------------------------------------------------

func TestPublishOnOpenSocket(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15551")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	defer pub.Close()

	err = pub.Publish("test.topic", []byte(`{"price":"50000"}`))
	if err != nil {
		t.Errorf("Publish should succeed on open socket: %v", err)
	}
}

func TestPublishAfterCloseErrors(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15552")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	pub.Close()

	err = pub.Publish("test.topic", []byte("data"))
	if err == nil {
		t.Error("Publish after Close should error")
	}
}

// ---------------------------------------------------------------------------
// PublishTick
// ---------------------------------------------------------------------------

func TestPublishTickFormsTopic(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15553")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	defer pub.Close()

	err = pub.PublishTick("trade", "binance", "BTC/USDT", []byte(`{"p":"50000"}`))
	if err != nil {
		t.Errorf("PublishTick should succeed: %v", err)
	}
}

// ---------------------------------------------------------------------------
// Ping
// ---------------------------------------------------------------------------

func TestPingOnOpenSocket(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15554")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	defer pub.Close()

	if err := pub.Ping(); err != nil {
		t.Errorf("Ping should return nil on open socket: %v", err)
	}
}

func TestPingOnClosedSocket(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15555")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	pub.Close()

	err = pub.Ping()
	if err == nil {
		t.Error("Ping after Close should error")
	}
}

// ---------------------------------------------------------------------------
// Close
// ---------------------------------------------------------------------------

func TestCloseIdempotent(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15556")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}

	err1 := pub.Close()
	err2 := pub.Close()
	if err1 != nil {
		t.Errorf("first Close should succeed: %v", err1)
	}
	if err2 != nil {
		t.Errorf("second Close should be idempotent nil: %v", err2)
	}
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

func TestStatsInitialValues(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15557")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	defer pub.Close()

	stats := pub.Stats()
	if stats.MessagesSent != 0 {
		t.Errorf("MessagesSent = %d, want 0", stats.MessagesSent)
	}
	if stats.BytesSent != 0 {
		t.Errorf("BytesSent = %d, want 0", stats.BytesSent)
	}
	if stats.Errors != 0 {
		t.Errorf("Errors = %d, want 0", stats.Errors)
	}
}

func TestStatsAfterPublish(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15558")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	defer pub.Close()

	payload := []byte(`{"test":"data"}`)
	pub.Publish("topic", payload)
	pub.Publish("topic", payload)

	stats := pub.Stats()
	if stats.MessagesSent != 2 {
		t.Errorf("MessagesSent = %d, want 2", stats.MessagesSent)
	}
	if stats.BytesSent != int64(len(payload)*2) {
		t.Errorf("BytesSent = %d, want %d", stats.BytesSent, len(payload)*2)
	}
	if stats.LastPublishAt.IsZero() {
		t.Error("LastPublishAt should be set after publish")
	}
}

// ---------------------------------------------------------------------------
// PublishStats record methods
// ---------------------------------------------------------------------------

func TestRecordSuccess(t *testing.T) {
	var s PublishStats
	s.recordSuccess(100)
	s.recordSuccess(200)

	s.mu.Lock()
	defer s.mu.Unlock()
	if s.MessagesSent != 2 {
		t.Errorf("MessagesSent = %d, want 2", s.MessagesSent)
	}
	if s.BytesSent != 300 {
		t.Errorf("BytesSent = %d, want 300", s.BytesSent)
	}
	if s.LastPublishAt.IsZero() {
		t.Error("LastPublishAt should be set")
	}
}

func TestRecordError(t *testing.T) {
	var s PublishStats
	s.recordError(errors.New("test error"))

	s.mu.Lock()
	defer s.mu.Unlock()
	if s.Errors != 1 {
		t.Errorf("Errors = %d, want 1", s.Errors)
	}
	if s.LastErrorMsg != "test error" {
		t.Errorf("LastErrorMsg = %q, want test error", s.LastErrorMsg)
	}
	if s.LastErrorAt.IsZero() {
		t.Error("LastErrorAt should be set")
	}
}

// ---------------------------------------------------------------------------
// Concurrent publish
// ---------------------------------------------------------------------------

func TestConcurrentPublish(t *testing.T) {
	pub, err := NewPublisher("tcp://127.0.0.1:15559")
	if err != nil {
		t.Fatalf("NewPublisher failed: %v", err)
	}
	defer pub.Close()

	var wg sync.WaitGroup
	goroutines := 5
	msgsPerGoroutine := 20

	wg.Add(goroutines)
	for i := 0; i < goroutines; i++ {
		go func() {
			defer wg.Done()
			for j := 0; j < msgsPerGoroutine; j++ {
				pub.Publish("concurrent.test", []byte("data"))
			}
		}()
	}
	wg.Wait()

	// Allow stats to settle
	time.Sleep(10 * time.Millisecond)

	stats := pub.Stats()
	expected := int64(goroutines * msgsPerGoroutine)
	if stats.MessagesSent != expected {
		t.Errorf("MessagesSent = %d, want %d", stats.MessagesSent, expected)
	}
}
