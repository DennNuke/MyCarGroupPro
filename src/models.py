"""
Модель данных линии сборки.

Station      — станция на линии (позиция, вместимость, время обработки)
Body         — кузов, движущийся по линии
LineState    — полное состояние линии на текущий момент (такт)
"""

from dataclasses import dataclass, field
from enum import Enum


class BodyStatus(str, Enum):
    """Статус кузова в системе."""
    QUEUED = "queued"        # ожидает во входной очереди
    IN_LINE = "in_line"      # находится на станции
    IN_REWORK = "in_rework"  # снят в буфер доработки
    DONE = "done"            # прошёл все станции


@dataclass
class Station:
    """
    Станция на линии сборки.

    id:               уникальный идентификатор станции
    name:             человекочитаемое название
    order:             порядковая позиция на линии (0, 1, 2, ...)
    capacity:         сколько кузовов может находиться одновременно (обычно 1)
    processing_ticks: сколько тактов кузов должен провести на станции
    """
    id: str
    name: str
    order: int
    capacity: int = 1
    processing_ticks: int = 1

    # Внутреннее состояние станции в рамках LineState:
    # id кузова, который сейчас занимает станцию (или None, если свободна)
    occupied_by: str | None = field(default=None, compare=False)
    # сколько тактов кузов уже простоял на этой станции
    ticks_spent: int = field(default=0, compare=False)
    # сколько тактов станция была занята за весь прогон (для метрики utilization)
    busy_ticks: int = field(default=0, compare=False)

    @property
    def is_free(self) -> bool:
        return self.occupied_by is None


@dataclass
class Body:
    """
    Кузов автомобиля, движущийся по линии.

    id:                уникальный идентификатор кузова
    vin:               VIN-номер (условный)
    model:             модель автомобиля
    current_station_id: id станции, где кузов находится сейчас (None, если в очереди/буфере)
    status:            текущий статус (см. BodyStatus)
    priority:          приоритет во входной очереди (чем меньше число — тем выше приоритет)
    name:              отображаемое имя, заданное пользователем (None — показывать id);
                       чисто визуальное свойство, на логику движения не влияет
    tick_entered:      номер такта, на котором кузов ВПЕРВЫЕ зашёл на первую станцию
                       (None — ещё не заходил); при возврате с доработки не сбрасывается
    tick_finished:     номер такта, на котором кузов стал "готов" (None — ещё не готов)
    """
    id: str
    vin: str
    model: str
    current_station_id: str | None = None
    status: BodyStatus = BodyStatus.QUEUED
    priority: int = 100
    name: str | None = None
    tick_entered: int | None = None
    tick_finished: int | None = None


@dataclass
class LineState:
    """
    Полное состояние линии сборки на текущий такт.

    tick:            номер текущего такта (0 — старт, до первого tick())
    stations:        список станций, упорядоченный по order
    input_queue:     очередь кузовов, ожидающих входа на линию (id кузовов)
    rework_buffer:   буфер доработки (id кузовов, снятых с линии)
    bodies:          словарь всех кузовов по id (единый источник правды)
    event_log:       журнал событий (заполняется со Дня 4)
    """
    stations: list[Station]
    bodies: dict[str, Body] = field(default_factory=dict)
    input_queue: list[str] = field(default_factory=list)
    rework_buffer: list[str] = field(default_factory=list)
    event_log: list[dict] = field(default_factory=list)
    tick: int = 0

    def get_station(self, station_id: str) -> Station:
        for st in self.stations:
            if st.id == station_id:
                return st
        raise KeyError(f"Станция с id={station_id!r} не найдена")

    def stations_sorted(self) -> list[Station]:
        return sorted(self.stations, key=lambda s: s.order)
