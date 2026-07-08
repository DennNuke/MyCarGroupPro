"""
Точка входа. День 1: загрузка конфига и вывод стартового состояния линии.

Запуск:
    python src/main.py
"""

from pathlib import Path

from config_loader import load_config
from display import print_line_state

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "line_config.json"


def main() -> None:
    state = load_config(DEFAULT_CONFIG_PATH)
    print("Линия успешно загружена из конфига:", DEFAULT_CONFIG_PATH)
    print_line_state(state)


if __name__ == "__main__":
    main()
