package config

import "testing"

func TestCacheKey(t *testing.T) {
	got := CacheKey("trace:", "abc")
	if got != "trace:abc" {
		t.Fatalf("got %s", got)
	}
}
