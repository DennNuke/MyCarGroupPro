"""
HTTP-сервер веб-интерфейса поверх ядра симуляции.

Только стандартная библиотека — никаких зависимостей.
Вся логика симуляции живёт в engine.py; сервер лишь принимает команды
от страницы index.html и отдаёт ей текущее состояние линии в JSON.

Запуск:
    python src/server.py          # http://localhost:8000
    python src/server.py 9000     # другой порт

API:
    GET  /            -> index.html
    GET  /api/state   -> текущее состояние линии
    POST /api/tick    -> tick(): продвинуть линию на один такт
    POST /api/add     -> add_body(): новый кузов в конец очереди
    POST /api/rework  -> send_to_rework(body_id)
    POST /api/return  -> return_to_line(body_id, position=0)
    POST /api/priority-> change_priority(body_id, priority)
    POST /api/rename-station -> rename_station(station_id, name)
    POST /api/rename-body    -> rename_body(body_id, name)
    POST /api/reset   -> перезагрузка состояния из config/line_config.json

Все POST-ручки возвращают свежее состояние; ошибки ядра (ValueError)
отдаются как HTTP 400 с текстом сообщения — фронтенд показывает его как есть.
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from config_loader import load_config
from engine import (
    add_body,
    change_priority,
    rename_body,
    rename_station,
    return_to_line,
    send_to_rework,
    tick,
)
from metrics import get_bottleneck, get_metrics, get_station_load
from models import LineState

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "line_config.json"
INDEX_PATH = ROOT / "index.html"
DEFAULT_PORT = 8000
# Страница показывает максимум столько последних записей журнала событий
EVENT_LOG_LIMIT = 200

# Единственное состояние симуляции на процесс; доступ строго под замком,
# т.к. ThreadingHTTPServer обслуживает запросы в разных потоках.
_lock = threading.Lock()
_state: LineState = load_config(CONFIG_PATH)


def _serialize(state: LineState) -> dict:
    """Превращает LineState в JSON-словарь для фронтенда."""
    m = get_metrics(state, state.tick)
    bottleneck = get_bottleneck(state, state.tick)
    return {
        "tick": state.tick,
        "metrics": {
            "completed": m["completed"],
            "throughput": m["throughput"],
            "avgLeadTime": m["avg_lead_time"],
        },
        "stationLoad": [
            {"stationId": r["station_id"], "name": r["name"], "utilization": r["utilization"]}
            for r in get_station_load(state, state.tick)
        ],
        "bottleneckId": bottleneck.id if bottleneck else None,
        "stations": [
            {
                "id": st.id,
                "name": st.name,
                "order": st.order,
                "processingTicks": st.processing_ticks,
                "occupiedBy": st.occupied_by,
                "ticksSpent": st.ticks_spent,
            }
            for st in state.stations_sorted()
        ],
        "bodies": {
            bid: {
                "id": b.id,
                "vin": b.vin,
                "model": b.model,
                "status": b.status.value,
                "stationId": b.current_station_id,
                "priority": b.priority,
                "name": b.name,
            }
            for bid, b in state.bodies.items()
        },
        "inputQueue": list(state.input_queue),
        "reworkBuffer": list(state.rework_buffer),
        "eventLog": state.event_log[-EVENT_LOG_LIMIT:],
        "doneCount": sum(1 for b in state.bodies.values() if b.status.value == "done"),
    }


class Handler(BaseHTTPRequestHandler):
    """Маршрутизация HTTP-запросов: статика (index.html) + JSON API."""

    def _send_json(self, payload: dict, code: int = 200) -> None:
        """Отправляет JSON-ответ с корректной кодировкой (кириллица в именах станций)."""
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        """Читает JSON-тело POST-запроса (пустое тело -> пустой словарь)."""
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802 (имя диктует BaseHTTPRequestHandler)
        if self.path in ("/", "/index.html"):
            try:
                raw = INDEX_PATH.read_bytes()
            except FileNotFoundError:
                self._send_json({"error": "index.html не найден рядом с config/"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/state":
            with _lock:
                self._send_json(_serialize(_state))
        else:
            self._send_json({"error": f"неизвестный путь: {self.path}"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        global _state
        try:
            data = self._read_json()
            with _lock:
                if self.path == "/api/tick":
                    tick(_state)
                elif self.path == "/api/add":
                    add_body(_state)
                elif self.path == "/api/rework":
                    send_to_rework(_state, data["body_id"])
                elif self.path == "/api/return":
                    return_to_line(_state, data["body_id"], int(data.get("position", 0)))
                elif self.path == "/api/priority":
                    change_priority(_state, data["body_id"], int(data["priority"]))
                elif self.path == "/api/rename-station":
                    rename_station(_state, data["station_id"], data.get("name", ""))
                elif self.path == "/api/rename-body":
                    rename_body(_state, data["body_id"], data.get("name", ""))
                elif self.path == "/api/reset":
                    _state = load_config(CONFIG_PATH)
                else:
                    self._send_json({"error": f"неизвестный путь: {self.path}"}, 404)
                    return
                self._send_json(_serialize(_state))
        except (ValueError, KeyError) as exc:
            # ошибки ядра и некорректные параметры -> 400 с человекочитаемым текстом
            self._send_json({"error": str(exc)}, 400)

    def log_message(self, fmt: str, *args) -> None:
        """Приглушаем стандартный построчный лог, чтобы не засорять консоль демо."""
        return


def main() -> None:
    """Точка входа: поднимает сервер и печатает адрес для браузера."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"MyCar Pro — линия сборки: http://localhost:{port}  (Ctrl+C — остановить)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")


if __name__ == "__main__":
    main()
