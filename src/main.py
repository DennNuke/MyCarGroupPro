import sys
from pathlib import Path
from model import Station 
from console_printer import print_line_state
from json_loader import load_config
from engine import tick

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "json" / "config1.json"
DEFAULT_TICKS = 10


def main() -> None:
    config_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CONFIG_PATH
    line_state = load_config(config_path)

    print_line_state(line_state)

    for n in range(0, DEFAULT_TICKS):
        input()
        tick(line_state)
        print_line_state(line_state)
        
if __name__ == "__main__":
    main()