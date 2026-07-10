"""
Unit-тесты ядра симулятора линии сборки.

Покрывает пункты из ТЗ ("Что покрыть тестами", День 5):
- продвижение кузова по тактам и блокировка занятой станцией;
- sendToRework: кузов уходит в буфер, станция освобождается;
- returnToLine: кузов встаёт в заданную позицию;
- changePriority: порядок очереди меняется;
- граничные случаи: пустая линия, все станции заняты, возврат несуществующего кузова.
"""

import pytest
from engine import (
    add_body,
    change_priority,
    rename_body,
    rename_station,
    return_to_line,
    send_to_rework,
    tick,
)
from factories import make_line
from models import BodyStatus


# ---------------------------------------------------------------------------
# Продвижение по тактам и блокировка станции
# ---------------------------------------------------------------------------

class TestTickAdvancement:
    def test_body_enters_line_from_queue(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 2)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        assert state.input_queue == ["b1"]

        tick(state)

        assert state.input_queue == []
        st1 = state.get_station("st1")
        assert st1.occupied_by == "b1"
        assert st1.ticks_spent == 0
        assert state.bodies["b1"].status == BodyStatus.IN_LINE
        assert state.bodies["b1"].current_station_id == "st1"

    def test_body_stays_on_station_until_processing_time_elapses(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 3), ("st2", "S2", 1, 1)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        tick(state)  # такт 1: b1 заезжает на st1, ticks_spent=0

        tick(state)  # такт 2: ticks_spent -> 1 (< 3), остаётся на st1
        st1 = state.get_station("st1")
        assert st1.occupied_by == "b1"
        assert st1.ticks_spent == 1

        tick(state)  # такт 3: ticks_spent -> 2 (< 3), остаётся на st1
        assert state.get_station("st1").ticks_spent == 2

        tick(state)  # такт 4: ticks_spent -> 3 (порог достигнут), но само
        # продвижение проверяется в НАЧАЛЕ такта — сработает на следующем вызове
        assert state.get_station("st1").ticks_spent == 3
        assert state.get_station("st1").occupied_by == "b1"

        tick(state)  # такт 5: ticks_spent(3) >= processing_ticks(3) -> продвигается на st2
        st1 = state.get_station("st1")
        st2 = state.get_station("st2")
        assert st1.occupied_by is None
        assert st2.occupied_by == "b1"
        assert st2.ticks_spent == 0

    def test_body_exits_line_after_last_station(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        tick(state)  # такт 1: b1 заезжает на st1, ticks_spent=0
        tick(state)  # такт 2: ticks_spent -> 1 (порог достигнут, продвижение проверится дальше)
        tick(state)  # такт 3: ticks_spent(1) >= processing_ticks(1) -> выходит с линии

        st1 = state.get_station("st1")
        assert st1.occupied_by is None
        body = state.bodies["b1"]
        assert body.status == BodyStatus.DONE
        assert body.current_station_id is None

    def test_occupied_station_blocks_advancement(self):
        # st2 обрабатывает дольше, чем st1 -> b2 должен встать и заблокировать st1
        state = make_line(
            station_specs=[("st1", "S1", 0, 1), ("st2", "S2", 1, 5)],
            body_specs=[
                ("b1", "VIN1", "Model", 10),
                ("b2", "VIN2", "Model", 20),
            ],
        )
        for _ in range(5):
            tick(state)
        # такт 1: b1 -> st1
        # такт 2: b1 ticks_spent 0->1 (порог достигнут)
        # такт 3: b1 продвигается на st2 (ticks_spent сброшен); st1 освобождается,
        #         в конце такта b2 затягивается из очереди на st1
        # такт 4: b2 ticks_spent 0->1 (порог достигнут); b1 на st2 копит ticks_spent (1->2)
        # такт 5: b2 пытается продвинуться на st2, но она занята b1 -> блокировка
        st1 = state.get_station("st1")
        st2 = state.get_station("st2")
        assert st1.occupied_by == "b2", "b2 должен остаться на st1 — станция назначения занята"
        assert st1.ticks_spent == 1, "ticks_spent не должен расти дальше, пока кузов заблокирован"
        assert st2.occupied_by == "b1"


# ---------------------------------------------------------------------------
# sendToRework
# ---------------------------------------------------------------------------

class TestSendToRework:
    def test_body_moves_to_rework_buffer_and_station_frees_immediately(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 5)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        tick(state)  # b1 -> st1

        send_to_rework(state, "b1")

        st1 = state.get_station("st1")
        assert st1.occupied_by is None
        assert st1.ticks_spent == 0
        assert state.rework_buffer == ["b1"]
        assert state.bodies["b1"].status == BodyStatus.IN_REWORK
        assert state.bodies["b1"].current_station_id is None

    def test_freed_station_is_used_by_next_body_on_next_tick(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 5)],
            body_specs=[
                ("b1", "VIN1", "Model", 10),
                ("b2", "VIN2", "Model", 20),
            ],
        )
        tick(state)  # b1 -> st1, b2 остаётся в очереди
        send_to_rework(state, "b1")  # st1 освобождается немедленно

        assert state.get_station("st1").occupied_by is None

        tick(state)  # следующий такт должен подхватить b2

        assert state.get_station("st1").occupied_by == "b2"

    def test_raises_for_nonexistent_body(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)])
        with pytest.raises(ValueError):
            send_to_rework(state, "ghost")

    def test_raises_for_body_not_on_line(self):
        # b1 ещё в очереди, не на станции
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        with pytest.raises(ValueError):
            send_to_rework(state, "b1")


# ---------------------------------------------------------------------------
# returnToLine
# ---------------------------------------------------------------------------

class TestReturnToLine:
    def test_body_inserted_at_requested_position(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[
                ("b1", "VIN1", "Model", 10),
                ("b2", "VIN2", "Model", 20),
                ("b3", "VIN3", "Model", 30),
            ],
        )
        tick(state)  # b1 -> st1
        send_to_rework(state, "b1")
        assert state.input_queue == ["b2", "b3"]

        return_to_line(state, "b1", position=1)

        assert state.input_queue == ["b2", "b1", "b3"]
        assert state.rework_buffer == []
        assert state.bodies["b1"].status == BodyStatus.QUEUED

    def test_position_is_clamped_to_valid_range(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[("b1", "VIN1", "Model", 10), ("b2", "VIN2", "Model", 20)],
        )
        tick(state)
        send_to_rework(state, "b1")

        return_to_line(state, "b1", position=999)  # больше длины очереди

        assert state.input_queue == ["b2", "b1"]  # встал в конец, без ошибки

    def test_returned_body_advances_on_subsequent_ticks(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        tick(state)
        send_to_rework(state, "b1")
        return_to_line(state, "b1", position=0)

        tick(state)  # b1 должен снова заехать на st1

        assert state.get_station("st1").occupied_by == "b1"

    def test_raises_for_nonexistent_body(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)])
        with pytest.raises(ValueError):
            return_to_line(state, "ghost", position=0)

    def test_raises_if_body_not_in_rework_buffer(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        # b1 в очереди, не в rework_buffer
        with pytest.raises(ValueError):
            return_to_line(state, "b1", position=0)


# ---------------------------------------------------------------------------
# changePriority
# ---------------------------------------------------------------------------

class TestChangePriority:
    def test_queue_order_changes_after_priority_update(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[
                ("b1", "VIN1", "Model", 10),
                ("b2", "VIN2", "Model", 20),
                ("b3", "VIN3", "Model", 30),
            ],
        )
        assert state.input_queue == ["b1", "b2", "b3"]

        change_priority(state, "b3", new_priority=1)  # b3 становится самым приоритетным

        assert state.input_queue == ["b3", "b1", "b2"]

    def test_priority_change_affects_next_tick_entry_order(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[
                ("b1", "VIN1", "Model", 10),
                ("b2", "VIN2", "Model", 20),
            ],
        )
        change_priority(state, "b2", new_priority=1)  # b2 обходит b1

        tick(state)  # на линию должен зайти b2, а не b1

        assert state.get_station("st1").occupied_by == "b2"
        assert state.input_queue == ["b1"]

    def test_raises_for_nonexistent_body(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)])
        with pytest.raises(ValueError):
            change_priority(state, "ghost", new_priority=1)


# ---------------------------------------------------------------------------
# Граничные случаи
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_tick_on_empty_line_does_not_crash(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)], body_specs=[])
        # не должно бросать исключений при пустой очереди/пустой линии
        tick(state)
        tick(state)
        assert state.input_queue == []
        assert state.get_station("st1").occupied_by is None

    def test_tick_with_no_stations_at_all_does_not_crash(self):
        state = make_line(station_specs=[], body_specs=[("b1", "VIN1", "Model", 10)])
        tick(state)  # линии некуда заезжать — просто ничего не происходит
        assert state.input_queue == ["b1"]

    def test_new_body_does_not_enter_when_all_stations_occupied(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 10)],
            body_specs=[
                ("b1", "VIN1", "Model", 10),
                ("b2", "VIN2", "Model", 20),
            ],
        )
        tick(state)  # b1 занимает единственную станцию надолго (processing_ticks=10)

        assert state.input_queue == ["b2"]
        tick(state)
        tick(state)
        # b2 всё ещё в очереди — станция занята b1, который обрабатывается 10 тактов
        assert state.input_queue == ["b2"]
        assert state.get_station("st1").occupied_by == "b1"


# ---------------------------------------------------------------------------
# add_body: добавление нового кузова (используется веб-интерфейсом)
# ---------------------------------------------------------------------------

class TestAddBody:
    def test_add_body_appends_to_end_of_queue(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        new = add_body(state)

        assert new.id == "b2"
        assert state.input_queue == ["b1", "b2"]
        assert new.status == BodyStatus.QUEUED
        # новый кузов не должен обгонять уже стоящих при пересортировке
        assert new.priority > state.bodies["b1"].priority

    def test_add_body_generates_unique_ids_and_logs_event(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)], body_specs=[])
        first = add_body(state)
        second = add_body(state)

        assert first.id != second.id
        assert first.vin != second.vin
        created = [e for e in state.event_log if e["type"] == "BODY_CREATED"]
        assert len(created) == 2


# ---------------------------------------------------------------------------
# rename_station / rename_body: переименование из веб-интерфейса
# ---------------------------------------------------------------------------

class TestRename:
    def test_rename_station_changes_name_and_logs(self):
        state = make_line(station_specs=[("st1", "Старое имя", 0, 1)])
        rename_station(state, "st1", "  Новое имя  ")

        assert state.get_station("st1").name == "Новое имя"
        ev = state.event_log[-1]
        assert ev["type"] == "STATION_RENAMED"
        assert ev["from"] == "Старое имя" and ev["to"] == "Новое имя"

    def test_rename_station_rejects_empty_name(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)])
        with pytest.raises(ValueError):
            rename_station(state, "st1", "   ")
        assert state.get_station("st1").name == "S1"

    def test_rename_station_unknown_id_raises(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)])
        with pytest.raises(KeyError):
            rename_station(state, "ghost", "Имя")

    def test_rename_body_sets_and_resets_name(self):
        state = make_line(
            station_specs=[("st1", "S1", 0, 1)],
            body_specs=[("b1", "VIN1", "Model", 10)],
        )
        rename_body(state, "b1", "Красный седан")
        assert state.bodies["b1"].name == "Красный седан"
        assert state.event_log[-1]["type"] == "BODY_RENAMED"

        rename_body(state, "b1", "")  # пустое имя сбрасывает к id
        assert state.bodies["b1"].name is None

    def test_rename_body_unknown_id_raises(self):
        state = make_line(station_specs=[("st1", "S1", 0, 1)])
        with pytest.raises(ValueError):
            rename_body(state, "ghost", "Имя")
