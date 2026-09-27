package consumer

import (
	"context"
	"errors"
	"path/filepath"
	"testing"

	"github.com/redis/go-redis/v9"

	"aidramastic/traceService/worker/internal/config"
	"aidramastic/traceService/worker/internal/writer"
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
	if r.buf[0].TraceID != "t1" || r.buf[0].RedisMsgID != "1-0" {
		t.Fatalf("row=%+v", r.buf[0])
	}
	if r.buf[1].RedisMsgID != "3-0" {
		t.Fatalf("row1=%+v", r.buf[1])
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

func TestFlushOnShutdownEmptyOK(t *testing.T) {
	r := &Runner{cfg: &config.Config{}}
	if err := r.flushOnShutdown(); err != nil {
		t.Fatalf("empty buf: %v", err)
	}
}

func TestFlushOnShutdownReturnsFlushError(t *testing.T) {
	dir := t.TempDir()
	w, err := writer.Open(config.SqliteConfig{
		Path:          filepath.Join(dir, "t.db"),
		BusyTimeoutMs: 1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	_ = w.Close()

	r := &Runner{
		cfg: &config.Config{Redis: config.RedisConfig{QueueType: "list"}},
		w:   w,
		buf: []writer.LogRow{{
			TraceID: "t1", Service: "s", Level: "INFO", Message: "m", Timestamp: "ts",
		}},
	}
	if err := r.flushOnShutdown(); err == nil {
		t.Fatal("expected flush error after closed writer")
	}
}

func TestFlushKeepsPendingOnAckFailure(t *testing.T) {
	dir := t.TempDir()
	w, err := writer.Open(config.SqliteConfig{
		Path:          filepath.Join(dir, "t.db"),
		BusyTimeoutMs: 1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer w.Close()

	ackCalls := 0
	r := &Runner{
		cfg: &config.Config{Redis: config.RedisConfig{QueueType: "stream", QueueKey: "q", Group: "g"}},
		w:   w,
		buf: []writer.LogRow{{
			TraceID: "t1", Service: "s", Level: "INFO", Message: "m", Timestamp: "ts",
			RedisMsgID: "1-0",
		}},
		pending: []string{"1-0"},
		xAck: func(ctx context.Context, ids ...string) error {
			ackCalls++
			return errors.New("redis down")
		},
	}
	if err := r.flush(context.Background()); err == nil {
		t.Fatal("expected xack error")
	}
	if len(r.buf) != 1 || len(r.pending) != 1 || r.pending[0] != "1-0" {
		t.Fatalf("should keep buf/pending: buf=%d pending=%v", len(r.buf), r.pending)
	}
	if ackCalls != 1 {
		t.Fatalf("ackCalls=%d", ackCalls)
	}

	// idempotent retry then successful ack clears
	r.xAck = func(ctx context.Context, ids ...string) error {
		ackCalls++
		return nil
	}
	if err := r.flush(context.Background()); err != nil {
		t.Fatal(err)
	}
	if len(r.buf) != 0 || len(r.pending) != 0 {
		t.Fatalf("should clear after ack ok: buf=%d pending=%v", len(r.buf), r.pending)
	}
	if ackCalls != 2 {
		t.Fatalf("ackCalls=%d", ackCalls)
	}
}

func TestFlushClearsPendingOnAckSuccess(t *testing.T) {
	dir := t.TempDir()
	w, err := writer.Open(config.SqliteConfig{
		Path:          filepath.Join(dir, "t.db"),
		BusyTimeoutMs: 1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer w.Close()

	r := &Runner{
		cfg: &config.Config{Redis: config.RedisConfig{QueueType: "stream"}},
		w:   w,
		buf: []writer.LogRow{{
			TraceID: "t1", Service: "s", Level: "INFO", Message: "m", Timestamp: "ts",
			RedisMsgID: "9-0",
		}},
		pending: []string{"9-0"},
		xAck: func(ctx context.Context, ids ...string) error {
			if len(ids) != 1 || ids[0] != "9-0" {
				t.Fatalf("ids=%v", ids)
			}
			return nil
		},
	}
	if err := r.flush(context.Background()); err != nil {
		t.Fatal(err)
	}
	if len(r.buf) != 0 || len(r.pending) != 0 {
		t.Fatalf("buf=%d pending=%v", len(r.buf), r.pending)
	}
}

func TestFlushLRemOnListSuccess(t *testing.T) {
	dir := t.TempDir()
	w, err := writer.Open(config.SqliteConfig{
		Path:          filepath.Join(dir, "t.db"),
		BusyTimeoutMs: 1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer w.Close()

	payload := `{"trace_id":"t1","service":"s","level":"INFO","message":"m","timestamp":"ts"}`
	var gotKey string
	var gotCount int64
	var gotVal string
	calls := 0
	r := &Runner{
		cfg: &config.Config{Redis: config.RedisConfig{QueueType: "list", QueueKey: "trace:persist"}},
		w:   w,
		buf: []writer.LogRow{{
			TraceID: "t1", Service: "s", Level: "INFO", Message: "m", Timestamp: "ts",
		}},
		pending: []string{payload},
		lRem: func(ctx context.Context, key string, count int64, value string) error {
			calls++
			gotKey, gotCount, gotVal = key, count, value
			return nil
		},
	}
	if err := r.flush(context.Background()); err != nil {
		t.Fatal(err)
	}
	if calls != 1 || gotKey != "trace:persist:processing" || gotCount != 1 || gotVal != payload {
		t.Fatalf("lrem calls=%d key=%s count=%d val=%q", calls, gotKey, gotCount, gotVal)
	}
	if len(r.buf) != 0 || len(r.pending) != 0 {
		t.Fatalf("buf=%d pending=%v", len(r.buf), r.pending)
	}
}

func TestFlushKeepsPendingOnListLRemFailure(t *testing.T) {
	dir := t.TempDir()
	w, err := writer.Open(config.SqliteConfig{
		Path:          filepath.Join(dir, "t.db"),
		BusyTimeoutMs: 1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer w.Close()

	payload := `{"trace_id":"t1","service":"s","level":"INFO","message":"m","timestamp":"ts"}`
	r := &Runner{
		cfg: &config.Config{Redis: config.RedisConfig{QueueType: "list", QueueKey: "q"}},
		w:   w,
		buf: []writer.LogRow{{
			TraceID: "t1", Service: "s", Level: "INFO", Message: "m", Timestamp: "ts",
		}},
		pending: []string{payload},
		lRem: func(ctx context.Context, key string, count int64, value string) error {
			return errors.New("redis down")
		},
	}
	if err := r.flush(context.Background()); err == nil {
		t.Fatal("expected lrem error")
	}
	if len(r.buf) != 1 || len(r.pending) != 1 || r.pending[0] != payload {
		t.Fatalf("should keep buf/pending: buf=%d pending=%v", len(r.buf), r.pending)
	}
}
