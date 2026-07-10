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

from models import Body, BodyStatus, LineState

# Шаг приоритета для новых кузовов: новый кузов получает приоритет
# "максимальный существующий + PRIORITY_STEP", чтобы не обгонять очередь.
PRIORITY_STEP = 10

# Шаблон условного VIN для кузовов, создаваемых через add_body().
VIN_TEMPLATE = "KZ{seq:04d}MYCAR"


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
            body.tick_finished = state.tick
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
            if body.tick_entered is None:
                # запоминаем только ПЕРВЫЙ вход: после возврата с доработки
                # lead time продолжает считаться от исходного входа
                body.tick_entered = state.tick

    # Шаг 3: учёт занятости станций для метрики utilization —
    # станция считается занятой на этом такте, если по его итогам на ней стоит кузов
    for st in stations:
        if st.occupied_by is not None:
            st.busy_ticks += 1

    return state


def send_to_rework(state: LineState, body_id: str) -> None:
    """
    Снимает кузов с его текущей станции и отправляет в буфер доработки.

    Требования Дня 3:
    - кузов должен реально находиться на какой-то станции линии
      (не в очереди, не уже в доработке, не завершён);
    - после снятия станция немедленно освобождается (occupied_by = None,
      ticks_spent сбрасывается), так что уже на СЛЕДУЮЩЕМ такте на неё
      может продвинуться кузов, стоявший позади;
    - кузов добавляется в state.rework_buffer и получает статус IN_REWORK.

    Бросает ValueError, если кузов не найден или не находится на линии.
    """
    body = state.bodies.get(body_id)
    if body is None:
        raise ValueError(f"Кузов с id={body_id!r} не найден")

    if body.status != BodyStatus.IN_LINE or body.current_station_id is None:
        raise ValueError(
            f"Кузов {body_id!r} нельзя отправить на доработку: "
            f"он не находится на линии (текущий статус: {body.status.value})"
        )

    station = state.get_station(body.current_station_id)
    if station.occupied_by != body_id:
        # защитная проверка на случай рассинхронизации состояния
        raise ValueError(
            f"Несогласованное состояние: станция {station.id!r} не содержит кузов {body_id!r}"
        )

    _log(state, "REWORK_OUT", body_id, station.id, "rework_buffer")

    # освобождаем станцию — на следующем такте она снова доступна
    station.occupied_by = None
    station.ticks_spent = 0

    # переводим кузов в буфер доработки
    body.current_station_id = None
    body.status = BodyStatus.IN_REWORK
    state.rework_buffer.append(body_id)


def return_to_line(state: LineState, body_id: str, position: int) -> None:
    """
    Возвращает кузов из буфера доработки во входную очередь на заданную позицию.

    Требования Дня 4:
    - кузов должен реально находиться в буфере доработки (иначе ValueError);
    - position — индекс во входной очереди (0 = первый на выходе), значение
      автоматически ограничивается диапазоном [0, len(input_queue)], чтобы
      нельзя было получить IndexError при слишком большом/отрицательном числе;
    - кузов получает статус QUEUED и с ближайшего свободного такта первой
      станции снова участвует в продвижении по линии наравне с остальными.

    Бросает ValueError, если кузов не найден или не находится в буфере доработки.
    """
    body = state.bodies.get(body_id)
    if body is None:
        raise ValueError(f"Кузов с id={body_id!r} не найден")

    if body_id not in state.rework_buffer:
        raise ValueError(
            f"Кузов {body_id!r} нельзя вернуть в линию: он не находится "
            f"в буфере доработки (текущий статус: {body.status.value})"
        )

    state.rework_buffer.remove(body_id)

    clamped_position = max(0, min(position, len(state.input_queue)))
    state.input_queue.insert(clamped_position, body_id)

    body.status = BodyStatus.QUEUED
    body.current_station_id = None

    _log(state, "RETURN_TO_LINE", body_id, "rework_buffer", f"queue@{clamped_position}")


def change_priority(state: LineState, body_id: str, new_priority: int) -> None:
    """
    Меняет приоритет кузова и пересортировывает входную очередь.

    Требования Дня 4:
    - приоритет применяется сразу (input_queue пересортировывается на месте);
    - чем МЕНЬШЕ число priority, тем ВЫШЕ приоритет (кузов ближе к началу очереди);
    - сортировка стабильная: у кузовов с одинаковым priority сохраняется их
      взаимный порядок (кто раньше встал в очередь — тот и остаётся впереди);
    - если кузов сейчас не во входной очереди (уже на линии/в доработке/готов),
      его priority всё равно обновляется — пригодится, если он вернётся в очередь
      позже (например, после доработки).

    Бросает ValueError, если кузов не найден.
    """
    body = state.bodies.get(body_id)
    if body is None:
        raise ValueError(f"Кузов с id={body_id!r} не найден")

    old_priority = body.priority
    body.priority = new_priority

    if body_id in state.input_queue:
        state.input_queue.sort(key=lambda bid: state.bodies[bid].priority)

    _log(state, "PRIORITY_CHANGE", body_id, str(old_priority), str(new_priority))


def add_body(state: LineState, model: str = "MyCar Pro") -> Body:
    """
    Создаёт новый кузов с автоматическими id/VIN и ставит его в КОНЕЦ входной очереди.

    Используется веб-интерфейсом (кнопка "Добавить кузов"):
    - id формируется как b<N> по первому свободному номеру;
    - VIN — условный, в том же стиле, что и стартовый конфиг (KZ####MYCAR);
    - priority = максимальный существующий + 10, чтобы новый кузов не обгонял
      уже стоящих в очереди при последующих пересортировках по приоритету;
    - в журнал пишется событие BODY_CREATED.
    """
    seq = len(state.bodies) + 1
    while f"b{seq}" in state.bodies:
        seq += 1
    priority = max((b.priority for b in state.bodies.values()), default=0) + PRIORITY_STEP
    body = Body(id=f"b{seq}", vin=VIN_TEMPLATE.format(seq=seq), model=model, priority=priority)
    state.bodies[body.id] = body
    state.input_queue.append(body.id)
    _log(state, "BODY_CREATED", body.id, None, "queue")
    return body


def rename_station(state: LineState, station_id: str, new_name: str) -> None:
    """
    Переименовывает станцию линии (двойной клик по карточке в веб-интерфейсе).

    Пустое название не допускается — станция обязана иметь читаемое имя.
    Бросает ValueError при пустом имени и KeyError, если станции нет.
    """
    new_name = (new_name or "").strip()
    if not new_name:
        raise ValueError("Название станции не может быть пустым")
    station = state.get_station(station_id)
    old_name = station.name
    station.name = new_name
    _log(state, "STATION_RENAMED", station_id, old_name, new_name)


def rename_body(state: LineState, body_id: str, new_name: str) -> None:
    """
    Задаёт кузову отображаемое имя; пустая строка сбрасывает имя обратно к id.

    Имя — чисто визуальное свойство: id, VIN и логика движения не меняются.
    Бросает ValueError, если кузов не найден.
    """
    body = state.bodies.get(body_id)
    if body is None:
        raise ValueError(f"Кузов с id={body_id!r} не найден")
    new_name = (new_name or "").strip()
    old_label = body.name or body.id
    body.name = new_name or None
    _log(state, "BODY_RENAMED", body_id, old_label, body.name or body.id)


def _log(state: LineState, event_type: str, body_id: str, from_: str | None, to: str | None) -> None:
    """
    Запись в журнал событий.

    Каждая запись: номер такта, тип события, кузов, откуда -> куда.
    Типы событий: ENTER_LINE, ADVANCE, EXIT_LINE, REWORK_OUT,
    RETURN_TO_LINE, PRIORITY_CHANGE.
    """
    state.event_log.append(
        {
            "tick": state.tick,
            "type": event_type,
            "body_id": body_id,
            "from": from_,
            "to": to,
        }
    )
