package config

import "testing"

func TestCacheKey(t *testing.T) {
	got := CacheKey("trace:", "abc")
	if got != "trace:abc" {
		t.Fatalf("got %s", got)
	}
}

func TestProcessingKey(t *testing.T) {
	got := ProcessingKey("trace:persist")
	if got != "trace:persist:processing" {
		t.Fatalf("got %s", got)
	}
}
