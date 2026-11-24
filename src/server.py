"""HTTP API сервер для асинхронного вычисления SHA-256."""
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, TCPServer

from src.auth import check_auth

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
STATUS_OK = 200
STATUS_BAD_REQUEST = 400
STATUS_UNAUTHORIZED = 401
STATUS_NOT_FOUND = 404
STATUS_SERVER_ERROR = 500

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
            self._send_json(STATUS_UNAUTHORIZED, {"error": "Unauthorized"})
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
            self._send_json(STATUS_OK, {"uid": uid, "status": "created"})
        elif self.path.startswith("/public/api/submit-assignment/"):
            uid = get_next_id()
            DB_ASSIGNMENTS[uid] = self._read_body()
            self._send_json(STATUS_OK, {"uid": uid, "status": "created"})
        else:
            self._send_json(STATUS_NOT_FOUND, {"error": "Not found"})

    def _handle_load_member(self):
        self._send_json(STATUS_OK, {"items": list(DB_MEMBERS.values())})

    def _handle_load_assignment(self):
        member_id = self.path.split("/")[-1]
        items = [
            a for a in DB_ASSIGNMENTS.values()
            if str(a.get("member")) == member_id
        ]
        self._send_json(STATUS_OK, {"items": items})

    def _handle_load_output(self):
        assignment_id = self.path.split("/")[-1]
        items = [
            o for o in DB_OUTPUTS.values()
            if str(o.get("assignment")) == assignment_id
        ]
        self._send_json(STATUS_OK, {"items": items})

    def _handle_load_report(self):
        input_file = "examples/input1.txt"
        output_file = "examples/report.json"
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m", "src.cli",
                    input_file,
                    "-o", output_file
                ],
                check=True,
                capture_output=True
            )
            with open(output_file, "r", encoding="utf-8") as f:
                report_data = json.load(f)
            self._send_json(STATUS_OK, {"report": report_data})
        except Exception as e:
            self._send_json(STATUS_SERVER_ERROR, {"error": str(e)})

    def do_POST(self):
        if not self._check_authorization():
            return

        if self.path.startswith("/public/api/load-member"):
            self._handle_load_member()
        elif self.path.startswith("/public/api/load-assignment/"):
            self._handle_load_assignment()
        elif self.path.startswith("/public/api/load-output/"):
            self._handle_load_output()
        elif self.path == "/public/api/load-report":
            self._handle_load_report()
        else:
            self._send_json(STATUS_NOT_FOUND, {"error": "Not found"})

    def do_PATCH(self):
        if not self._check_authorization():
            return

        if self.path.startswith("/public/api/modify-member/"):
            try:
                uid = int(self.path.split("/")[-1])
            except ValueError:
                self._send_json(STATUS_BAD_REQUEST, {"error": "Bad Request"})
                return
            if uid in DB_MEMBERS:
                DB_MEMBERS[uid].update(self._read_body())
                self._send_json(STATUS_OK, {"status": "updated"})
            else:
                self._send_json(
                    STATUS_NOT_FOUND,
                    {"error": "Member not found"}
                )

        elif self.path.startswith("/public/api/modify-assignment/"):
            try:
                uid = int(self.path.split("/")[-1])
            except ValueError:
                self._send_json(STATUS_BAD_REQUEST, {"error": "Bad Request"})
                return
            if uid in DB_ASSIGNMENTS:
                DB_ASSIGNMENTS[uid].update(self._read_body())
                self._send_json(STATUS_OK, {"status": "updated"})
            else:
                self._send_json(
                    STATUS_NOT_FOUND,
                    {"error": "Assignment not found"}
                )
        else:
            self._send_json(STATUS_NOT_FOUND, {"error": "Not found"})

    def log_message(self, format, *args):
        pass


class ThreadingHTTPServer(ThreadingMixIn, TCPServer):
    """Многопоточный сервер с большой очередью подключений."""
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 128


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
