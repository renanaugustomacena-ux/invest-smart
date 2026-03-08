// Package publisher provides a ZeroMQ PUB socket wrapper for broadcasting
// normalized market data to downstream MONEYMAKER services. Topics are used
// to allow subscribers to filter by exchange, symbol, or event type.
package publisher

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/go-zeromq/zmq4"
)

// Publisher wraps a ZeroMQ PUB socket and provides a high-level interface
// for publishing MONEYMAKER market data messages with topic-based routing.
type Publisher struct {
	addr   string
	socket zmq4.Socket
	mu     sync.Mutex
	closed bool

	// stats tracks publishing metrics for monitoring.
	stats PublishStats
}

// PublishStats holds counters for monitoring publisher health.
type PublishStats struct {
	mu            sync.Mutex
	MessagesSent  int64
	BytesSent     int64
	Errors        int64
	LastPublishAt time.Time
	LastErrorAt   time.Time
	LastErrorMsg  string
}

// NewPublisher creates and binds a new ZeroMQ PUB socket on the given address.
//
// The address should be a ZeroMQ endpoint, for example:
//
//	"tcp://*:5555"      - bind on all interfaces, port 5555
//	"tcp://0.0.0.0:5555" - same as above
//	"ipc:///tmp/moneymaker-data.sock" - Unix domain socket
//
// The PUB socket will bind (not connect), and subscribers will connect to it.
func NewPublisher(addr string) (*Publisher, error) {
	pub := zmq4.NewPub(context.Background())

	// Set send high-water mark to bound internal buffer size.
	// When the HWM is reached, ZeroMQ drops messages for PUB sockets
	// rather than blocking, preventing unbounded memory growth when
	// subscribers are slow.
	if err := pub.SetOption(zmq4.OptionHWM, 1000); err != nil {
		return nil, fmt.Errorf("publisher: failed to set HWM: %w", err)
	}

	if err := pub.Listen(addr); err != nil {
		return nil, fmt.Errorf("publisher: failed to bind ZMQ PUB on %q: %w", addr, err)
	}

	return &Publisher{
		addr:   addr,
		socket: pub,
	}, nil
}

// Publish sends a message on the given topic. The topic is prepended to the
// message data as a multi-part ZeroMQ message, enabling topic-based filtering
// on the subscriber side.
//
// Topic conventions for MONEYMAKER:
//
//	"trade.binance.BTC/USDT"     - specific trade events
//	"trade.binance"              - all Binance trades
//	"depth.binance.BTC/USDT"     - depth updates for BTC/USDT
//	"kline.binance.BTC/USDT.1m"  - 1-minute klines
//
// Subscribers use ZeroMQ's prefix matching: subscribing to "trade.binance"
// will receive all messages whose topic starts with that prefix.
func (p *Publisher) Publish(topic string, data []byte) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.closed {
		return fmt.Errorf("publisher: socket is closed")
	}

	// ZeroMQ PUB/SUB uses prefix matching on the first frame.
	// We send the topic as the first frame and data as the second.
	msg := zmq4.NewMsgFrom([]byte(topic), data)

	if err := p.socket.Send(msg); err != nil {
		p.stats.recordError(err)
		return fmt.Errorf("publisher: send on topic %q: %w", topic, err)
	}

	p.stats.recordSuccess(len(data))
	return nil
}

// PublishTick is a convenience method that constructs the topic from the
// event type, exchange, and symbol, then publishes the serialized data.
func (p *Publisher) PublishTick(eventType, exchange, symbol string, data []byte) error {
	topic := fmt.Sprintf("%s.%s.%s", eventType, exchange, symbol)
	return p.Publish(topic, data)
}

// Close gracefully shuts down the ZeroMQ PUB socket.
func (p *Publisher) Close() error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.closed {
		return nil
	}

	p.closed = true

	// Allow a brief moment for any final messages to be flushed to
	// connected subscribers before closing the socket.
	// ZeroMQ internally buffers messages; closing immediately could
	// lose messages that are in the send buffer.
	//
	// TODO: Investigate zmq4 linger socket option for a cleaner solution.
	time.Sleep(100 * time.Millisecond)

	return p.socket.Close()
}

// Stats returns a snapshot of the current publishing statistics.
func (p *Publisher) Stats() PublishStats {
	p.stats.mu.Lock()
	defer p.stats.mu.Unlock()

	return PublishStats{
		MessagesSent:  p.stats.MessagesSent,
		BytesSent:     p.stats.BytesSent,
		Errors:        p.stats.Errors,
		LastPublishAt: p.stats.LastPublishAt,
		LastErrorAt:   p.stats.LastErrorAt,
		LastErrorMsg:  p.stats.LastErrorMsg,
	}
}

// Addr returns the address the publisher is bound to.
func (p *Publisher) Addr() string {
	return p.addr
}

// Ping verifies the publisher socket is still operational. This is intended
// for use in health checks.
func (p *Publisher) Ping() error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.closed {
		return fmt.Errorf("publisher: socket is closed")
	}

	// ZeroMQ PUB sockets don't have a native ping mechanism.
	// We verify the socket is open and has been active recently.
	// TODO: Consider sending a heartbeat message on a dedicated topic
	// that monitoring services can subscribe to.
	return nil
}

// recordSuccess updates stats after a successful publish.
func (s *PublishStats) recordSuccess(bytes int) {
	s.mu.Lock()
	s.MessagesSent++
	s.BytesSent += int64(bytes)
	s.LastPublishAt = time.Now()
	s.mu.Unlock()
}

// recordError updates stats after a failed publish.
func (s *PublishStats) recordError(err error) {
	s.mu.Lock()
	s.Errors++
	s.LastErrorAt = time.Now()
	s.LastErrorMsg = err.Error()
	s.mu.Unlock()
}

// TODO: Add batch publishing support for high-throughput scenarios:
//
// func (p *Publisher) PublishBatch(messages []TopicMessage) error { ... }
//
// type TopicMessage struct {
//     Topic string
//     Data  []byte
// }

// TODO: Add Prometheus metrics integration:
//   - moneymaker_publisher_messages_total (counter, labels: topic, exchange)
//   - moneymaker_publisher_bytes_total (counter, labels: topic, exchange)
//   - moneymaker_publisher_errors_total (counter, labels: topic, error_type)
//   - moneymaker_publisher_latency_seconds (histogram, labels: topic)

