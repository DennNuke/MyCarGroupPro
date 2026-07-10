"""
Тесты метрик недели 2: throughput, avgLeadTime, загрузка станций,
узкое место и ASCII-схема линии.

Сценарии соответствуют таблице «Тесты — конкретные проверки» из ТЗ.
"""

import pytest

from display import format_line_schema
from engine import return_to_line, send_to_rework, tick
from factories import make_line
from metrics import get_bottleneck, get_metrics, get_station_load


def run_ticks(state, n):
    for _ in range(n):
        tick(state)
    return state


def three_station_line(num_bodies=5):
    """3 станции с processing_ticks=1 и num_bodies кузовов в очереди."""
    return make_line(
        [("st1", "Сварка", 0, 1), ("st2", "Окраска", 1, 1), ("st3", "Монтаж", 2, 1)],
        [(f"b{i}", f"VIN{i}", "MyCar Pro", i * 10) for i in range(1, num_bodies + 1)],
    )


class TestGetMetrics:
    def test_five_bodies_complete_line_manual_numbers(self):
        """ТЗ: 3 станции, 5 кузовов, прогон до конца линии.

        Ручной подсчёт (движок: вход в конце такта, +processing_ticks
        на станции, продвижение на следующем такте):
          b1 входит на такте 1 и готов на такте 7  -> lead time 6
          далее кузова выходят каждые 2 такта: 9, 11, 13, 15
        Итого за 15 тактов: completed=5, avgLeadTime=6.0, throughput=5/15.
        """
        state = run_ticks(three_station_line(5), 15)

        m = get_metrics(state, 15)
        assert m["completed"] == 5
        assert m["throughput"] == pytest.approx(5 / 15)
        assert m["avg_lead_time"] == pytest.approx(6.0)

    def test_no_completed_bodies_gives_null_lead_time(self):
        """ТЗ: ни один кузов не готов -> completed=0, avgLeadTime=null."""
        state = run_ticks(three_station_line(2), 3)  # 3 тактов мало, чтобы выйти

        m = get_metrics(state, 3)
        assert m["completed"] == 0
        assert m["avg_lead_time"] is None
        assert m["throughput"] == 0.0

    def test_empty_line_no_bodies_does_not_crash(self):
        """ТЗ: пустая линия (нет кузовов) -> completed=0, avgLeadTime=null, без ошибок."""
        state = run_ticks(three_station_line(0), 10)

        m = get_metrics(state, 10)
        assert m == {"completed": 0, "throughput": 0.0, "avg_lead_time": None}

    def test_total_ticks_zero_no_division_error(self):
        """ТЗ: totalTicks=0 -> throughput=0, без деления на ноль."""
        state = three_station_line(3)

        m = get_metrics(state, 0)
        assert m["throughput"] == 0.0
        assert m["completed"] == 0

    def test_lead_time_counts_from_first_entry_after_rework(self):
        """avgLeadTime считается от ПЕРВОГО входа: возврат с доработки
        не сбрасывает tick_entered."""
        state = three_station_line(1)
        tick(state)  # b1 входит на такте 1
        first_entry = state.bodies["b1"].tick_entered
        assert first_entry == 1

        send_to_rework(state, "b1")
        return_to_line(state, "b1", 0)
        run_ticks(state, 10)

        assert state.bodies["b1"].tick_entered == first_entry
        m = get_metrics(state, 11)
        assert m["completed"] == 1
        assert m["avg_lead_time"] > 6  # доработка удлинила прохождение


class TestStationLoadAndBottleneck:
    def slow_middle_line(self):
        """Средняя станция в 3 раза медленнее остальных — заведомое узкое место."""
        return make_line(
            [("st1", "Сварка", 0, 1), ("st2", "Окраска", 1, 3), ("st3", "Монтаж", 2, 1)],
            [(f"b{i}", f"VIN{i}", "MyCar Pro", i * 10) for i in range(1, 6)],
        )

    def test_slow_station_is_bottleneck(self):
        """ТЗ: станция с processingTicks=3, остальные=1 -> bottleneck = эта станция."""
        state = run_ticks(self.slow_middle_line(), 30)

        bottleneck = get_bottleneck(state, 30)
        assert bottleneck is not None
        assert bottleneck.id == "st2"

        load = {row["station_id"]: row["utilization"] for row in get_station_load(state, 30)}
        assert load["st2"] == max(load.values())

    def test_utilization_always_between_0_and_1(self):
        """ТЗ: utilization каждой станции в диапазоне 0..1."""
        state = run_ticks(self.slow_middle_line(), 25)

        for row in get_station_load(state, 25):
            assert 0.0 <= row["utilization"] <= 1.0

    def test_station_load_keeps_line_order(self):
        state = run_ticks(self.slow_middle_line(), 10)
        assert [r["station_id"] for r in get_station_load(state, 10)] == ["st1", "st2", "st3"]

    def test_equal_load_returns_first_station_by_order(self):
        """ТЗ: две станции с равной загрузкой -> вернуть первую по порядку."""
        state = three_station_line(0)
        state.get_station("st1").busy_ticks = 5
        state.get_station("st2").busy_ticks = 5
        state.get_station("st3").busy_ticks = 2

        bottleneck = get_bottleneck(state, 10)
        assert bottleneck.id == "st1"

    def test_total_ticks_zero_bottleneck_is_none(self):
        """ТЗ: totalTicks=0 -> все utilization=0, bottleneck=null."""
        state = three_station_line(3)

        assert get_bottleneck(state, 0) is None
        assert all(r["utilization"] == 0.0 for r in get_station_load(state, 0))

    def test_no_stations_bottleneck_is_none(self):
        state = make_line([], [])
        assert get_bottleneck(state, 10) is None


class TestLineSchema:
    def test_schema_shows_queue_stations_and_done(self):
        state = three_station_line(3)
        tick(state)  # b1 на первой станции

        schema = format_line_schema(state)
        assert schema.startswith("[Вход:2]")
        assert "(Сварка:VIN1)" in schema
        assert "(Окраска:—)" in schema
        assert schema.endswith("[Готово:0]")

    def test_schema_marks_bottleneck_station(self):
        state = run_ticks(three_station_line(3), 4)
        bottleneck = get_bottleneck(state, 4)

        schema = format_line_schema(state, bottleneck.id)
        assert "*" in schema
        # звёздочка стоит именно в скобках станции-узкого места
        marked = [p for p in schema.split(" -> ") if "*" in p]
        assert len(marked) == 1
        assert bottleneck.name in marked[0]

    def test_schema_counts_done_bodies(self):
        state = run_ticks(three_station_line(2), 20)
        schema = format_line_schema(state)
        assert schema.endswith("[Готово:2]")
