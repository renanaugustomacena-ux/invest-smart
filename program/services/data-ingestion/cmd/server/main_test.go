package main

import (
	"testing"
)

// ---------------------------------------------------------------------------
// parseIntEnv
// ---------------------------------------------------------------------------

func TestParseIntEnvValid(t *testing.T) {
	n, err := parseIntEnv("42")
	if err != nil {
		t.Fatalf("parseIntEnv(42) error: %v", err)
	}
	if n != 42 {
		t.Errorf("parseIntEnv(42) = %d, want 42", n)
	}
}

func TestParseIntEnvZero(t *testing.T) {
	n, err := parseIntEnv("0")
	if err != nil {
		t.Fatalf("parseIntEnv(0) error: %v", err)
	}
	if n != 0 {
		t.Errorf("parseIntEnv(0) = %d, want 0", n)
	}
}

func TestParseIntEnvNegative(t *testing.T) {
	n, err := parseIntEnv("-5")
	if err != nil {
		t.Fatalf("parseIntEnv(-5) error: %v", err)
	}
	if n != -5 {
		t.Errorf("parseIntEnv(-5) = %d, want -5", n)
	}
}

func TestParseIntEnvLargeNumber(t *testing.T) {
	n, err := parseIntEnv("1000000")
	if err != nil {
		t.Fatalf("parseIntEnv(1000000) error: %v", err)
	}
	if n != 1000000 {
		t.Errorf("parseIntEnv(1000000) = %d, want 1000000", n)
	}
}

func TestParseIntEnvInvalidString(t *testing.T) {
	_, err := parseIntEnv("not-a-number")
	if err == nil {
		t.Error("parseIntEnv(not-a-number) should error")
	}
}

func TestParseIntEnvEmptyString(t *testing.T) {
	_, err := parseIntEnv("")
	if err == nil {
		t.Error("parseIntEnv('') should error")
	}
}

func TestParseIntEnvFloat(t *testing.T) {
	// Sscanf with %d will parse the integer part
	n, err := parseIntEnv("42.5")
	if err != nil {
		t.Fatalf("parseIntEnv(42.5) error: %v", err)
	}
	if n != 42 {
		t.Errorf("parseIntEnv(42.5) = %d, want 42 (integer part)", n)
	}
}
