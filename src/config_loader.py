"""
Загрузка конфигурации линии из JSON-файла в объект LineState.

Формат конфига (config/line_config.json):
{
  "stations": [
    { "id": "st1", "name": "...", "order": 0, "capacity": 1, "processingTicks": 2 },
    ...
  ],
  "bodies": [
    { "id": "b1", "vin": "...", "model": "...", "priority": 10 },
    ...
  ]
}

Кузова из "bodies" становятся стартовой входной очередью (input_queue),
отсортированной по priority (меньше — выше приоритет).
"""

import json
from pathlib import Path

from models import Body, LineState, Station


def load_config(path: str | Path) -> LineState:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    stations = [
        Station(
            id=s["id"],
            name=s["name"],
            order=s["order"],
            capacity=s.get("capacity", 1),
            processing_ticks=s.get("processingTicks", 1),
        )
        for s in raw.get("stations", [])
    ]

    bodies_raw = raw.get("bodies", [])
    bodies: dict[str, Body] = {}
    for b in bodies_raw:
        bodies[b["id"]] = Body(
            id=b["id"],
            vin=b["vin"],
            model=b["model"],
            priority=b.get("priority", 100),
        )

    # Стартовая входная очередь — все кузова, отсортированные по приоритету
    input_queue = [
        b["id"] for b in sorted(bodies_raw, key=lambda x: x.get("priority", 100))
    ]

    return LineState(
        stations=stations,
        bodies=bodies,
        input_queue=input_queue,
    )