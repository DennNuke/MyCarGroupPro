"""Вспомогательные фабрики для построения тестовых LineState без JSON-конфига."""

from models import Body, LineState, Station


def make_line(station_specs, body_specs=()):
    """
    station_specs: список кортежей (id, name, order, processing_ticks)
    body_specs:    список кортежей (id, vin, model, priority)

    Возвращает готовый LineState со входной очередью, отсортированной
    по приоритету (как это делает config_loader.load_config).
    """
    stations = [
        Station(id=sid, name=name, order=order, processing_ticks=pt)
        for sid, name, order, pt in station_specs
    ]

    bodies = {}
    for bid, vin, model, priority in body_specs:
        bodies[bid] = Body(id=bid, vin=vin, model=model, priority=priority)

    input_queue = [bid for bid, *_ in sorted(body_specs, key=lambda b: b[3])]

    return LineState(stations=stations, bodies=bodies, input_queue=input_queue)
