"""HTTP API сервер для асинхронного вычисления SHA-256."""
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, TCPServer

from src.auth import check_auth

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

DB_MEMBERS = {}
DB_ASSIGNMENTS = {}
DB_OUTPUTS = {}
NEXT_ID = 1


def get_next_id() -> int:
    """Генерирует следующий ID."""
    global NEXT_ID
    current = NEXT_ID
    NEXT_ID += 1
    return current


class APIHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов."""

    def _send_json(self, status_code: int, data: dict) -> None:
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _check_authorization(self) -> bool:
        auth_header = self.headers.get("Authorization")
        if not check_auth(auth_header):
            self._send_json(401, {"error": "Unauthorized"})
            return False
        return True

    def _read_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_PUT(self):
        if not self._check_authorization():
            return
        if self.path.startswith("/public/api/submit-member/"):
            uid = get_next_id()
            DB_MEMBERS[uid] = self._read_body()
            self._send_json(200, {"uid": uid, "status": "created"})
        elif self.path.startswith("/public/api/submit-assignment/"):
            uid = get_next_id()
            DB_ASSIGNMENTS[uid] = self._read_body()
            self._send_json(200, {"uid": uid, "status": "created"})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if not self._check_authorization():
            return
        if self.path.startswith("/public/api/load-member"):
            self._send_json(200, {"items": list(DB_MEMBERS.values())})
        elif self.path.startswith("/public/api/load-assignment/"):
            member_id = self.path.split("/")[-1]
            items = [a for a in DB_ASSIGNMENTS.values() if str(a.get("member")) == member_id]
            self._send_json(200, {"items": items})
        elif self.path.startswith("/public/api/load-output/"):
            assignment_id = self.path.split("/")[-1]
            items = [o for o in DB_OUTPUTS.values() if str(o.get("assignment")) == assignment_id]
            self._send_json(200, {"items": items})
        elif self.path == "/public/api/load-report":
            try:
                subprocess.run(
                    [sys.executable, "-m", "src.cli", "examples/input1.txt", "-o", "examples/report.json"],
                    check=True, capture_output=True
                )
                with open("examples/report.json", "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                self._send_json(200, {"report": report_data})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_PATCH(self):
        if not self._check_authorization():
            return
        if self.path.startswith("/public/api/modify-member/"):
            try:
                uid = int(self.path.split("/")[-1])
            except ValueError:
                self._send_json(400, {"error": "Bad Request"})
                return
            if uid in DB_MEMBERS:
                DB_MEMBERS[uid].update(self._read_body())
                self._send_json(200, {"status": "updated"})
            else:
                self._send_json(404, {"error": "Member not found"})
        elif self.path.startswith("/public/api/modify-assignment/"):
            try:
                uid = int(self.path.split("/")[-1])
            except ValueError:
                self._send_json(400, {"error": "Bad Request"})
                return
            if uid in DB_ASSIGNMENTS:
                DB_ASSIGNMENTS[uid].update(self._read_body())
                self._send_json(200, {"status": "updated"})
            else:
                self._send_json(404, {"error": "Assignment not found"})
        else:
            self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        pass


class ThreadingHTTPServer(ThreadingMixIn, TCPServer):
    """Многопоточный сервер с большой очередью подключений."""
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128  # Увеличиваем очередь


def run_server():
    """Запускает сервер."""
    server_address = (SERVER_HOST, SERVER_PORT)
    httpd = ThreadingHTTPServer(server_address, APIHandler)
    print(f"Сервер запущен на http://{SERVER_HOST}:{SERVER_PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()