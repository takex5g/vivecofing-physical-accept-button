#!/usr/bin/env python3
"""
accept_server.py のユニットテスト
"""

import unittest
import json
import subprocess
import threading
import time
import urllib.request
import urllib.error
import sys
import os

# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import HTTPServer
from accept_server import AcceptHandler, HOST, PORT

TEST_PORT = 18080  # テスト用ポート


class TestAcceptServer(unittest.TestCase):
    """HTTPサーバーのテスト"""

    @classmethod
    def setUpClass(cls):
        """テストサーバーを起動"""
        cls.server = HTTPServer(('127.0.0.1', TEST_PORT), AcceptHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.5)  # サーバー起動待ち

    @classmethod
    def tearDownClass(cls):
        """テストサーバーを停止"""
        cls.server.shutdown()

    def request(self, method: str, path: str, data: dict = None) -> tuple:
        """HTTPリクエストを送信"""
        url = f'http://127.0.0.1:{TEST_PORT}{path}'
        body = json.dumps(data).encode() if data else None
        headers = {'Content-Type': 'application/json'} if data else {}

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    # ===== Phase 1: 単体テスト =====

    def test_01_root_endpoint(self):
        """GET / - エンドポイント一覧が返る"""
        status, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('endpoints', body)
        self.assertIn('POST /accept', body['endpoints'])

    def test_02_status_endpoint(self):
        """GET /status - ステータス情報が返る"""
        status, body = self.request('GET', '/status')
        self.assertEqual(status, 200)
        self.assertIn('status', body)
        self.assertEqual(body['status'], 'running')
        self.assertIn('tmux_session', body)
        self.assertIn('session_exists', body)

    def test_03_not_found(self):
        """GET /invalid - 404が返る"""
        status, body = self.request('GET', '/invalid')
        self.assertEqual(status, 404)
        self.assertIn('error', body)

    # ===== Phase 2: POSTエンドポイントテスト（tmux不要の検証） =====

    def test_04_accept_endpoint_format(self):
        """POST /accept - レスポンス形式が正しい"""
        status, body = self.request('POST', '/accept')
        # tmuxがなくても500が返り、形式は正しい
        self.assertIn(status, [200, 500])
        self.assertIn('action', body)
        self.assertEqual(body['action'], 'accept')
        self.assertIn('success', body)

    def test_05_reject_endpoint_format(self):
        """POST /reject - レスポンス形式が正しい"""
        status, body = self.request('POST', '/reject')
        self.assertIn(status, [200, 500])
        self.assertIn('action', body)
        self.assertEqual(body['action'], 'reject')

    def test_06_key_endpoint_format(self):
        """POST /key - カスタムキー送信"""
        status, body = self.request('POST', '/key', {'key': 'Enter'})
        self.assertIn(status, [200, 500])
        self.assertIn('action', body)
        self.assertEqual(body['action'], 'custom')

    def test_07_key_endpoint_missing_key(self):
        """POST /key - keyパラメータなしで400"""
        status, body = self.request('POST', '/key', {})
        self.assertEqual(status, 400)
        self.assertIn('error', body)

    def test_08_key_endpoint_invalid_json(self):
        """POST /key - 不正なJSONで400"""
        url = f'http://127.0.0.1:{TEST_PORT}/key'
        req = urllib.request.Request(
            url,
            data=b'not json',
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            status = e.code
            body = json.loads(e.read().decode())

        self.assertEqual(status, 400)
        self.assertIn('error', body)


class TestTmuxIntegration(unittest.TestCase):
    """tmux連携のテスト（tmuxが必要）"""

    TEST_SESSION = 'test_claude_button'

    @classmethod
    def setUpClass(cls):
        """テスト用tmuxセッションを作成"""
        # tmuxが利用可能か確認
        result = subprocess.run(['which', 'tmux'], capture_output=True)
        if result.returncode != 0:
            raise unittest.SkipTest('tmux not installed')

        # 既存セッションを削除
        subprocess.run(
            ['tmux', 'kill-session', '-t', cls.TEST_SESSION],
            capture_output=True
        )

        # テスト用セッション作成
        result = subprocess.run(
            ['tmux', 'new-session', '-d', '-s', cls.TEST_SESSION],
            capture_output=True
        )
        if result.returncode != 0:
            raise unittest.SkipTest('Failed to create tmux session')

        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        """テスト用tmuxセッションを削除"""
        subprocess.run(
            ['tmux', 'kill-session', '-t', cls.TEST_SESSION],
            capture_output=True
        )

    def test_01_session_exists(self):
        """tmuxセッションが存在する"""
        result = subprocess.run(
            ['tmux', 'has-session', '-t', self.TEST_SESSION],
            capture_output=True
        )
        self.assertEqual(result.returncode, 0)

    def test_02_send_key(self):
        """tmuxにキーを送信できる"""
        result = subprocess.run(
            ['tmux', 'send-keys', '-t', self.TEST_SESSION, 'echo test'],
            capture_output=True
        )
        self.assertEqual(result.returncode, 0)

    def test_03_capture_pane(self):
        """送信したキーがペインに表示される"""
        # テスト文字列を送信
        test_str = f'TEST_{int(time.time())}'
        subprocess.run(
            ['tmux', 'send-keys', '-t', self.TEST_SESSION, test_str],
            capture_output=True
        )
        time.sleep(0.2)

        # ペインの内容を取得
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', self.TEST_SESSION, '-p'],
            capture_output=True,
            text=True
        )
        self.assertIn(test_str, result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
