"""Тест загрузки реального конфига линии из config/line_config.json."""

from pathlib import Path

from config_loader import load_config

CONFIG_PATH = Path(__file__).parent.parent / "config" / "line_config.json"


def test_load_real_config_produces_five_stations_sorted_by_order():
    state = load_config(CONFIG_PATH)
    assert len(state.stations) == 5
    orders = [st.order for st in state.stations_sorted()]
    assert orders == sorted(orders)


def test_load_real_config_input_queue_sorted_by_priority():
    state = load_config(CONFIG_PATH)
    priorities = [state.bodies[bid].priority for bid in state.input_queue]
    assert priorities == sorted(priorities)


def test_load_real_config_all_bodies_start_queued():
    state = load_config(CONFIG_PATH)
    for body_id in state.input_queue:
        assert state.bodies[body_id].current_station_id is None
