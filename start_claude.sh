#!/bin/bash
#
# Claude Code を tmux セッションで起動するスクリプト
#

SESSION_NAME="claude"
WORKING_DIR="${1:-.}"  # 引数でディレクトリ指定可能、デフォルトはカレント

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Claude Code Tmux Launcher ===${NC}"

# tmuxがインストールされているか確認
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}Error: tmux is not installed${NC}"
    echo "Install with: brew install tmux"
    exit 1
fi

# 既存セッションの確認
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo -e "${YELLOW}Session '$SESSION_NAME' already exists${NC}"
    echo ""
    echo "Options:"
    echo "  1. Attach to existing session:  tmux attach -t $SESSION_NAME"
    echo "  2. Kill and recreate:           tmux kill-session -t $SESSION_NAME && $0"
    echo ""
    read -p "Attach to existing session? (y/n): " choice
    if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
        tmux attach -t "$SESSION_NAME"
    fi
    exit 0
fi

# 作業ディレクトリの確認
if [[ ! -d "$WORKING_DIR" ]]; then
    echo -e "${RED}Error: Directory '$WORKING_DIR' does not exist${NC}"
    exit 1
fi

WORKING_DIR=$(cd "$WORKING_DIR" && pwd)  # 絶対パスに変換

echo "Working directory: $WORKING_DIR"
echo "Session name: $SESSION_NAME"
echo ""

# tmuxセッション作成
echo -e "${GREEN}Creating tmux session...${NC}"
tmux new-session -d -s "$SESSION_NAME" -c "$WORKING_DIR"

# Claude Code起動
echo -e "${GREEN}Starting Claude Code...${NC}"
tmux send-keys -t "$SESSION_NAME" 'claude' Enter

echo ""
echo -e "${GREEN}Done!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Session: $SESSION_NAME"
echo "  Directory: $WORKING_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Commands:"
echo "  Attach:  tmux attach -t $SESSION_NAME"
echo "  Detach:  Ctrl+B, then D"
echo "  Kill:    tmux kill-session -t $SESSION_NAME"
echo ""
echo "Test accept:"
echo "  curl -X POST http://localhost:8080/accept"
echo ""

# 自動でアタッチするか確認
read -p "Attach to session now? (y/n): " attach
if [[ "$attach" == "y" || "$attach" == "Y" ]]; then
    tmux attach -t "$SESSION_NAME"
fi
