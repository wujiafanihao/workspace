// Package config 加载 Go Worker YAML 配置。
// 负责：解析 redis/sqlite/cache；从 env 读 Redis 地址。
// 不负责：热更。依赖：gopkg.in/yaml.v3。
package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// Config 根配置。
type Config struct {
	Redis  RedisConfig  `yaml:"redis"`
	Sqlite SqliteConfig `yaml:"sqlite"`
	Cache  CacheConfig  `yaml:"cache"`
}

// RedisConfig Redis 与消费者组。
type RedisConfig struct {
	AddrEnv        string `yaml:"addr_env"`
	QueueKey       string `yaml:"queue_key"`
	QueueType      string `yaml:"queue_type"`
	Group          string `yaml:"group"`
	Consumer       string `yaml:"consumer"`
	ClaimMinIdleMs int    `yaml:"claim_min_idle_ms"` // PEL 最小空闲毫秒，XAUTOCLAIM MinIdle
	ClaimCount     int    `yaml:"claim_count"`       // 每次 claim 条数；<=0 则用 batch_size
	Addr           string `yaml:"-"`
	Password       string `yaml:"-"`
}

// SqliteConfig 本地库路径与批量参数。
type SqliteConfig struct {
	Path            string `yaml:"path"`
	BusyTimeoutMs   int    `yaml:"busy_timeout_ms"`
	BatchSize       int    `yaml:"batch_size"`
	FlushIntervalMs int    `yaml:"flush_interval_ms"`
}

// CacheConfig 写后缓存失效策略。
type CacheConfig struct {
	Prefix         string `yaml:"prefix"`
	InvalidateMode string `yaml:"invalidate_mode"`
}

// Load 从 path 加载配置；空则用 configs/default.yaml。
func Load(path string) (*Config, error) {
	if path == "" {
		wd, _ := os.Getwd()
		path = filepath.Join(wd, "configs", "default.yaml")
	}
	absPath, err := filepath.Abs(path)
	if err != nil {
		return nil, fmt.Errorf("abs config: %w", err)
	}
	b, err := os.ReadFile(absPath)
	if err != nil {
		return nil, fmt.Errorf("read config: %w", err)
	}
	var cfg Config
	if err := yaml.Unmarshal(b, &cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}
	addrEnv := cfg.Redis.AddrEnv
	if addrEnv == "" {
		addrEnv = "REDIS_ADDR"
	}
	cfg.Redis.Addr = os.Getenv(addrEnv)
	if cfg.Redis.Addr == "" {
		cfg.Redis.Addr = "127.0.0.1:6379"
	}
	cfg.Redis.Password = os.Getenv("REDIS_PASSWORD")
	if cfg.Redis.QueueKey == "" {
		cfg.Redis.QueueKey = "trace:persist"
	}
	if cfg.Redis.QueueType == "" {
		cfg.Redis.QueueType = "stream"
	}
	if cfg.Redis.Group == "" {
		cfg.Redis.Group = "trace-persist-workers"
	}
	if cfg.Redis.Consumer == "" {
		cfg.Redis.Consumer = "go-worker-1"
	}
	if cfg.Redis.ClaimMinIdleMs <= 0 {
		cfg.Redis.ClaimMinIdleMs = 60000
	}
	// ClaimCount <= 0：运行时回退到 sqlite.batch_size
	if cfg.Sqlite.Path == "" {
		cfg.Sqlite.Path = "../backend/data/logs.db"
	}
	if !filepath.IsAbs(cfg.Sqlite.Path) {
		// 相对 worker 模块根（configs/ 的父目录）
		workerRoot := filepath.Dir(filepath.Dir(absPath))
		cfg.Sqlite.Path = filepath.Clean(filepath.Join(workerRoot, cfg.Sqlite.Path))
	}
	if cfg.Sqlite.BusyTimeoutMs <= 0 {
		cfg.Sqlite.BusyTimeoutMs = 5000
	}
	if cfg.Sqlite.BatchSize <= 0 {
		cfg.Sqlite.BatchSize = 100
	}
	if cfg.Sqlite.FlushIntervalMs <= 0 {
		cfg.Sqlite.FlushIntervalMs = 100
	}
	if cfg.Cache.Prefix == "" {
		cfg.Cache.Prefix = "trace:"
	}
	if cfg.Cache.InvalidateMode == "" {
		cfg.Cache.InvalidateMode = "delete"
	}
	return &cfg, nil
}

// CacheKey 构造 trace:{id}。
func CacheKey(prefix, traceID string) string {
	return prefix + traceID
}

// ProcessingKey 返回可靠 list 队列的 processing 侧键：queueKey + ":processing"。
func ProcessingKey(queueKey string) string {
	return queueKey + ":processing"
}
