"""HTTP API сервер для асинхронного вычисления SHA-256."""
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.auth import check_auth

# Константы
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
TEST_MODE = "--test" in sys.argv

# Простое хранилище в памяти (имитация БД для Этапа 2)
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
        """Отправляет JSON-ответ."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _check_authorization(self) -> bool:
        """Проверяет авторизацию и отправляет 401 если неверно."""
        auth_header = self.headers.get("Authorization")
        if not check_auth(auth_header):
            self._send_json(401, {"error": "Unauthorized"})
            return False
        return True

    def _read_body(self) -> dict:
        """Читает тело запроса (JSON)."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    # --- МАРШРУТЫ (Таблица 4) ---

    def do_PUT(self):
        """PUT запросы (1.1, 2.1)."""
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
        """POST запросы (1.2, 2.2, 3.1, 4.1)."""
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
            # Вызов нашей утилиты cli.py через subprocess (п.3 требований)
            input_file = "examples/input1.txt"
            output_file = "examples/report.json"
            try:
                subprocess.run(
                    [sys.executable, "-m", "src.cli", input_file, "-o", output_file],
                    check=True, capture_output=True
                )
                with open(output_file, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                self._send_json(200, {"report": report_data})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_PATCH(self):
        """PATCH запросы (1.3, 2.3)."""
        if not self._check_authorization():
            return

        if self.path.startswith("/public/api/modify-member/"):
            uid = int(self.path.split("/")[-1])
            if uid in DB_MEMBERS:
                DB_MEMBERS[uid].update(self._read_body())
                self._send_json(200, {"status": "updated"})
            else:
                self._send_json(404, {"error": "Member not found"})

        elif self.path.startswith("/public/api/modify-assignment/"):
            uid = int(self.path.split("/")[-1])
            if uid in DB_ASSIGNMENTS:
                DB_ASSIGNMENTS[uid].update(self._read_body())
                self._send_json(200, {"status": "updated"})
            else:
                self._send_json(404, {"error": "Assignment not found"})
        else:
            self._send_json(404, {"error": "Not found"})

    def log_message(self, format, *args):
        """Отключаем стандартное логирование в консоль (чтобы не мусорить)."""
        pass


def run_server():
    """Запускает сервер."""
    server_address = (SERVER_HOST, SERVER_PORT)
    httpd = HTTPServer(server_address, APIHandler)
    print(f"Сервер запущен на http://{SERVER_HOST}:{SERVER_PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()