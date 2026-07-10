"""
Точка входа.

Неделя 1: загрузка конфига, прогон тактов, доработка/возврат/приоритет, журнал.
Неделя 2: метрики прогона (completed, throughput, avgLeadTime), загрузка
          станций, узкое место и ASCII-схема линии.

Запуск:
    python src/main.py                         # 14 тактов, config/line_config.json
    python src/main.py 20                      # 20 тактов
    python src/main.py 40 config/demo_config.json   # демо-конфиг с узким местом
"""

import sys
from pathlib import Path

from config_loader import load_config
from display import print_event_log, print_line_state, print_metrics
from engine import change_priority, return_to_line, send_to_rework, tick

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "line_config.json"
DEFAULT_TICKS = 14

# Демонстрационный сценарий действий по тактам.
# Формат: {номер_такта: [(функция, args...), ...]}
# Это просто демонстрация для README/презентации; полноценный CLI/API
# для ручного управления операциями — вне рамок недельного MVP.
DEMO_ACTIONS = {
    3: [("rework", "b1")],
    5: [("priority", "b4", 1)],       # b4 получает наивысший приоритет
    7: [("return", "b1", 0)],          # b1 возвращается в начало очереди
}


def _run_demo_actions(state, tick_number: int) -> None:
    for action in DEMO_ACTIONS.get(tick_number, []):
        kind = action[0]
        if kind == "rework":
            _, body_id = action
            print(f">>> Демо: send_to_rework({body_id!r})")
            send_to_rework(state, body_id)
        elif kind == "return":
            _, body_id, position = action
            print(f">>> Демо: return_to_line({body_id!r}, position={position})")
            return_to_line(state, body_id, position)
        elif kind == "priority":
            _, body_id, new_priority = action
            print(f">>> Демо: change_priority({body_id!r}, {new_priority})")
            change_priority(state, body_id, new_priority)
        print_line_state(state)


def main() -> None:
    num_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TICKS
    config_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CONFIG_PATH
    # демо-сценарий rework/priority/return рассчитан на стартовый конфиг
    demo_actions_enabled = config_path == DEFAULT_CONFIG_PATH

    state = load_config(config_path)
    print("Линия успешно загружена из конфига:", config_path)
    print_line_state(state)

    for i in range(1, num_ticks + 1):
        tick(state)
        print_line_state(state)
        if demo_actions_enabled:
            _run_demo_actions(state, i)

    print_event_log(state)
    print_metrics(state, num_ticks)


if __name__ == "__main__":
    main()
