// Package cache 写后失效查询缓存。
// 负责：按 trace_id DEL trace:{id}。
// 不负责：回填缓存。依赖：go-redis。
package cache

import (
	"context"

	"github.com/redis/go-redis/v9"

	"aidramastic/traceService/worker/internal/config"
	wlog "aidramastic/traceService/worker/internal/log"
)

// Invalidator 缓存失效器。
type Invalidator struct {
	rdb    *redis.Client
	prefix string
	mode   string
}

// New 构造 Invalidator。
func New(rdb *redis.Client, cfg config.CacheConfig) *Invalidator {
	return &Invalidator{rdb: rdb, prefix: cfg.Prefix, mode: cfg.InvalidateMode}
}

// Invalidate 删除涉及的缓存键。
func (i *Invalidator) Invalidate(ctx context.Context, traceIDs []string) error {
	if len(traceIDs) == 0 {
		return nil
	}
	keys := make([]string, 0, len(traceIDs))
	for _, id := range traceIDs {
		keys = append(keys, config.CacheKey(i.prefix, id))
	}
	if err := i.rdb.Del(ctx, keys...).Err(); err != nil {
		wlog.Warn("cache invalidate failed", "", map[string]any{"err": err.Error()})
		return err
	}
	return nil
}
