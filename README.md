# Claude Code 物理ボタン (Physical Accept Button)

M5 Atom S3 を使って Claude Code の確認プロンプトに物理ボタンで応答するシステム。

```
[M5 Atom S3] --HTTP POST--> [Python Server] --tmux send-keys--> [Claude Code]
```

## 構成ファイル

```
.
├── platformio.ini          # PlatformIO設定
├── src/
│   └── main.cpp            # M5 Atom S3用コード
├── include/
│   └── credentials.h.example  # 認証情報テンプレート
├── accept_server.py        # HTTPサーバー（macOS側）
├── start_claude.sh         # tmux起動スクリプト
├── test/
│   ├── test_server.py      # サーバーテスト
│   └── test_integration.sh # 統合テスト
└── README.md
```

## セットアップ

### 1. macOS側の準備

```bash
# tmuxをインストール（未インストールの場合）
brew install tmux

# Claude Codeをtmuxで起動
./start_claude.sh /path/to/your/project

# 別ターミナルでHTTPサーバーを起動
python3 accept_server.py
```

### 2. M5 Atom S3の準備（PlatformIO）

1. 認証情報ファイルを作成:

   ```bash
   cp include/credentials.h.example include/credentials.h
   ```

2. `include/credentials.h` を編集:

   ```cpp
   #define WIFI_SSID "YOUR_WIFI_SSID"          // WiFi SSID
   #define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"   // WiFi パスワード
   #define SERVER_HOST "192.168.1.100"          // macOSのIPアドレス
   #define SERVER_PORT 8080                     // サーバーポート
   ```

3. ビルド＆アップロード:

   ```bash
   # ビルド
   pio run

   # アップロード
   pio run -t upload

   # シリアルモニター
   pio device monitor
   ```

### 3. macOSのIPアドレス確認

```bash
# WiFiのIPアドレス
ipconfig getifaddr en0

# または全インターフェース
ifconfig | grep "inet "
```

## 使い方

1. tmuxセッションでClaude Codeを起動（`./start_claude.sh`）
2. HTTPサーバーを起動（`python3 accept_server.py`）
3. M5 Atom S3のボタンを押す → Claude Codeに「Enter」が送信される（Accept）

## APIエンドポイント

| メソッド | パス      | 説明                  |
| -------- | --------- | --------------------- |
| `POST`   | `/accept` | 「Enter」を送信（Accept） |
| `POST`   | `/reject` | 「n」を送信（Reject） |
| `POST`   | `/key`    | カスタムキーを送信    |
| `GET`    | `/status` | サーバー状態を確認    |

### テスト

```bash
# Accept送信
curl -X POST http://localhost:8080/accept

# Reject送信
curl -X POST http://localhost:8080/reject

# カスタムキー送信
curl -X POST http://localhost:8080/key \
  -H "Content-Type: application/json" \
  -d '{"key": "Enter"}'

# ステータス確認
curl http://localhost:8080/status
```

## LED表示（M5 Atom S3）

| 色     | 状態       |
| ------ | ---------- |
| 緑     | 準備完了   |
| 黄     | WiFi接続中 |
| 青     | 送信中     |
| シアン | 成功       |
| 赤     | エラー     |

## tmuxコマンド

```bash
# セッションにアタッチ
tmux attach -t claude

# デタッチ（セッション内で）
Ctrl+B, D

# セッション終了
tmux kill-session -t claude

# セッション一覧
tmux ls
```

## トラブルシューティング

### 「Session not found」エラー

→ `./start_claude.sh` でtmuxセッションを先に起動する

### M5 Atom S3が接続できない

→ macOSのファイアウォール設定を確認（ポート8080を許可）

### キーが送信されない

→ tmuxセッション名が「claude」であることを確認

```bash
# セッション確認
tmux ls
```

## ライセンス

MIT
