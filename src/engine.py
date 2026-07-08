"""
Движок симуляции: функция tick() продвигает линию на один такт.

Логика одного такта (в этом порядке):

1. Станции обрабатываются от ПОСЛЕДНЕЙ к ПЕРВОЙ (order убывает).
   Это важно: если сначала продвинуть кузов в начале линии, а потом
   выяснится, что станция назначения занята — придётся откатывать.
   Обработка с конца исключает эту проблему: место освобождается
   там, где кузов уходит дальше/выходит с линии, и это место
   становится доступно для кузова, идущего следом, в рамках ТОГО ЖЕ такта
   не требуется — каждый кузов продвигается максимум на одну станцию за такт.

   Для каждой занятой станции:
   - если кузов ещё не доработал положенное число тактов (ticks_spent < processing_ticks)
     -> увеличиваем ticks_spent на 1 (кузов продолжает обрабатываться);
   - если кузов уже отработал (ticks_spent >= processing_ticks):
       - если это последняя станция линии -> кузов покидает линию (status = DONE);
       - иначе смотрим на следующую станцию:
           - если она свободна -> кузов переходит на неё, ticks_spent сбрасывается;
           - если она занята -> кузов остаётся на месте, станция заблокирована
             (typичное "занятая станция блокирует продвижение").

2. После обработки существующих кузовов пытаемся забрать кузова из входной
   очереди (FIFO) на первую станцию линии, если она свободна.
"""

from models import BodyStatus, LineState


def tick(state: LineState) -> LineState:
    """Продвигает линию на один такт и возвращает изменённое состояние."""
    state.tick += 1
    stations = state.stations_sorted()
    n = len(stations)

    # Шаг 1: обрабатываем занятые станции от последней к первой
    for i in reversed(range(n)):
        st = stations[i]
        if st.occupied_by is None:
            continue

        if st.ticks_spent < st.processing_ticks:
            # кузов ещё обрабатывается на этой станции
            st.ticks_spent += 1
            continue

        # кузов отработал положенное время — пытаемся продвинуть дальше
        body_id = st.occupied_by
        body = state.bodies[body_id]

        if i == n - 1:
            # последняя станция — кузов выходит с линии
            _log(state, "EXIT_LINE", body_id, st.id, None)
            body.status = BodyStatus.DONE
            body.current_station_id = None
            st.occupied_by = None
            st.ticks_spent = 0
            continue

        next_st = stations[i + 1]
        if next_st.is_free:
            _log(state, "ADVANCE", body_id, st.id, next_st.id)
            next_st.occupied_by = body_id
            next_st.ticks_spent = 0
            body.current_station_id = next_st.id
            st.occupied_by = None
            st.ticks_spent = 0
        # иначе: следующая станция занята -> кузов остаётся,
        # станция заблокирована до освобождения next_st

    # Шаг 2: затягиваем новый кузов из входной очереди на первую станцию
    if stations:
        first_st = stations[0]
        if first_st.is_free and state.input_queue:
            body_id = state.input_queue.pop(0)
            body = state.bodies[body_id]
            _log(state, "ENTER_LINE", body_id, "queue", first_st.id)
            first_st.occupied_by = body_id
            first_st.ticks_spent = 0
            body.current_station_id = first_st.id
            body.status = BodyStatus.IN_LINE

    return state


def _log(state: LineState, event_type: str, body_id: str, from_: str | None, to: str | None) -> None:
    """Минимальная запись в журнал событий (полноценно доработаем в День 4)."""
    state.event_log.append(
        {
            "tick": state.tick,
            "type": event_type,
            "body_id": body_id,
            "from": from_,
            "to": to,
        }
    )