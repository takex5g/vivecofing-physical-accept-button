# テスト

## テストファイル

| ファイル | 説明 |
|---------|------|
| `test_server.py` | ユニットテスト（Python unittest） |
| `test_integration.sh` | 統合テスト（シェルスクリプト） |

## 実行方法

### ユニットテスト

```bash
# プロジェクトルートから実行
python3 test/test_server.py

# または pytest（インストール済みの場合）
pytest test/test_server.py -v
```

### 統合テスト

```bash
./test/test_integration.sh
```

## テスト内容

### Phase 1: 前提条件
- tmux, curl, python3 のインストール確認
- accept_server.py の存在確認

### Phase 2: サーバー起動
- HTTPサーバーがポート18080で起動するか

### Phase 3: HTTPエンドポイント
- `GET /` - エンドポイント一覧
- `GET /status` - ステータス確認
- `GET /invalid` - 404レスポンス
- `POST /accept` - Accept送信
- `POST /reject` - Reject送信
- `POST /key` - カスタムキー送信
- `POST /key` (keyなし) - 400エラー

### Phase 4: tmux連携
- セッション作成
- キー送信
- ペイン内容確認

### Phase 5: エンドツーエンド
- 'claude'セッション作成
- `/accept` → 'y'が送信されるか
- `/reject` → 'n'が送信されるか
