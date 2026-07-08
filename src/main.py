"""
Точка входа.

День 1: загрузка конфига и вывод стартового состояния линии.
День 2: прогон нескольких тактов (tick) с выводом состояния после каждого.

Запуск:
    python src/main.py            # прогоняет 12 тактов по умолчанию
    python src/main.py 20         # прогоняет 20 тактов
"""

import sys
from pathlib import Path

from config_loader import load_config
from display import print_line_state
from engine import tick

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "line_config.json"
DEFAULT_TICKS = 12


def main() -> None:
    num_ticks = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TICKS

    state = load_config(DEFAULT_CONFIG_PATH)
    print("Линия успешно загружена из конфига:", DEFAULT_CONFIG_PATH)
    print_line_state(state)

    for _ in range(num_ticks):
        tick(state)
        print_line_state(state)


if __name__ == "__main__":
    main()