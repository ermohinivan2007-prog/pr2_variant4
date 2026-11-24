"""MBT-тесты для HTTP API с использованием hypothesis."""
import threading
import time
import pytest
import requests
from hypothesis import settings, HealthCheck
from hypothesis.stateful import (
    RuleBasedStateMachine, rule, run_state_machine_as_test
)
from hypothesis import strategies as st

from src.server import run_server, SERVER_HOST, SERVER_PORT

BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
AUTH = ("admin", "secret")
STATUS_OK = 200
STATUS_NOT_FOUND = 404
DEFAULT_TIMEOUT = 2
STEP_DELAY = 0.1


@pytest.fixture(scope="session", autouse=True)
def start_server():
    """Фикстура, которая запускает сервер перед тестами."""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    yield


class APITestMachine(RuleBasedStateMachine):
    """Модель поведения для тестирования HTTP API."""

    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        self.session.auth = AUTH

    def _pause(self):
        time.sleep(STEP_DELAY)

    @rule(uid=st.integers(min_value=1, max_value=100))
    def test_submit_member(self, uid):
        self._pause()
        url = f"{BASE_URL}/public/api/submit-member/{uid}"
        resp = self.session.put(url, json={"uid": uid}, timeout=DEFAULT_TIMEOUT)
        assert resp.status_code == STATUS_OK

    @rule()
    def test_load_member(self):
        self._pause()
        url = f"{BASE_URL}/public/api/load-member"
        resp = self.session.post(url, timeout=DEFAULT_TIMEOUT)
        assert resp.status_code == STATUS_OK

    @rule(uid=st.integers(min_value=1, max_value=100))
    def test_modify_member(self, uid):
        self._pause()
        url = f"{BASE_URL}/public/api/modify-member/{uid}"
        resp = self.session.patch(
            url, json={"uid": uid}, timeout=DEFAULT_TIMEOUT
        )
        assert resp.status_code in (STATUS_OK, STATUS_NOT_FOUND)

    @rule(uid=st.integers(min_value=1, max_value=100))
    def test_submit_assignment(self, uid):
        self._pause()
        url = f"{BASE_URL}/public/api/submit-assignment/{uid}"
        resp = self.session.put(url, json={"uid": uid}, timeout=DEFAULT_TIMEOUT)
        assert resp.status_code == STATUS_OK

    @rule(member_id=st.integers(min_value=1, max_value=100))
    def test_load_assignment(self, member_id):
        self._pause()
        url = f"{BASE_URL}/public/api/load-assignment/{member_id}"
        resp = self.session.post(url, timeout=DEFAULT_TIMEOUT)
        assert resp.status_code == STATUS_OK

    @rule(uid=st.integers(min_value=1, max_value=100))
    def test_modify_assignment(self, uid):
        self._pause()
        url = f"{BASE_URL}/public/api/modify-assignment/{uid}"
        resp = self.session.patch(
            url, json={"uid": uid}, timeout=DEFAULT_TIMEOUT
        )
        assert resp.status_code in (STATUS_OK, STATUS_NOT_FOUND)

    @rule(assignment_id=st.integers(min_value=1, max_value=100))
    def test_load_output(self, assignment_id):
        self._pause()
        url = f"{BASE_URL}/public/api/load-output/{assignment_id}"
        resp = self.session.post(url, timeout=DEFAULT_TIMEOUT)
        assert resp.status_code == STATUS_OK

    @rule()
    def test_load_report(self):
        self._pause()
        url = f"{BASE_URL}/public/api/load-report"
        resp = self.session.post(url, timeout=DEFAULT_TIMEOUT)
        assert resp.status_code == STATUS_OK
        assert "report" in resp.json()


def test_mbt():
    """Запуск тестирования на основе модели."""
    settings_obj = settings(
        max_examples=5,
        stateful_step_count=5,
        suppress_health_check=[
            HealthCheck.too_slow,
            HealthCheck.function_scoped_fixture,
            HealthCheck.filter_too_much
        ],
        deadline=None,
    )
    run_state_machine_as_test(APITestMachine, settings=settings_obj)
