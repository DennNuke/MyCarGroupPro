import sys
from pathlib import Path
from model import Station 
from console_printer import print_line_state
from json_loader import load_config
from engine import tick, get_bottleneck, update, run_scenario

DEFAULT_CONFIG1_PATH = Path(__file__).parent.parent / "json" / "config1.json"
DEFAULT_CONFIG2_PATH = Path(__file__).parent.parent / "json" / "config2.json"
DEFAULT_TICKS = 20


def main() -> None:
    config1_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CONFIG1_PATH
    config2_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CONFIG2_PATH

    print(run_scenario(load_config(config1_path),DEFAULT_TICKS))
    print()
    print(run_scenario(load_config(config2_path),DEFAULT_TICKS))

    # print_line_state(line_state)

    # for n in range(0, DEFAULT_TICKS):
    #     input()
    #     tick(line_state)
    #     update(commands, line_state)
    #     print_line_state(line_state)

    # print(line_state.event_log)
    # print(line_state.get_metrics()) 
    # max_id =  get_bottleneck(line_state)     
    # print(max_id + " : " + str(line_state.get_station(max_id).busy_ticks))

if __name__ == "__main__":
    main()