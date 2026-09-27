// Package main 是 Go Worker 进程入口。
// 负责：加载配置、连接 Redis/SQLite、优雅关闭。
// 不负责：HTTP API。依赖：internal/*。
package main

import (
	"context"
	"flag"
	"os"
	"os/signal"
	"syscall"

	"github.com/redis/go-redis/v9"

	"aidramastic/traceService/worker/internal/cache"
	"aidramastic/traceService/worker/internal/config"
	"aidramastic/traceService/worker/internal/consumer"
	wlog "aidramastic/traceService/worker/internal/log"
	"aidramastic/traceService/worker/internal/writer"
)

func main() {
	cfgPath := flag.String("config", "", "path to default.yaml")
	flag.Parse()

	cfg, err := config.Load(*cfgPath)
	if err != nil {
		wlog.Error("load config failed", "", map[string]any{"err": err.Error()})
		os.Exit(1)
	}

	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.Redis.Addr,
		Password: cfg.Redis.Password,
	})
	ctx := context.Background()
	if err := rdb.Ping(ctx).Err(); err != nil {
		wlog.Error("redis ping failed", "", map[string]any{"err": err.Error()})
		os.Exit(1)
	}

	w, err := writer.Open(cfg.Sqlite)
	if err != nil {
		wlog.Error("sqlite open failed", "", map[string]any{"err": err.Error()})
		os.Exit(1)
	}
	defer w.Close()

	inv := cache.New(rdb, cfg.Cache)
	runner := consumer.New(cfg, rdb, w, inv)

	runCtx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		wlog.Info("signal received", "", nil)
		cancel()
	}()

	if err := runner.Run(runCtx); err != nil {
		wlog.Error("runner exited", "", map[string]any{"err": err.Error()})
		os.Exit(1)
	}
}
