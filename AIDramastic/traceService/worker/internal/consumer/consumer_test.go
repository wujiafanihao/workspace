package consumer

import (
	"testing"

	"github.com/redis/go-redis/v9"

	"aidramastic/traceService/worker/internal/config"
)

func TestAppendStreamMessages(t *testing.T) {
	r := &Runner{
		cfg: &config.Config{Sqlite: config.SqliteConfig{BatchSize: 100}},
	}
	good := `{"trace_id":"t1","service":"s","level":"info","message":"ok","timestamp":"ts"}`
	msgs := []redis.XMessage{
		{ID: "1-0", Values: map[string]interface{}{"payload": good}},
		{ID: "2-0", Values: map[string]interface{}{"payload": "not-json"}},
		{ID: "3-0", Values: map[string]interface{}{"payload": good}},
	}
	bad := r.appendStreamMessages(msgs)
	if len(bad) != 1 || bad[0] != "2-0" {
		t.Fatalf("badIDs=%v", bad)
	}
	if len(r.buf) != 2 || len(r.pending) != 2 {
		t.Fatalf("buf=%d pending=%d", len(r.buf), len(r.pending))
	}
	if r.pending[0] != "1-0" || r.pending[1] != "3-0" {
		t.Fatalf("pending=%v", r.pending)
	}
	if r.buf[0].TraceID != "t1" {
		t.Fatalf("row=%+v", r.buf[0])
	}
}

func TestClaimCountDefaultsToBatchSize(t *testing.T) {
	r := &Runner{cfg: &config.Config{
		Redis:  config.RedisConfig{},
		Sqlite: config.SqliteConfig{BatchSize: 42},
	}}
	if r.claimCount() != 42 {
		t.Fatalf("got %d", r.claimCount())
	}
	r.cfg.Redis.ClaimCount = 7
	if r.claimCount() != 7 {
		t.Fatalf("got %d", r.claimCount())
	}
}
