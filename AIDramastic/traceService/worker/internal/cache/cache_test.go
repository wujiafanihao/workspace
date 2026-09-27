package cache

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestInvalidateRetriesUntilSuccess(t *testing.T) {
	wantErr := errors.New("redis unavailable")
	calls := 0
	var gotKeys []string
	i := &Invalidator{
		prefix: "trace:",
		del: func(ctx context.Context, keys ...string) error {
			calls++
			gotKeys = append([]string(nil), keys...)
			if calls < 3 {
				return wantErr
			}
			return nil
		},
		sleep: func(context.Context, time.Duration) error { return nil },
	}

	if err := i.Invalidate(context.Background(), []string{"t1", "t2"}); err != nil {
		t.Fatalf("Invalidate() error = %v", err)
	}
	if calls != 3 {
		t.Fatalf("DEL calls = %d, want 3", calls)
	}
	if len(gotKeys) != 2 || gotKeys[0] != "trace:t1" || gotKeys[1] != "trace:t2" {
		t.Fatalf("keys = %v", gotKeys)
	}
}

func TestInvalidateReturnsFinalErrorAfterRetries(t *testing.T) {
	wantErr := errors.New("redis unavailable")
	calls := 0
	i := &Invalidator{
		prefix: "trace:",
		del: func(context.Context, ...string) error {
			calls++
			return wantErr
		},
		sleep: func(context.Context, time.Duration) error { return nil },
	}

	err := i.Invalidate(context.Background(), []string{"t1"})
	if !errors.Is(err, wantErr) {
		t.Fatalf("Invalidate() error = %v, want wrapped final error", err)
	}
	if calls != invalidateAttempts {
		t.Fatalf("DEL calls = %d, want %d", calls, invalidateAttempts)
	}
}
