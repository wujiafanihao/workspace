// Package writer 批量写入 SQLite（WAL）。
// 负责：建表、事务批量 INSERT。
// 不负责：消费 Redis；缓存失效。依赖：database/sql + modernc.org/sqlite。
package writer

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	_ "modernc.org/sqlite"

	"aidramastic/traceService/worker/internal/config"
)

// LogRow 待写入行。
type LogRow struct {
	TraceID    string
	SpanID     string
	Service    string
	Level      string
	Message    string
	Timestamp  string
	Fields     map[string]any
	RedisMsgID string // stream message id；list 模式为空
}

const ddl = `
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS logs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id      TEXT    NOT NULL,
  span_id       TEXT,
  service       TEXT    NOT NULL,
  level         TEXT    NOT NULL,
  message       TEXT    NOT NULL,
  timestamp     TEXT    NOT NULL,
  fields_json   TEXT,
  redis_msg_id  TEXT,
  created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_logs_trace_ts ON logs(trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_logs_redis_msg_id ON logs(redis_msg_id);
`

// Writer SQLite 批量写者。
type Writer struct {
	db  *sql.DB
	cfg config.SqliteConfig
}

// Open 打开数据库并 ensure schema。
func Open(cfg config.SqliteConfig) (*Writer, error) {
	if err := os.MkdirAll(filepath.Dir(cfg.Path), 0o755); err != nil {
		return nil, fmt.Errorf("mkdir: %w", err)
	}
	dsn := fmt.Sprintf("file:%s?_pragma=busy_timeout(%d)", cfg.Path, cfg.BusyTimeoutMs)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open sqlite: %w", err)
	}
	db.SetMaxOpenConns(1)
	if err := ensureSchema(db); err != nil {
		_ = db.Close()
		return nil, err
	}
	return &Writer{db: db, cfg: cfg}, nil
}

// ensureSchema 建表并迁移补列。
func ensureSchema(db *sql.DB) error {
	if _, err := db.Exec(ddl); err != nil {
		return fmt.Errorf("ddl: %w", err)
	}
	// 旧库缺列时 ADD COLUMN；已存在则忽略错误。
	_, _ = db.Exec(`ALTER TABLE logs ADD COLUMN redis_msg_id TEXT`)
	// 完整 UNIQUE（非 partial）以便 ON CONFLICT(redis_msg_id)；SQLite UNIQUE 允许多个 NULL（list 模式）。
	if _, err := db.Exec(`CREATE UNIQUE INDEX IF NOT EXISTS idx_logs_redis_msg_id ON logs(redis_msg_id)`); err != nil {
		return fmt.Errorf("migrate index: %w", err)
	}
	return nil
}

// Close 关闭 DB。
func (w *Writer) Close() error {
	if w.db == nil {
		return nil
	}
	return w.db.Close()
}

// BuildInsertSQL 返回批量 INSERT 语句（纯函数，便于单测）。
// n 为行数；每行 8 个占位符；ON CONFLICT(redis_msg_id) DO NOTHING 保证 stream 幂等。
func BuildInsertSQL(n int) (string, error) {
	if n <= 0 {
		return "", fmt.Errorf("n must be > 0")
	}
	var b strings.Builder
	b.WriteString("INSERT INTO logs (trace_id, span_id, service, level, message, timestamp, fields_json, redis_msg_id) VALUES ")
	for i := 0; i < n; i++ {
		if i > 0 {
			b.WriteByte(',')
		}
		b.WriteString("(?,?,?,?,?,?,?,?)")
	}
	b.WriteString(" ON CONFLICT(redis_msg_id) DO NOTHING")
	return b.String(), nil
}

// Flush 事务批量插入；返回涉及的 trace_id 集合。
func (w *Writer) Flush(ctx context.Context, rows []LogRow) ([]string, error) {
	if len(rows) == 0 {
		return nil, nil
	}
	sqlStr, err := BuildInsertSQL(len(rows))
	if err != nil {
		return nil, err
	}
	args := make([]any, 0, len(rows)*8)
	seen := map[string]struct{}{}
	ids := make([]string, 0)
	for _, r := range rows {
		fj, _ := json.Marshal(r.Fields)
		if r.Fields == nil {
			fj = []byte("{}")
		}
		args = append(args, r.TraceID, nullStr(r.SpanID), r.Service, r.Level, r.Message, r.Timestamp, string(fj), nullStr(r.RedisMsgID))
		if _, ok := seen[r.TraceID]; !ok {
			seen[r.TraceID] = struct{}{}
			ids = append(ids, r.TraceID)
		}
	}
	tx, err := w.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	if _, err := tx.ExecContext(ctx, sqlStr, args...); err != nil {
		_ = tx.Rollback()
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return ids, nil
}

func nullStr(s string) any {
	if s == "" {
		return nil
	}
	return s
}

// NormalizeLevel 将 level 转为大写（纯辅助）。
func NormalizeLevel(level string) string {
	return strings.ToUpper(strings.TrimSpace(level))
}

// ParsePayload 从 JSON payload 解析 LogRow。
func ParsePayload(raw string) (LogRow, error) {
	var m map[string]any
	if err := json.Unmarshal([]byte(raw), &m); err != nil {
		return LogRow{}, err
	}
	msg, _ := m["message"].(string)
	if msg == "" {
		if v, ok := m["msg"].(string); ok {
			msg = v
		}
	}
	level, _ := m["level"].(string)
	tid, _ := m["trace_id"].(string)
	svc, _ := m["service"].(string)
	ts, _ := m["timestamp"].(string)
	span, _ := m["span_id"].(string)
	fields, _ := m["fields"].(map[string]any)
	if fields == nil {
		fields = map[string]any{}
	}
	if tid == "" || svc == "" || level == "" || msg == "" || ts == "" {
		return LogRow{}, fmt.Errorf("missing required fields")
	}
	return LogRow{
		TraceID:   tid,
		SpanID:    span,
		Service:   svc,
		Level:     NormalizeLevel(level),
		Message:   msg,
		Timestamp: ts,
		Fields:    fields,
	}, nil
}
