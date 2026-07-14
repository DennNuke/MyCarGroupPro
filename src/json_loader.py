import json
from pathlib import Path

from model import Body, LineState, Station


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

    input_queue = [
        b["id"] for b in sorted(bodies_raw, key=lambda x: x.get("priority", 100))
    ]

    return LineState(
        stations=stations,
        bodies=bodies,
        input_queue=input_queue,
    )