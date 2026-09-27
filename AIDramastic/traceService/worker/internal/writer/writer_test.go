package writer

import "testing"

func TestBuildInsertSQL(t *testing.T) {
	sql, err := BuildInsertSQL(2)
	if err != nil {
		t.Fatal(err)
	}
	want := "INSERT INTO logs (trace_id, span_id, service, level, message, timestamp, fields_json) VALUES (?,?,?,?,?,?,?),(?,?,?,?,?,?,?)"
	if sql != want {
		t.Fatalf("got %s", sql)
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
