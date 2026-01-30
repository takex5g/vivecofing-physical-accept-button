#!/usr/bin/env python3
"""
Claude Code Accept Server
M5 Atom S3からのHTTPリクエストを受けて、tmuxセッションにキーを送信する
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 設定
TMUX_SESSION = 'claude'
HOST = '0.0.0.0'
PORT = 8080


class AcceptHandler(BaseHTTPRequestHandler):
    """HTTPリクエストハンドラー"""

    def log_message(self, format, *args):
        """アクセスログをloggerに出力"""
        logger.info(f"{self.address_string()} - {format % args}")

    def send_json_response(self, status_code: int, data: dict):
        """JSON形式でレスポンスを返す"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_key_to_tmux(self, key: str) -> bool:
        """tmuxセッションにキーを送信"""
        try:
            result = subprocess.run(
                ['tmux', 'send-keys', '-t', TMUX_SESSION, key],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Sent key '{key}' to tmux session '{TMUX_SESSION}'")
                return True
            else:
                logger.error(f"tmux error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("tmux command timed out")
            return False
        except FileNotFoundError:
            logger.error("tmux not found")
            return False
        except Exception as e:
            logger.error(f"Error sending key: {e}")
            return False

    def do_GET(self):
        """GETリクエスト処理（ステータス確認用）"""
        if self.path == '/status':
            # tmuxセッションの存在確認
            try:
                result = subprocess.run(
                    ['tmux', 'has-session', '-t', TMUX_SESSION],
                    capture_output=True,
                    timeout=5
                )
                session_exists = result.returncode == 0
                tmux_available = True
            except FileNotFoundError:
                session_exists = False
                tmux_available = False
            except Exception:
                session_exists = False
                tmux_available = True

            self.send_json_response(200, {
                'status': 'running',
                'tmux_session': TMUX_SESSION,
                'session_exists': session_exists,
                'tmux_available': tmux_available,
                'timestamp': datetime.now().isoformat()
            })
        elif self.path == '/':
            self.send_json_response(200, {
                'endpoints': {
                    'POST /accept': 'Send "y" to accept',
                    'POST /reject': 'Send "n" to reject',
                    'POST /key': 'Send custom key (body: {"key": "x"})',
                    'GET /status': 'Check server status'
                }
            })
        else:
            self.send_json_response(404, {'error': 'Not found'})

    def do_POST(self):
        """POSTリクエスト処理"""
        if self.path == '/accept':
            # Accept (Enter) を送信
            success = self.send_key_to_tmux('Enter')
            if success:
                self.send_json_response(200, {
                    'action': 'accept',
                    'key': 'Enter',
                    'success': True
                })
            else:
                self.send_json_response(500, {
                    'action': 'accept',
                    'success': False,
                    'error': 'Failed to send key to tmux'
                })

        elif self.path == '/reject':
            # Reject (n) を送信
            success = self.send_key_to_tmux('n')
            if success:
                self.send_json_response(200, {
                    'action': 'reject',
                    'key': 'n',
                    'success': True
                })
            else:
                self.send_json_response(500, {
                    'action': 'reject',
                    'success': False,
                    'error': 'Failed to send key to tmux'
                })

        elif self.path == '/key':
            # カスタムキーを送信
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode()
                data = json.loads(body)
                key = data.get('key', '')

                if not key:
                    self.send_json_response(400, {'error': 'key is required'})
                    return

                success = self.send_key_to_tmux(key)
                if success:
                    self.send_json_response(200, {
                        'action': 'custom',
                        'key': key,
                        'success': True
                    })
                else:
                    self.send_json_response(500, {
                        'action': 'custom',
                        'success': False,
                        'error': 'Failed to send key to tmux'
                    })
            except json.JSONDecodeError:
                self.send_json_response(400, {'error': 'Invalid JSON'})

        else:
            self.send_json_response(404, {'error': 'Not found'})

    def do_OPTIONS(self):
        """CORS対応"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    """メイン関数"""
    server = HTTPServer((HOST, PORT), AcceptHandler)
    logger.info(f"Starting server on {HOST}:{PORT}")
    logger.info(f"Target tmux session: {TMUX_SESSION}")
    logger.info("Endpoints:")
    logger.info("  POST /accept - Send 'y' to accept")
    logger.info("  POST /reject - Send 'n' to reject")
    logger.info("  POST /key    - Send custom key")
    logger.info("  GET  /status - Check status")
    logger.info("-" * 40)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        server.shutdown()


if __name__ == '__main__':
    main()
