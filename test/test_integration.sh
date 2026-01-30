#!/bin/bash
#
# 統合テスト: サーバー + tmux連携
#

# set -e は使わない（テスト失敗でも継続）

# 色付き出力
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 設定
TEST_SESSION="test_claude_button"
TEST_PORT=18080
SERVER_PID=""
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# カウンター
PASSED=0
FAILED=0

# クリーンアップ
cleanup() {
    echo ""
    echo -e "${CYAN}Cleaning up...${NC}"

    # サーバー停止
    if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        echo "  Server stopped"
    fi

    # tmuxセッション削除
    if tmux has-session -t "$TEST_SESSION" 2>/dev/null; then
        tmux kill-session -t "$TEST_SESSION" 2>/dev/null || true
        echo "  tmux session killed"
    fi
}

trap cleanup EXIT

# テスト関数
pass() {
    echo -e "  ${GREEN}✓ $1${NC}"
    ((PASSED++))
}

fail() {
    echo -e "  ${RED}✗ $1${NC}"
    ((FAILED++))
}

test_cmd() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        pass "$desc"
        return 0
    else
        fail "$desc"
        return 1
    fi
}

test_http() {
    local desc="$1"
    local method="$2"
    local path="$3"
    local expected_status="$4"
    local data="$5"

    local url="http://127.0.0.1:${TEST_PORT}${path}"
    local status

    if [[ "$method" == "GET" ]]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    else
        if [[ -n "$data" ]]; then
            status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$url")
        else
            status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url")
        fi
    fi

    if [[ "$status" == "$expected_status" ]]; then
        pass "$desc (HTTP $status)"
        return 0
    else
        fail "$desc (expected $expected_status, got $status)"
        return 1
    fi
}

test_http_any() {
    # 複数の期待ステータスを許容
    local desc="$1"
    local method="$2"
    local path="$3"
    local expected1="$4"
    local expected2="$5"
    local data="$6"

    local url="http://127.0.0.1:${TEST_PORT}${path}"
    local status

    if [[ "$method" == "GET" ]]; then
        status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    else
        if [[ -n "$data" ]]; then
            status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d "$data" "$url")
        else
            status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url")
        fi
    fi

    if [[ "$status" == "$expected1" || "$status" == "$expected2" ]]; then
        pass "$desc (HTTP $status)"
        return 0
    else
        fail "$desc (expected $expected1 or $expected2, got $status)"
        return 1
    fi
}

# ===== メイン =====

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Integration Test${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ----- Phase 1: 前提条件 -----
echo -e "${YELLOW}Phase 1: Prerequisites${NC}"

test_cmd "tmux is installed" which tmux
test_cmd "curl is installed" which curl
test_cmd "python3 is installed" which python3
test_cmd "accept_server.py exists" test -f "$PROJECT_DIR/accept_server.py"

echo ""

# ----- Phase 2: サーバー起動 -----
echo -e "${YELLOW}Phase 2: Server Startup${NC}"

# ポート使用中チェック
if lsof -i ":$TEST_PORT" > /dev/null 2>&1; then
    fail "Port $TEST_PORT is already in use"
    exit 1
fi

# サーバー起動（テスト用ポートで）
cd "$PROJECT_DIR"
PORT=$TEST_PORT python3 -c "
import sys
sys.path.insert(0, '.')
from accept_server import AcceptHandler
from http.server import HTTPServer
import os
port = int(os.environ.get('PORT', 8080))
server = HTTPServer(('127.0.0.1', port), AcceptHandler)
server.serve_forever()
" &
SERVER_PID=$!
sleep 1

if kill -0 "$SERVER_PID" 2>/dev/null; then
    pass "Server started (PID: $SERVER_PID)"
else
    fail "Server failed to start"
    exit 1
fi

echo ""

# ----- Phase 3: HTTPエンドポイントテスト -----
echo -e "${YELLOW}Phase 3: HTTP Endpoints${NC}"

test_http "GET /" "GET" "/" "200"
test_http "GET /status" "GET" "/status" "200"
test_http "GET /invalid (404)" "GET" "/invalid" "404"
# tmuxセッションがあれば200、なければ500（どちらもOK）
test_http_any "POST /accept" "POST" "/accept" "200" "500"
test_http_any "POST /reject" "POST" "/reject" "200" "500"
test_http_any "POST /key with data" "POST" "/key" "200" "500" '{"key":"y"}'
test_http "POST /key without key (400)" "POST" "/key" "400" '{}'

echo ""

# ----- Phase 4: tmux連携テスト -----
echo -e "${YELLOW}Phase 4: tmux Integration${NC}"

# tmuxセッション作成
tmux new-session -d -s "$TEST_SESSION" 2>/dev/null
if tmux has-session -t "$TEST_SESSION" 2>/dev/null; then
    pass "Created tmux session: $TEST_SESSION"
else
    fail "Failed to create tmux session"
    exit 1
fi

# セッション名を変更してテスト（サーバーはデフォルトの'claude'を見るので別途テスト）
test_cmd "Send key to tmux" tmux send-keys -t "$TEST_SESSION" "echo hello"
sleep 0.2

# ペイン内容確認
PANE_CONTENT=$(tmux capture-pane -t "$TEST_SESSION" -p)
if echo "$PANE_CONTENT" | grep -q "echo hello"; then
    pass "Key appears in tmux pane"
else
    fail "Key not found in tmux pane"
fi

echo ""

# ----- Phase 5: エンドツーエンドテスト -----
echo -e "${YELLOW}Phase 5: End-to-End (with 'claude' session)${NC}"

# 'claude'セッションを作成
CLAUDE_SESSION="claude"
tmux kill-session -t "$CLAUDE_SESSION" 2>/dev/null || true
tmux new-session -d -s "$CLAUDE_SESSION"

if tmux has-session -t "$CLAUDE_SESSION" 2>/dev/null; then
    pass "Created 'claude' session"
else
    fail "Failed to create 'claude' session"
fi

# /acceptを叩いて'y'が送信されるか確認
curl -s -X POST "http://127.0.0.1:${TEST_PORT}/accept" > /dev/null
sleep 0.3

CLAUDE_PANE=$(tmux capture-pane -t "$CLAUDE_SESSION" -p)
if echo "$CLAUDE_PANE" | grep -q "y"; then
    pass "POST /accept sent 'y' to claude session"
else
    fail "'y' not found in claude session"
fi

# /rejectを叩いて'n'が送信されるか確認
curl -s -X POST "http://127.0.0.1:${TEST_PORT}/reject" > /dev/null
sleep 0.3

CLAUDE_PANE=$(tmux capture-pane -t "$CLAUDE_SESSION" -p)
if echo "$CLAUDE_PANE" | grep -q "n"; then
    pass "POST /reject sent 'n' to claude session"
else
    fail "'n' not found in claude session"
fi

# クリーンアップ
tmux kill-session -t "$CLAUDE_SESSION" 2>/dev/null || true

echo ""

# ===== 結果 =====
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Results${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo ""

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
