"""
Метрики линии сборки (неделя 2 ТЗ): пропускная способность, время
прохождения, загрузка станций и поиск узкого места.

Формулы:
    throughput   = completed / totalTicks          (кузовов за такт)
    leadTime     = tick_finished - tick_entered    (тактов на один кузов)
    avgLeadTime  = среднее leadTime по ГОТОВЫМ кузовам (None, если готовых нет)
    utilization  = busy_ticks / totalTicks         (доля времени занятости, 0..1)
    bottleneck   = станция с максимальной utilization
                   (при равенстве — первая по порядку на линии)

Все функции только читают состояние и не меняют его.
"""

from models import BodyStatus, LineState, Station


def get_metrics(state: LineState, total_ticks: int) -> dict:
    """
    Возвращает основные метрики прогона:

    {
        "completed":     сколько кузовов стали "готов" за прогон,
        "throughput":    completed / total_ticks (0 при total_ticks = 0),
        "avg_lead_time": среднее время прохождения линии в тактах
                         (None, если ни один кузов не готов),
    }
    """
    finished = [
        b for b in state.bodies.values()
        if b.status == BodyStatus.DONE
        and b.tick_entered is not None
        and b.tick_finished is not None
    ]
    completed = len(finished)

    throughput = completed / total_ticks if total_ticks > 0 else 0.0

    if completed == 0:
        avg_lead_time = None
    else:
        avg_lead_time = sum(b.tick_finished - b.tick_entered for b in finished) / completed

    return {
        "completed": completed,
        "throughput": throughput,
        "avg_lead_time": avg_lead_time,
    }


def get_station_load(state: LineState, total_ticks: int) -> list[dict]:
    """
    Загрузка каждой станции за прогон (в порядке следования по линии):

    [ { "station_id": ..., "name": ..., "utilization": 0..1 }, ... ]

    При total_ticks = 0 все utilization равны 0 (без деления на ноль).
    """
    return [
        {
            "station_id": st.id,
            "name": st.name,
            "utilization": st.busy_ticks / total_ticks if total_ticks > 0 else 0.0,
        }
        for st in state.stations_sorted()
    ]


def get_bottleneck(state: LineState, total_ticks: int) -> Station | None:
    """
    Станция — узкое место: максимальная utilization за прогон.

    Правила предсказуемости:
    - при равной загрузке возвращается ПЕРВАЯ станция по порядку (order);
    - при total_ticks = 0 или отсутствии станций узкое место
      не определяется — возвращается None.
    """
    stations = state.stations_sorted()
    if total_ticks <= 0 or not stations:
        return None

    # max() при равенстве ключей возвращает первый элемент — как раз
    # первую станцию по order, что и требует ТЗ
    return max(stations, key=lambda st: st.busy_ticks)
