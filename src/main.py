"""
Точка входа.

День 1: загрузка конфига и вывод стартового состояния линии.
День 2: прогон нескольких тактов (tick) с выводом состояния после каждого.
День 3: демонстрация отправки кузова на доработку (send_to_rework) в середине прогона.

Запуск:
    python src/main.py            # прогоняет 12 тактов по умолчанию
    python src/main.py 20         # прогоняет 20 тактов
"""

import sys
from pathlib import Path

from config_loader import load_config
from display import print_line_state
from engine import send_to_rework, tick

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "line_config.json"
DEFAULT_TICKS = 12

# На каком такте и какой кузов демонстрационно отправить на доработку.
# Это просто демонстрация для Дня 3 — полноценный CLI/API для ручного
# управления операциями появится ближе к Дню 4-5.
REWORK_DEMO_TICK = 3
REWORK_DEMO_BODY_ID = "b1"


def main() -> None:
    num_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TICKS

    state = load_config(DEFAULT_CONFIG_PATH)
    print("Линия успешно загружена из конфига:", DEFAULT_CONFIG_PATH)
    print_line_state(state)

    for i in range(1, num_ticks + 1):
        tick(state)
        print_line_state(state)

        if i == REWORK_DEMO_TICK:
            body = state.bodies.get(REWORK_DEMO_BODY_ID)
            if body is not None and body.status.value == "in_line":
                print(f">>> Демо: отправляем кузов {REWORK_DEMO_BODY_ID} на доработку "
                      f"(станция {body.current_station_id})")
                send_to_rework(state, REWORK_DEMO_BODY_ID)
                print_line_state(state)


if __name__ == "__main__":
    main()