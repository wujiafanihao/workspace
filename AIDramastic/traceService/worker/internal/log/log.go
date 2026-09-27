// Package log 提供 Worker 结构化 JSON 日志。
// 负责：统一输出 timestamp/level/service/trace_id/message。
// 不负责：业务决策。依赖：encoding/json。
package log

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

const ServiceName = "trace-worker-go"

// Entry 单条结构化日志。
type Entry struct {
	Timestamp string         `json:"timestamp"`
	Level     string         `json:"level"`
	Service   string         `json:"service"`
	Message   string         `json:"message"`
	TraceID   string         `json:"trace_id,omitempty"`
	Fields    map[string]any `json:"fields,omitempty"`
}

func emit(level, msg, traceID string, fields map[string]any) {
	e := Entry{
		Timestamp: time.Now().Format(time.RFC3339),
		Level:     level,
		Service:   ServiceName,
		Message:   msg,
		TraceID:   traceID,
		Fields:    fields,
	}
	b, _ := json.Marshal(e)
	fmt.Fprintln(os.Stderr, string(b))
}

// Info 打 INFO 日志。
func Info(msg string, traceID string, fields map[string]any) { emit("INFO", msg, traceID, fields) }

// Warn 打 WARN 日志。
func Warn(msg string, traceID string, fields map[string]any) { emit("WARN", msg, traceID, fields) }

// Error 打 ERROR 日志。
func Error(msg string, traceID string, fields map[string]any) { emit("ERROR", msg, traceID, fields) }
