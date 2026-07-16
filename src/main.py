import sys
from pathlib import Path
from model import Station 
from console_printer import print_line_state
from json_loader import load_config
from engine import tick, send_to_tework, return_to_line,change_priority, get_bottleneck

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "json" / "config1.json"
DEFAULT_TICKS = 20


def main() -> None:
    config_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CONFIG_PATH
    line_state = load_config(config_path)

    print_line_state(line_state)

    for n in range(0, DEFAULT_TICKS):
        # input()
        if n == 2:
            send_to_tework(line_state, "b1")

        if n == 3:
            change_priority(line_state, "b4", 39)

        if n == 5:
            return_to_line(line_state, "b1", 29)

            
        tick(line_state)
        print_line_state(line_state)

    print(line_state.event_log)
    print(line_state.get_metrics()) 
    max_id =  get_bottleneck(line_state)     
    print(max_id + " : " + str(line_state.get_station(max_id).busy_ticks))
if __name__ == "__main__":
    main()