// Package consumer 消费 trace:persist 并批量落库。
// 负责：XREADGROUP/XAUTOCLAIM/BRPOP、批缓冲、调用 writer + cache。
// 不负责：HTTP。依赖：go-redis、writer、cache。
package consumer

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"

	"aidramastic/traceService/worker/internal/cache"
	"aidramastic/traceService/worker/internal/config"
	wlog "aidramastic/traceService/worker/internal/log"
	"aidramastic/traceService/worker/internal/writer"
)

// Runner 消费循环。
type Runner struct {
	cfg     *config.Config
	rdb     *redis.Client
	w       *writer.Writer
	inv     *cache.Invalidator
	buf     []writer.LogRow
	pending []string // stream message ids
}

// New 构造 Runner。
func New(cfg *config.Config, rdb *redis.Client, w *writer.Writer, inv *cache.Invalidator) *Runner {
	return &Runner{cfg: cfg, rdb: rdb, w: w, inv: inv, buf: make([]writer.LogRow, 0, cfg.Sqlite.BatchSize)}
}

// ensureGroup 创建消费者组。
func (r *Runner) ensureGroup(ctx context.Context) error {
	if r.cfg.Redis.QueueType != "stream" {
		return nil
	}
	err := r.rdb.XGroupCreateMkStream(ctx, r.cfg.Redis.QueueKey, r.cfg.Redis.Group, "0").Err()
	if err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
		// go-redis 用 redis.Nil 等；BUSYGROUP 字符串匹配
		if !containsBusy(err) {
			return err
		}
	}
	return nil
}

func containsBusy(err error) bool {
	return err != nil && (contains(err.Error(), "BUSYGROUP") || contains(err.Error(), "already exists"))
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (s == sub || len(sub) == 0 || indexOf(s, sub) >= 0)
}

func indexOf(s, sub string) int {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}

// flushOnShutdown 用带超时的 background context 做关机 flush，避免 cancel 立即打断落库。
// flush 失败时记 error 并返回该错误（调用方应非 0 退出）。
func (r *Runner) flushOnShutdown() error {
	flushCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := r.flush(flushCtx); err != nil {
		wlog.Error("shutdown flush failed", "", map[string]any{"err": err.Error()})
		return err
	}
	return nil
}

// Run 阻塞直到 ctx 取消；退出前 flush。flush 失败则返回 error。
func (r *Runner) Run(ctx context.Context) error {
	if err := r.ensureGroup(ctx); err != nil {
		return fmt.Errorf("ensure group: %w", err)
	}
	wlog.Info("go worker started", "", map[string]any{"queue": r.cfg.Redis.QueueKey})
	ticker := time.NewTicker(time.Duration(r.cfg.Sqlite.FlushIntervalMs) * time.Millisecond)
	defer ticker.Stop()

	depthTicker := time.NewTicker(5 * time.Second)
	defer depthTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			if err := r.flushOnShutdown(); err != nil {
				return err
			}
			wlog.Info("go worker stopping", "", nil)
			return nil
		case <-ticker.C:
			if err := r.flush(ctx); err != nil {
				wlog.Error("flush failed", "", map[string]any{"err": err.Error()})
			}
		case <-depthTicker.C:
			r.logDepth(ctx)
		default:
			if err := r.poll(ctx); err != nil {
				if ctx.Err() != nil {
					return r.flushOnShutdown()
				}
				wlog.Error("poll failed", "", map[string]any{"err": err.Error()})
				time.Sleep(200 * time.Millisecond)
			}
		}
	}
}

func (r *Runner) logDepth(ctx context.Context) {
	var n int64
	var err error
	if r.cfg.Redis.QueueType == "list" {
		n, err = r.rdb.LLen(ctx, r.cfg.Redis.QueueKey).Result()
	} else {
		n, err = r.rdb.XLen(ctx, r.cfg.Redis.QueueKey).Result()
	}
	if err != nil {
		return
	}
	if n > 100000 {
		wlog.Error("persist queue depth high", "", map[string]any{"depth": n})
	}
}

func (r *Runner) poll(ctx context.Context) error {
	if r.cfg.Redis.QueueType == "list" {
		return r.pollList(ctx)
	}
	return r.pollStream(ctx)
}

// claimCount 返回本轮 XAUTOCLAIM Count；未配置 claim_count 时用 batch_size。
func (r *Runner) claimCount() int64 {
	if r.cfg.Redis.ClaimCount > 0 {
		return int64(r.cfg.Redis.ClaimCount)
	}
	return int64(r.cfg.Sqlite.BatchSize)
}

// claimPending 用 XAUTOCLAIM 回收空闲 PEL，再按新消息同样入库缓冲。
func (r *Runner) claimPending(ctx context.Context) error {
	msgs, _, err := r.rdb.XAutoClaim(ctx, &redis.XAutoClaimArgs{
		Stream:   r.cfg.Redis.QueueKey,
		Group:    r.cfg.Redis.Group,
		Consumer: r.cfg.Redis.Consumer,
		MinIdle:  time.Duration(r.cfg.Redis.ClaimMinIdleMs) * time.Millisecond,
		Start:    "0-0",
		Count:    r.claimCount(),
	}).Result()
	if err != nil {
		return err
	}
	return r.ingestStreamMessages(ctx, msgs)
}

// appendStreamMessages 将 claim/read 得到的消息解析进 buf/pending。
// 返回无法解析、应 XACK 丢弃的 id 列表（纯逻辑，便于单测，不触 Redis）。
func (r *Runner) appendStreamMessages(msgs []redis.XMessage) (badIDs []string) {
	for _, msg := range msgs {
		payload, _ := msg.Values["payload"].(string)
		row, err := writer.ParsePayload(payload)
		if err != nil {
			badIDs = append(badIDs, msg.ID)
			continue
		}
		r.buf = append(r.buf, row)
		r.pending = append(r.pending, msg.ID)
	}
	return badIDs
}

// ingestStreamMessages 解析消息、ACK 坏包，缓冲满则 flush。
func (r *Runner) ingestStreamMessages(ctx context.Context, msgs []redis.XMessage) error {
	if len(msgs) == 0 {
		return nil
	}
	badIDs := r.appendStreamMessages(msgs)
	for _, id := range badIDs {
		// 坏消息 ACK 丢弃
		_ = r.rdb.XAck(ctx, r.cfg.Redis.QueueKey, r.cfg.Redis.Group, id).Err()
	}
	if len(r.buf) >= r.cfg.Sqlite.BatchSize {
		if err := r.flush(ctx); err != nil {
			return err
		}
	}
	return nil
}

func (r *Runner) pollStream(ctx context.Context) error {
	// 先回收崩溃后卡在 PEL 的空闲条目，再读新消息 (">")。
	if err := r.claimPending(ctx); err != nil {
		return err
	}
	res, err := r.rdb.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    r.cfg.Redis.Group,
		Consumer: r.cfg.Redis.Consumer,
		Streams:  []string{r.cfg.Redis.QueueKey, ">"},
		Count:    int64(r.cfg.Sqlite.BatchSize),
		Block:    time.Duration(r.cfg.Sqlite.FlushIntervalMs) * time.Millisecond,
	}).Result()
	if err == redis.Nil {
		return nil
	}
	if err != nil {
		return err
	}
	for _, stream := range res {
		if err := r.ingestStreamMessages(ctx, stream.Messages); err != nil {
			return err
		}
	}
	return nil
}

func (r *Runner) pollList(ctx context.Context) error {
	val, err := r.rdb.BRPop(ctx, time.Second, r.cfg.Redis.QueueKey).Result()
	if err == redis.Nil {
		return nil
	}
	if err != nil {
		return err
	}
	if len(val) < 2 {
		return nil
	}
	row, err := writer.ParsePayload(val[1])
	if err != nil {
		return nil
	}
	r.buf = append(r.buf, row)
	if len(r.buf) >= r.cfg.Sqlite.BatchSize {
		return r.flush(ctx)
	}
	return nil
}

func (r *Runner) flush(ctx context.Context) error {
	if len(r.buf) == 0 {
		return nil
	}
	ids, err := r.w.Flush(ctx, r.buf)
	if err != nil {
		return err
	}
	_ = r.inv.Invalidate(ctx, ids)
	if r.cfg.Redis.QueueType == "stream" && len(r.pending) > 0 {
		_ = r.rdb.XAck(ctx, r.cfg.Redis.QueueKey, r.cfg.Redis.Group, r.pending...).Err()
	}
	for _, id := range ids {
		wlog.Info("flushed batch", id, map[string]any{"rows": len(r.buf)})
	}
	r.buf = r.buf[:0]
	r.pending = r.pending[:0]
	return nil
}
