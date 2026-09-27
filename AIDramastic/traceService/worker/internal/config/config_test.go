package config

import (
	"os"
	"path/filepath"
	"testing"
)

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

func TestLoadHonorsTraceSQLitePath(t *testing.T) {
	configPath := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(configPath, []byte("sqlite:\n  path: yaml.db\n"), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	if err := os.Setenv("TRACE_SQLITE_PATH", "trace.db"); err != nil {
		t.Fatalf("set TRACE_SQLITE_PATH: %v", err)
	}
	t.Cleanup(func() {
		if err := os.Unsetenv("TRACE_SQLITE_PATH"); err != nil {
			t.Errorf("unset TRACE_SQLITE_PATH: %v", err)
		}
	})

	cfg, err := Load(configPath)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	expected, err := filepath.Abs("trace.db")
	if err != nil {
		t.Fatalf("resolve expected path: %v", err)
	}
	if cfg.Sqlite.Path != expected {
		t.Fatalf("sqlite path = %q, want %q", cfg.Sqlite.Path, expected)
	}
}
