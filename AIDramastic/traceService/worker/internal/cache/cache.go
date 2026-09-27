// Package cache 写后失效查询缓存。
// 负责：按 trace_id DEL trace:{id}。
// 不负责：回填缓存。依赖：go-redis。
package cache

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"

	"aidramastic/traceService/worker/internal/config"
	wlog "aidramastic/traceService/worker/internal/log"
)

const (
	invalidateAttempts = 3
	invalidateBackoff  = 50 * time.Millisecond
)

// Invalidator 缓存失效器。
type Invalidator struct {
	rdb    *redis.Client
	prefix string
	mode   string

	// del and sleep are injectable so retry behavior can be tested without Redis
	// or waiting for the production backoff.
	del   func(context.Context, ...string) error
	sleep func(context.Context, time.Duration) error
}

// New 构造 Invalidator。
func New(rdb *redis.Client, cfg config.CacheConfig) *Invalidator {
	return &Invalidator{
		rdb:    rdb,
		prefix: cfg.Prefix,
		mode:   cfg.InvalidateMode,
		del: func(ctx context.Context, keys ...string) error {
			return rdb.Del(ctx, keys...).Err()
		},
		sleep: waitWithContext,
	}
}

// Invalidate 删除涉及的缓存键。Redis 暂时不可用时有限重试，并返回最终错误。
func (i *Invalidator) Invalidate(ctx context.Context, traceIDs []string) error {
	if len(traceIDs) == 0 {
		return nil
	}
	keys := make([]string, 0, len(traceIDs))
	for _, id := range traceIDs {
		keys = append(keys, config.CacheKey(i.prefix, id))
	}

	for attempt := 1; attempt <= invalidateAttempts; attempt++ {
		err := i.del(ctx, keys...)
		if err == nil {
			return nil
		}
		wlog.Error("cache invalidate failed", "", map[string]any{
			"err":       err.Error(),
			"attempt":   attempt,
			"attempts":  invalidateAttempts,
			"trace_ids": traceIDs,
		})
		if attempt == invalidateAttempts {
			return fmt.Errorf("cache invalidate after %d attempts: %w", invalidateAttempts, err)
		}
		if err := i.sleep(ctx, invalidateBackoff); err != nil {
			return fmt.Errorf("cache invalidate retry backoff: %w", err)
		}
	}
	return nil
}

func waitWithContext(ctx context.Context, d time.Duration) error {
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-timer.C:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}
