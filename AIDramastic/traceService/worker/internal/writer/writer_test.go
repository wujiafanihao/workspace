package writer

import (
	"context"
	"path/filepath"
	"testing"

	"aidramastic/traceService/worker/internal/config"
)

func TestBuildInsertSQL(t *testing.T) {
	sqlStr, err := BuildInsertSQL(2)
	if err != nil {
		t.Fatal(err)
	}
	want := "INSERT INTO logs (trace_id, span_id, service, level, message, timestamp, fields_json, redis_msg_id) VALUES (?,?,?,?,?,?,?,?),(?,?,?,?,?,?,?,?) ON CONFLICT(redis_msg_id) DO NOTHING"
	if sqlStr != want {
		t.Fatalf("got %s", sqlStr)
	}
}

func TestBuildInsertSQLInvalid(t *testing.T) {
	if _, err := BuildInsertSQL(0); err == nil {
		t.Fatal("expected error")
	}
}

func TestNormalizeLevel(t *testing.T) {
	if NormalizeLevel("info") != "INFO" {
		t.Fatal("upper")
	}
}

func TestParsePayloadMsgAlias(t *testing.T) {
	raw := `{"trace_id":"t","service":"s","level":"warn","msg":"hi","timestamp":"ts"}`
	row, err := ParsePayload(raw)
	if err != nil {
		t.Fatal(err)
	}
	if row.Message != "hi" || row.Level != "WARN" {
		t.Fatalf("%+v", row)
	}
}

func TestFlushIdempotentByRedisMsgID(t *testing.T) {
	dir := t.TempDir()
	w, err := Open(config.SqliteConfig{
		Path:          filepath.Join(dir, "t.db"),
		BusyTimeoutMs: 1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer w.Close()

	rows := []LogRow{{
		TraceID: "t1", Service: "s", Level: "INFO", Message: "m", Timestamp: "ts",
		RedisMsgID: "1-0",
	}}
	ctx := context.Background()
	if _, err := w.Flush(ctx, rows); err != nil {
		t.Fatal(err)
	}
	if _, err := w.Flush(ctx, rows); err != nil {
		t.Fatal(err)
	}
	var n int
	if err := w.db.QueryRow(`SELECT COUNT(*) FROM logs WHERE redis_msg_id = ?`, "1-0").Scan(&n); err != nil {
		t.Fatal(err)
	}
	if n != 1 {
		t.Fatalf("want 1 row after idempotent flush, got %d", n)
	}
}

func TestFlushListModeAllowsMultipleNullMsgID(t *testing.T) {
	dir := t.TempDir()
	w, err := Open(config.SqliteConfig{
		Path:          filepath.Join(dir, "t.db"),
		BusyTimeoutMs: 1000,
	})
	if err != nil {
		t.Fatal(err)
	}
	defer w.Close()

	ctx := context.Background()
	row := LogRow{TraceID: "t1", Service: "s", Level: "INFO", Message: "m", Timestamp: "ts"}
	if _, err := w.Flush(ctx, []LogRow{row, row}); err != nil {
		t.Fatal(err)
	}
	var n int
	if err := w.db.QueryRow(`SELECT COUNT(*) FROM logs`).Scan(&n); err != nil {
		t.Fatal(err)
	}
	if n != 2 {
		t.Fatalf("want 2 rows with NULL redis_msg_id, got %d", n)
	}
}
