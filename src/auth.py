"""Модуль авторизации для HTTP API (Basic Auth по RFC 7617)."""
import base64

VALID_USERNAME = "admin"
VALID_PASSWORD = "secret"


def check_auth(auth_header: str) -> bool:
    """Проверяет заголовок Authorization (Basic Auth).

    Args:
        auth_header: Строка заголовка, например 'Basic YWRtaW46c2VjcmV0'

    Returns:
        True, если логин и пароль верны, иначе False.
    """
    if not auth_header:
        return False

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "basic":
        return False

    try:
        decoded = base64.b64decode(parts[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
        return username == VALID_USERNAME and password == VALID_PASSWORD
    except (ValueError, UnicodeDecodeError):
        return False
