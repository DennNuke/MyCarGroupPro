"""Консольная визуализация состояния линии (без графики, просто текст)."""

from metrics import get_bottleneck, get_metrics, get_station_load
from models import BodyStatus, LineState

# Символ, которым в схеме помечается узкое место
BOTTLENECK_MARK = "*"
# Символ пустой станции в схеме
EMPTY_MARK = "—"


def format_line_schema(state: LineState, bottleneck_id: str | None = None) -> str:
    """
    Однострочная ASCII-схема линии (День 3 ТЗ):

        [Вход:3] -> (Сварка:VIN1) -> (Окраска:VIN2 *) -> (Монтаж:—) -> [Готово:20]

    Слева — входная очередь, по центру — станции с VIN стоящего кузова
    (или «—», если станция пуста), узкое место помечено «*»,
    справа — счётчик готовых кузовов.
    """
    parts = [f"[Вход:{len(state.input_queue)}]"]

    for st in state.stations_sorted():
        if st.occupied_by:
            content = state.bodies[st.occupied_by].vin
        else:
            content = EMPTY_MARK
        mark = f" {BOTTLENECK_MARK}" if st.id == bottleneck_id else ""
        parts.append(f"({st.name}:{content}{mark})")

    done = sum(1 for b in state.bodies.values() if b.status == BodyStatus.DONE)
    parts.append(f"[Готово:{done}]")
    return " -> ".join(parts)


def print_line_schema(state: LineState) -> None:
    """Печатает схему линии; узкое место определяется по текущему такту."""
    bottleneck = get_bottleneck(state, state.tick)
    print("Схема: " + format_line_schema(state, bottleneck.id if bottleneck else None))


def print_metrics(state: LineState, total_ticks: int) -> None:
    """
    Печатает итоговые метрики прогона (День 2–3 ТЗ):
    completed, throughput, avgLeadTime, загрузку станций и узкое место.
    """
    m = get_metrics(state, total_ticks)
    bottleneck = get_bottleneck(state, total_ticks)

    print(f"\n=== Метрики прогона ({total_ticks} тактов) ===")
    print(f"  completed   = {m['completed']} (кузовов готово)")
    print(f"  throughput  = {m['throughput']:.3f} (кузовов за такт)")
    if m["avg_lead_time"] is None:
        print("  avgLeadTime = — (ни один кузов не готов)")
    else:
        print(f"  avgLeadTime = {m['avg_lead_time']:.1f} (тактов от входа до готовности)")

    print("\n  Загрузка станций (utilization):")
    for row in get_station_load(state, total_ticks):
        bar = "#" * round(row["utilization"] * 20)
        mark = f"  <- узкое место {BOTTLENECK_MARK}" if bottleneck and row["station_id"] == bottleneck.id else ""
        print(f"    {row['name']:<22} {row['utilization']:>5.2f} |{bar:<20}|{mark}")
    print()


def print_line_state(state: LineState) -> None:
    print(f"\n=== Такт {state.tick} ===")
    print_line_schema(state)

    print("\nСтанции:")
    for st in state.stations_sorted():
        if st.occupied_by:
            body = state.bodies[st.occupied_by]
            occ = f"занята: {body.model} ({st.occupied_by}, {body.vin}) — {st.ticks_spent}/{st.processing_ticks} тактов"
        else:
            occ = "свободна"
        print(f"  [{st.order}] {st.name:<22} ({st.id}) — {occ}")

    print("\nВходная очередь:")
    if not state.input_queue:
        print("  (пусто)")
    else:
        for body_id in state.input_queue:
            body = state.bodies[body_id]
            print(f"  {body_id}: {body.model} ({body.vin}), приоритет={body.priority}")

    print("\nБуфер доработки:")
    if not state.rework_buffer:
        print("  (пусто)")
    else:
        for body_id in state.rework_buffer:
            body = state.bodies[body_id]
            print(f"  {body_id}: {body.model} ({body.vin})")

    print()


def print_event_log(state: LineState, last_n: int | None = None) -> None:
    """Печатает журнал событий. Если last_n задан — только последние N записей."""
    entries = state.event_log if last_n is None else state.event_log[-last_n:]
    print("\n=== Журнал событий ===")
    if not entries:
        print("  (пусто)")
        return
    for e in entries:
        print(f"  [такт {e['tick']:>3}] {e['type']:<16} кузов={e['body_id']:<4} {e['from']} -> {e['to']}")
    print()
